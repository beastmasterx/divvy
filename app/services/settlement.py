from sqlalchemy.orm import Session

from app.core.i18n import _
from app.models.models import Transaction, TransactionKind
from app.services.transaction import TransactionService


class SettlementService:
    def __init__(self, session: Session):
        self.session = session
        self.transaction_service = TransactionService(session)

    def get_all_balances(self, period_id: int) -> dict[int, int]:
        """Calculate balances for all users in a specific period.

        Returns:
            dict[int, int]: {user_id: net_balance}
                Positive = user is owed money
                Negative = user owes money
        """
        balances: dict[int, int] = {}
        transactions = self.transaction_service.get_transactions_by_period_id(period_id)
        for transaction in transactions:
            if transaction.transaction_kind == TransactionKind.EXPENSE:
                shares = self.transaction_service.calculate_shares_for_transaction(transaction.id)
                for user_id, amount in shares.items():
                    balances[user_id] += amount
            elif transaction.transaction_kind == TransactionKind.DEPOSIT:
                balances[transaction.payer_id] += transaction.amount
            elif transaction.transaction_kind == TransactionKind.REFUND:
                balances[transaction.payer_id] -= transaction.amount
            else:
                raise ValueError(
                    _("Invalid transaction kind: %(transaction_kind)s")
                    % {"transaction_kind": transaction.transaction_kind}
                )
        return balances

    def get_settlement_plan(self, period_id: int) -> list[Transaction]:
        """Get settlement plan for a specific period.

        Returns:
            list[Transaction]: List of transactions that would be created to settle balances
        """
        plan: list[Transaction] = []
        balances = self.get_all_balances(period_id)
        for user_id, balance in balances.items():
            if balance > 0:
                plan.append(Transaction(transaction_kind=TransactionKind.DEPOSIT, amount=balance, payer_id=user_id))
            elif balance < 0:
                plan.append(Transaction(transaction_kind=TransactionKind.REFUND, amount=-balance, payer_id=user_id))
        return plan
