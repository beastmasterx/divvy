from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy.orm import Session

from app.core.i18n import _
from app.models.models import SplitKind, Transaction, TransactionKind
from app.repositories.transaction import TransactionRepository


class TransactionService:
    """Service layer for transaction-related business logic and operations."""

    def __init__(self, session: Session):
        self.transaction_repository = TransactionRepository(session)

    def get_all_transactions(self) -> Sequence[Transaction]:
        """Retrieve all transactions."""
        return self.transaction_repository.get_all_transactions()

    def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        """Retrieve a specific transaction by its ID."""
        return self.transaction_repository.get_transaction_by_id(transaction_id)

    def create_transaction(self, transaction: Transaction) -> Transaction:
        """Create a new transaction."""
        return self.transaction_repository.create_transaction(transaction)

    def update_transaction(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        return self.transaction_repository.update_transaction(transaction)

    def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction by its ID."""
        return self.transaction_repository.delete_transaction(transaction_id)

    def get_transactions_by_period_id(self, period_id: int) -> Sequence[Transaction]:
        """Retrieve all transactions associated with a specific period."""
        return self.transaction_repository.get_transactions_by_period_id(period_id)

    def get_shared_transactions_by_user_id(self, user_id: int) -> Sequence[Transaction]:
        """Retrieve all transactions where a specific user has an expense share."""
        return self.transaction_repository.get_shared_transactions_by_user_id(user_id)

    def calculate_shares_for_transaction(self, transaction_id: int) -> dict[int, int]:
        """Calculate how much each user owes for a transaction.

        Args:
            transaction_id: ID of the transaction to calculate shares for

        Returns:
            dict[int, int]: {user_id: amount_owed_in_cents}

        Raises:
            ValueError: If transaction not found or has invalid split configuration
        """
        transaction = self.get_transaction_by_id(transaction_id)
        if not transaction:
            raise ValueError(_("Transaction %s not found") % transaction_id)

        # Edge case: no expense shares
        if transaction.transaction_kind != TransactionKind.EXPENSE or not transaction.expense_shares:
            return {}

        shares: dict[int, int] = {}

        # Calculate shares based on split kind
        if transaction.split_kind == SplitKind.PERSONAL.value:
            # Personal expense - only one person (should be the payer)
            for s in transaction.expense_shares:
                shares[s.user_id] = transaction.amount

        elif transaction.split_kind == SplitKind.EQUAL.value:
            # Equal split - divide equally among all participants
            num_participants = len(transaction.expense_shares)
            base_share = transaction.amount // num_participants
            remainder = transaction.amount % num_participants

            # Assign base shares to everyone
            for s in transaction.expense_shares:
                shares[s.user_id] = base_share

            # Distribute remainder to first N users (sorted by user_id)
            if remainder > 0:
                sorted_user_ids = sorted(shares.keys())
                for i in range(remainder):
                    shares[sorted_user_ids[i]] += 1

        elif transaction.split_kind == SplitKind.CUSTOM.value:
            # Custom split - use specified amount or percentage
            for s in transaction.expense_shares:
                if s.share_amount is not None:
                    shares[s.user_id] = s.share_amount
                elif s.share_percentage is not None:
                    amount_decimal = Decimal(transaction.amount) * Decimal(str(s.share_percentage)) / 100
                    shares[s.user_id] = int(amount_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
                else:
                    raise ValueError(
                        _(
                            "Transaction %(transaction_id)s has split_kind='custom' but "
                            "ExpenseShare for user %(user_id)s has no share_amount or "
                            "share_percentage specified"
                        )
                        % {"transaction_id": transaction_id, "user_id": s.user_id}
                    )

            # Validate and correct remainder for custom splits
            total_shares = sum(shares.values())
            remainder = transaction.amount - total_shares

            if remainder != 0:
                # Distribute remainder to first N users (sorted for determinism)
                sorted_user_ids = sorted(shares.keys())
                if remainder > 0:
                    for i in range(remainder):
                        shares[sorted_user_ids[i]] += 1
                else:  # remainder < 0
                    for i in range(abs(remainder)):
                        shares[sorted_user_ids[i]] -= 1
        else:
            raise ValueError(
                _("Transaction %(transaction_id)s has invalid split_kind: '%(split_kind)s'")
                % {"transaction_id": transaction_id, "split_kind": transaction.split_kind}
            )

        # Final validation
        total = sum(shares.values())
        if total != transaction.amount:
            raise RuntimeError(
                _(
                    "Share calculation error for transaction %(transaction_id)s: "
                    "shares sum to %(total)s but transaction amount is %(amount)s"
                )
                % {
                    "transaction_id": transaction_id,
                    "total": total,
                    "amount": transaction.amount,
                }
            )

        return shares
