from collections import defaultdict
from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import InternalServerError, NotFoundError, ValidationError
from app.models import ExpenseShare, SplitKind, Transaction, TransactionKind, TransactionStatus
from app.repositories import TransactionRepository
from app.schemas import BalanceResponse, TransactionRequest, TransactionResponse


class TransactionService:
    """Service layer for transaction-related business logic and operations."""

    def __init__(self, session: AsyncSession):
        self._transaction_repository = TransactionRepository(session)

    async def get_transaction_by_id(self, transaction_id: int) -> TransactionResponse | None:
        """Retrieve a specific transaction by its ID."""
        transaction = await self._transaction_repository.get_transaction_by_id(transaction_id)
        return TransactionResponse.model_validate(transaction) if transaction else None

    async def get_transactions_by_period_id(self, period_id: int) -> Sequence[TransactionResponse]:
        """Retrieve all transactions associated with a specific period."""
        transactions = await self._transaction_repository.get_transactions_by_period_id(period_id)
        return [TransactionResponse.model_validate(transaction) for transaction in transactions]

    async def create_transaction(self, period_id: int, request: TransactionRequest) -> TransactionResponse:
        """Create a new transaction.

        Args:
            period_id: ID of the period of the transaction
            request: Transaction request schema containing transaction data

        Returns:
            Created Transaction response DTO

        Raises:
            ValidationError: If transaction validation fails
        """
        expense_shares = [
            ExpenseShare(
                user_id=s.user_id,
                share_amount=s.share_amount,
                share_percentage=s.share_percentage,
            )
            for s in request.expense_shares or []
        ]

        self._validate_transaction(
            transaction_kind=request.transaction_kind,
            split_kind=request.split_kind,
            expense_shares=expense_shares,
            amount=request.amount,
            payer_id=request.payer_id,
        )

        transaction = Transaction(
            description=request.description,
            amount=request.amount,
            payer_id=request.payer_id,
            category_id=request.category_id,
            period_id=period_id,
            transaction_kind=request.transaction_kind,
            split_kind=request.split_kind,
            expense_shares=expense_shares,
        )
        transaction = await self._transaction_repository.create_transaction(transaction)
        return TransactionResponse.model_validate(transaction)

    async def update_transaction(self, transaction_id: int, request: TransactionRequest) -> TransactionResponse:
        """Update an existing transaction.

        Args:
            transaction_id: ID of the transaction to update
            request: Transaction request schema containing updated transaction data

        Returns:
            Updated Transaction response DTO

        Raises:
            NotFoundError: If transaction not found
            ValidationError: If transaction validation fails
        """
        # Fetch from repository (need ORM for modification)
        transaction = await self._transaction_repository.get_transaction_by_id(transaction_id)
        if not transaction:
            raise NotFoundError(_("Transaction %s not found") % transaction_id)

        expense_shares = [
            ExpenseShare(
                transaction_id=transaction_id,
                user_id=s.user_id,
                share_amount=s.share_amount,
                share_percentage=s.share_percentage,
            )
            for s in request.expense_shares or []
        ]

        self._validate_transaction(
            transaction_kind=request.transaction_kind,
            split_kind=request.split_kind,
            expense_shares=expense_shares,
            amount=request.amount,
            payer_id=request.payer_id,
            transaction_id=transaction_id,
        )

        transaction.description = request.description
        transaction.amount = request.amount
        transaction.payer_id = request.payer_id
        transaction.category_id = request.category_id
        transaction.transaction_kind = request.transaction_kind
        transaction.split_kind = request.split_kind
        transaction.status = TransactionStatus.DRAFT
        transaction.expense_shares = expense_shares

        updated_transaction = await self._transaction_repository.update_transaction(transaction)
        return TransactionResponse.model_validate(updated_transaction)

    async def update_transaction_status(self, transaction_id: int, status: TransactionStatus) -> TransactionResponse:
        """Update the status of a transaction."""
        transaction = await self._transaction_repository.get_transaction_by_id(transaction_id)
        if not transaction:
            raise NotFoundError(_("Transaction %s not found") % transaction_id)

        transaction.status = status
        updated_transaction = await self._transaction_repository.update_transaction(transaction)

        return TransactionResponse.model_validate(updated_transaction)

    async def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction by its ID."""
        return await self._transaction_repository.delete_transaction(transaction_id)

    async def _calculate_shares_for_transaction(self, transaction_id: int) -> dict[int, int]:
        """Calculate how much each user owes for a transaction.

        Args:
            transaction_id: ID of the transaction to calculate shares for

        Returns:
            dict[int, int]: {user_id: amount_owed_in_cents}

        Raises:
            NotFoundError: If transaction not found
            ValidationError: If transaction has invalid split configuration
            InternalServerError: If share calculation fails
        """
        # Fetch from repository (need ORM for relationship access)
        transaction = await self._transaction_repository.get_transaction_by_id(transaction_id)
        if not transaction:
            raise NotFoundError(_("Transaction %s not found") % transaction_id)

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

        elif transaction.split_kind == SplitKind.AMOUNT.value:
            # Amount-based split - use specified amounts
            for s in transaction.expense_shares:
                if s.share_amount is None:
                    raise ValidationError(
                        _(
                            "Transaction %(transaction_id)s has split_kind='amount' but "
                            "ExpenseShare for user %(user_id)s has no share_amount specified"
                        )
                        % {"transaction_id": transaction_id, "user_id": s.user_id}
                    )
                shares[s.user_id] = s.share_amount

            # Validate and correct remainder for amount splits
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

        elif transaction.split_kind == SplitKind.PERCENTAGE.value:
            # Percentage-based split - calculate amounts from percentages
            for s in transaction.expense_shares:
                if s.share_percentage is None:
                    raise ValidationError(
                        _(
                            "Transaction %(transaction_id)s has split_kind='percentage' but "
                            "ExpenseShare for user %(user_id)s has no share_percentage specified"
                        )
                        % {"transaction_id": transaction_id, "user_id": s.user_id}
                    )
                amount_decimal = Decimal(transaction.amount) * Decimal(str(s.share_percentage)) / 100
                shares[s.user_id] = int(amount_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))

            # Validate and correct remainder for percentage splits
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
            raise ValidationError(
                _("Transaction %(transaction_id)s has invalid split_kind: '%(split_kind)s'")
                % {"transaction_id": transaction_id, "split_kind": transaction.split_kind}
            )

        # Final validation
        total = sum(shares.values())
        if total != transaction.amount:
            raise InternalServerError(
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

    async def get_all_balances(self, period_id: int) -> Sequence[BalanceResponse]:
        """Calculate balances for all users in a specific period.

        Returns:
            Sequence[BalanceResponse]: List of user balances
                Positive balance = user is owed money
                Negative balance = user owes money

        Raises:
            ValidationError: If transaction kind is invalid
        """
        balances: dict[int, int] = defaultdict(int)
        transactions = await self.get_transactions_by_period_id(period_id)
        for transaction in transactions:
            if transaction.transaction_kind == TransactionKind.EXPENSE:
                # Credit the payer for paying the full amount
                balances[transaction.payer_id] += transaction.amount

                # Debit each participant for their share
                shares = await self._calculate_shares_for_transaction(transaction.id)
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
        return [BalanceResponse(user_id=user_id, balance=balance) for user_id, balance in balances.items()]

    def _validate_transaction(
        self,
        transaction_kind: TransactionKind,
        split_kind: SplitKind,
        expense_shares: list[ExpenseShare],
        amount: int,
        payer_id: int,
        transaction_id: int | None = None,
    ) -> None:
        """Validate transaction consistency including transaction_kind, split_kind, and expense_shares.

        This method validates:
        - Only EXPENSE transactions can have expense_shares
        - EXPENSE transactions must have expense_shares
        - split_kind consistency with expense_shares (personal, equal, amount, percentage)
        - Amount/percentage split totals add up correctly

        Args:
            transaction_kind: The type of transaction (expense, deposit, refund)
            split_kind: How the transaction is split (personal, equal, amount, percentage)
            expense_shares: List of expense shares
            amount: Transaction amount in cents
            payer_id: ID of the user who paid
            transaction_id: Optional transaction ID for error messages

        Raises:
            ValidationError: If validation fails.
        """
        transaction_ref = f"Transaction {transaction_id}" if transaction_id else "Transaction"
        num_shares = len(expense_shares)

        # Validate transaction_kind vs expense_shares relationship
        if transaction_kind != TransactionKind.EXPENSE:
            # Only EXPENSE transactions can have expense_shares
            if expense_shares:
                raise ValidationError(
                    _(
                        "%(ref)s has transaction_kind='%(kind)s' but has expense_shares. "
                        "Only 'expense' transactions can have expense shares."
                    )
                    % {"ref": transaction_ref, "kind": transaction_kind.value}
                )
            # Deposits and refunds don't need split_kind validation
            return

        # EXPENSE transactions must have expense_shares
        if not expense_shares:
            raise ValidationError(
                _(
                    "%(ref)s has transaction_kind='expense' but has no expense_shares. "
                    "Expense transactions must have at least one expense share."
                )
                % {"ref": transaction_ref}
            )

        # Validate split_kind consistency with expense_shares
        # Personal split should have exactly one share
        if split_kind == SplitKind.PERSONAL:
            if num_shares != 1:
                raise ValidationError(
                    _(
                        "%(ref)s has split_kind='personal' but has %(num)d shares. "
                        "Personal transactions must have exactly 1 share."
                    )
                    % {"ref": transaction_ref, "num": num_shares}
                )
            # Verify the single share is the payer
            if expense_shares[0].user_id != payer_id:
                raise ValidationError(
                    _(
                        "%(ref)s has split_kind='personal' but the share is not for the payer. "
                        "Personal expenses must be shared only by the payer."
                    )
                    % {"ref": transaction_ref}
                )

        # Equal splits should have at least one share
        elif split_kind == SplitKind.EQUAL:
            if num_shares < 1:
                raise ValidationError(
                    _("%(ref)s has split_kind='equal' but has no expense shares. " "At least one share is required.")
                    % {"ref": transaction_ref}
                )

        # Amount-based splits: validate all shares have share_amount and totals match
        elif split_kind == SplitKind.AMOUNT:
            if num_shares < 1:
                raise ValidationError(
                    _("%(ref)s has split_kind='amount' but has no expense shares. " "At least one share is required.")
                    % {"ref": transaction_ref}
                )

            total_amount = 0
            for share in expense_shares:
                if share.share_amount is None:
                    raise ValidationError(
                        _(
                            "%(ref)s has split_kind='amount' but ExpenseShare for user "
                            "%(user_id)s has no share_amount specified."
                        )
                        % {"ref": transaction_ref, "user_id": share.user_id}
                    )
                total_amount += share.share_amount

            # Validate totals match transaction amount
            if total_amount != amount:
                raise ValidationError(
                    _("%(ref)s share amounts total %(total)d cents but " "transaction amount is %(amount)d cents.")
                    % {"ref": transaction_ref, "total": total_amount, "amount": amount}
                )

        # Percentage-based splits: validate all shares have share_percentage and total 100%
        elif split_kind == SplitKind.PERCENTAGE:
            if num_shares < 1:
                raise ValidationError(
                    _(
                        "%(ref)s has split_kind='percentage' but has no expense shares. "
                        "At least one share is required."
                    )
                    % {"ref": transaction_ref}
                )

            total_percentage = 0.0
            for share in expense_shares:
                if share.share_percentage is None:
                    raise ValidationError(
                        _(
                            "%(ref)s has split_kind='percentage' but ExpenseShare for user "
                            "%(user_id)s has no share_percentage specified."
                        )
                        % {"ref": transaction_ref, "user_id": share.user_id}
                    )
                total_percentage += share.share_percentage

            # Validate that the percentages add up to 100.0%
            if abs(total_percentage - 100.0) > 0.0:
                raise ValidationError(
                    _("%(ref)s share percentages total %(total).1f%% but " "must equal 100%%")
                    % {"ref": transaction_ref, "total": total_percentage}
                )
