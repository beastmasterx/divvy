from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models import PeriodStatus, Settlement
from app.repositories import SettlementRepository
from app.schemas import SettlementResponse
from app.services.period import PeriodService
from app.services.transaction import TransactionService
from app.services.user import UserService


class SettlementService:
    def __init__(
        self,
        period_service: PeriodService,
        transaction_service: TransactionService,
        user_service: UserService,
        settlement_repository: SettlementRepository,
    ):
        self._period_service = period_service
        self._transaction_service = transaction_service
        self._user_service = user_service
        self._settlement_repository = settlement_repository

    async def get_settlements_by_period_id(self, period_id: int) -> Sequence[SettlementResponse]:
        """Get settlements for a specific period."""
        settlements = await self._settlement_repository.get_settlements_by_period_id(period_id)
        return [SettlementResponse.model_validate(settlement) for settlement in settlements]

    async def get_settlement_plan(self, period_id: int) -> Sequence[SettlementResponse]:
        """Get settlement plan for a specific period.

        Returns a minimal set of transfers to settle all balances.

        Returns:
            list[SettlementPlanResponse]: List of settlement transfers (payer -> payee)

        Raises:
            NotFoundError: If period or users are not found
            BusinessRuleError: If period is not closed
        """
        # Get period to ensure it exists and for context
        period = await self._period_service.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)
        if period.status != PeriodStatus.CLOSED:
            raise BusinessRuleError(_("Period %s is not closed") % period_id)

        plan: list[SettlementResponse] = []
        balances = await self._transaction_service.get_all_balances(period_id)

        # Separate creditors (positive balance) and debtors (negative balance)
        creditors: list[tuple[int, int]] = []  # (user_id, amount_owed)
        debtors: list[tuple[int, int]] = []  # (user_id, amount_owed)

        for balance_response in balances:
            user_id = balance_response.user_id
            balance = balance_response.balance
            if balance > 0:
                creditors.append((user_id, balance))
            elif balance < 0:
                debtors.append((user_id, -balance))  # Store as positive amount

        # Sort by amount (largest first) for optimal matching
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)

        # Get user names for all involved users
        user_ids = {user_id for user_id, _ in creditors + debtors}
        users: dict[int, str] = {}  # Store user names for lookup
        for user_id in user_ids:
            user = await self._user_service.get_user_by_id(user_id)
            if not user:
                raise NotFoundError(_("User %s not found") % user_id)
            users[user_id] = user.name

        # Greedy algorithm: match debtors with creditors
        creditor_idx = 0
        debtor_idx = 0

        while creditor_idx < len(creditors) and debtor_idx < len(debtors):
            creditor_id, creditor_amount = creditors[creditor_idx]
            debtor_id, debtor_amount = debtors[debtor_idx]

            # Calculate transfer amount
            transfer_amount = min(creditor_amount, debtor_amount)

            # Create settlement entry
            plan.append(
                SettlementResponse(
                    payer_id=debtor_id,
                    payee_id=creditor_id,
                    amount=transfer_amount,
                    period_id=period_id,
                    payer_name=users[debtor_id],
                    payee_name=users[creditor_id],
                    period_name=period.name,
                )
            )

            # Update remaining amounts
            creditor_amount -= transfer_amount
            debtor_amount -= transfer_amount

            if creditor_amount == 0:
                creditor_idx += 1
            else:
                creditors[creditor_idx] = (creditor_id, creditor_amount)

            if debtor_amount == 0:
                debtor_idx += 1
            else:
                debtors[debtor_idx] = (debtor_id, debtor_amount)

        return plan

    async def apply_settlement_plan(self, period_id: int, db: AsyncSession) -> None:
        """
        Apply the settlement plan for a specific period.

        This method performs all settlement operations within a single transaction
        to ensure atomicity. If any operation fails, all changes are rolled back.

        Args:
            period_id: The ID of the period to settle
            db: Database session to use for the transaction. Should be a session
                with SERIALIZABLE isolation level for critical financial operations.

        Raises:
            NotFoundError: If period or users are not found
            BusinessRuleError: If period is not closed
        """
        try:
            # Get the settlement plan (validates period exists and is not settled)
            plan = await self.get_settlement_plan(period_id)

            # Create Settlement entities for each transfer
            for p in plan:
                settlement = Settlement(
                    period_id=p.period_id,
                    payer_id=p.payer_id,
                    payee_id=p.payee_id,
                    amount=p.amount,
                )
                await self._settlement_repository.create_settlement(settlement)

            # Update period status to SETTLED
            await self._period_service.settle_period(period_id)

            # Commit all changes atomically
            await db.commit()

        except Exception:
            # Rollback all changes if any operation fails
            await db.rollback()
            raise
