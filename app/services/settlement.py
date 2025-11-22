from collections import defaultdict

from app.api.schemas import SettlementPlanResponse, TransactionRequest
from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.models import SplitKind, TransactionKind
from app.services.category import CategoryService
from app.services.period import PeriodService
from app.services.transaction import TransactionService
from app.services.user import UserService


class SettlementService:
    def __init__(
        self,
        transaction_service: TransactionService,
        period_service: PeriodService,
        category_service: CategoryService,
        user_service: UserService,
    ):
        self.transaction_service = transaction_service
        self.period_service = period_service
        self.category_service = category_service
        self.user_service = user_service

    def get_all_balances(self, period_id: int) -> dict[int, int]:
        """Calculate balances for all users in a specific period.

        Returns:
            dict[int, int]: {user_id: net_balance}
                Positive = user is owed money
                Negative = user owes money
        """
        balances: dict[int, int] = defaultdict(int)
        transactions = self.transaction_service.get_transactions_by_period_id(period_id)
        for transaction in transactions:
            if transaction.transaction_kind == TransactionKind.EXPENSE:
                # Credit the payer for paying the full amount
                balances[transaction.payer_id] += transaction.amount

                # Debit each participant for their share
                shares = self.transaction_service.calculate_shares_for_transaction(transaction.id)
                for user_id, amount in shares.items():
                    balances[user_id] -= amount
            elif transaction.transaction_kind == TransactionKind.DEPOSIT:
                balances[transaction.payer_id] += transaction.amount
            elif transaction.transaction_kind == TransactionKind.REFUND:
                balances[transaction.payer_id] -= transaction.amount
            else:
                raise ValidationError(
                    _("Invalid transaction kind: %(transaction_kind)s")
                    % {"transaction_kind": transaction.transaction_kind}
                )
        return dict(balances)

    def get_settlement_plan(self, period_id: int) -> list[SettlementPlanResponse]:
        """Get settlement plan for a specific period.

        Returns:
            list[Transaction]: List of transactions that would be created to settle balances

        Raises:
            NotFoundError: If period or settlement category is not found
        """
        # Get period to ensure it exists and for context
        period = self.period_service.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)
        if period.is_closed:
            raise BusinessRuleError(_("Period %s is already closed") % period_id)

        # Get settlement category
        settlement_category = self.category_service.get_category_by_name("Settlement")
        if not settlement_category:
            raise NotFoundError(_("Settlement category not found"))

        plan: list[SettlementPlanResponse] = []
        balances = self.get_all_balances(period_id)

        for user_id, balance in balances.items():
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                raise NotFoundError(_("User %s not found") % user_id)
            transaction = SettlementPlanResponse(
                transaction_kind=TransactionKind.DEPOSIT,
                amount=balance,
                payer_id=user_id,
                payer_name=user.name,
                period_id=period_id,
                period_name=period.name,
                category_id=settlement_category.id,
                category_name=settlement_category.name,
                split_kind=SplitKind.PERSONAL,
                description=_("Settlement payment to user %s") % user.name,
            )
            if balance > 0:
                # User is owed money - they should receive a DEPOSIT
                plan.append(transaction)
            elif balance < 0:
                # User owes money - they should make a payment (REFUND represents money being returned/paid)
                transaction.transaction_kind = TransactionKind.REFUND
                transaction.description = _("Settlement payment from user %s") % user_id
                plan.append(transaction)
        return plan

    def apply_settlement_plan(self, period_id: int) -> None:
        """Apply the settlement plan to the period."""
        plan = self.get_settlement_plan(period_id)
        for t in plan:
            request = TransactionRequest(
                transaction_kind=t.transaction_kind,
                amount=t.amount,
                payer_id=t.payer_id,
                period_id=t.period_id,
                category_id=t.category_id,
                split_kind=t.split_kind,
                description=t.description,
                expense_shares=[],
            )
            self.transaction_service.create_transaction(request)
        self.period_service.close_period(period_id)
