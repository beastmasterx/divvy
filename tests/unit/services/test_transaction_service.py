"""
Unit tests for TransactionService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import NotFoundError, ValidationError
from app.models import Category, Period, SplitKind, Transaction, TransactionKind, TransactionStatus, User
from app.schemas import ExpenseShareRequest, TransactionRequest
from app.services import TransactionService


@pytest.mark.unit
class TestTransactionService:
    """Test suite for TransactionService."""

    async def test_get_transaction_by_id_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving a transaction by ID when it exists."""
        # Create required dependencies
        user = await user_factory(email="payer@example.com", name="Payer")
        category = await category_factory(name="Test Category")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="Test Transaction"
        )

        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.id == transaction.id
        assert retrieved.description == "Test Transaction"

    async def test_get_transaction_by_id_not_exists(self, transaction_service: TransactionService):
        """Test retrieving a transaction by ID when it doesn't exist."""
        result = await transaction_service.get_transaction_by_id(99999)
        assert result is None

    async def test_get_transactions_by_period_id(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving transactions for a specific period."""
        # Create required dependencies
        user = await user_factory(email="payer@example.com", name="Payer")
        category = await category_factory(name="Test Category")
        period1 = await period_factory(group_id=1, name="Period 1")
        period2 = await period_factory(group_id=1, name="Period 2")

        tx1 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx2 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx3 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period2.id)

        period1_transactions = await transaction_service.get_transactions_by_period_id(period1.id)

        assert len(period1_transactions) >= 2

        transaction_ids = {tx.id for tx in period1_transactions}

        assert tx1.id in transaction_ids
        assert tx2.id in transaction_ids
        assert tx3.id not in transaction_ids

    async def test_create_transaction_expense_equal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating an expense transaction with equal split."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )

        created = await transaction_service.create_transaction(request)

        assert created.id is not None
        assert created.description == "Dinner"
        assert created.amount == 10000
        assert created.transaction_kind == TransactionKind.EXPENSE
        assert created.split_kind == SplitKind.EQUAL
        assert len(created.expense_shares or []) == 2

    async def test_create_transaction_deposit(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating a deposit transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Monthly deposit",
            amount=50000,  # $500.00
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )

        created = await transaction_service.create_transaction(request)

        assert created.id is not None
        assert created.description == "Monthly deposit"
        assert created.amount == 50000
        assert created.transaction_kind == TransactionKind.DEPOSIT

    async def test_create_transaction_expense_no_shares_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating an expense without expense_shares raises ValidationError."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Expense",
            amount=10000,
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[],  # Empty shares should raise error
        )

        with pytest.raises(ValidationError):
            await transaction_service.create_transaction(request)

    async def test_create_transaction_deposit_with_shares_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating a deposit with expense_shares raises ValidationError."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Deposit",
            amount=10000,
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user.id, transaction_id=0, share_amount=10000, share_percentage=100.0)
            ],  # Deposits shouldn't have shares
        )

        with pytest.raises(ValidationError):
            await transaction_service.create_transaction(request)

    async def test_update_transaction_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating an existing transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Original Description",
            amount=10000,
        )

        request = TransactionRequest(
            description="Updated Description",
            amount=20000,
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user.id, transaction_id=0, share_amount=20000, share_percentage=100.0)
            ],
        )

        updated = await transaction_service.update_transaction(transaction.id, request)

        assert updated.description == "Updated Description"
        assert updated.amount == 20000

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)

        assert retrieved is not None
        assert retrieved.description == "Updated Description"
        assert retrieved.amount == 20000

    async def test_update_transaction_not_exists(self, transaction_service: TransactionService):
        """Test updating a non-existent transaction raises NotFoundError."""
        request = TransactionRequest(
            description="Updated",
            amount=10000,
            payer_id=1,
            category_id=1,
            period_id=1,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=1, transaction_id=0, share_amount=10000, share_percentage=100.0)
            ],
        )

        with pytest.raises(NotFoundError):
            await transaction_service.update_transaction(99999, request)

    async def test_delete_transaction_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test deleting a transaction that exists."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="To Delete"
        )
        transaction_id = transaction.id

        # Delete it
        await transaction_service.delete_transaction(transaction_id)

        # Verify it's gone
        retrieved = await transaction_service.get_transaction_by_id(transaction_id)

        assert retrieved is None

    async def test_calculate_shares_equal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test calculating shares for equal split transaction."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        user3 = await user_factory(email="user3@example.com", name="User 3")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        # Create transaction with equal split: $10.00 / 3 = $3.33 each with 1 cent remainder
        from app.models import ExpenseShare

        transaction = await transaction_factory(
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            amount=1000,  # $10.00
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShare(user_id=user1.id),
                ExpenseShare(user_id=user2.id),
                ExpenseShare(user_id=user3.id),
            ],
        )

        shares = await transaction_service.calculate_shares_for_transaction(transaction.id)

        assert len(shares) == 3

        # Base share: 1000 / 3 = 333 cents each
        # Remainder: 1 cent goes to first user (sorted by user_id)
        total = sum(shares.values())

        assert total == 1000  # Should sum to transaction amount

        # One user should have 334 cents, others 333 cents
        share_values = sorted(shares.values())

        assert share_values == [333, 333, 334]

    async def test_calculate_shares_personal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test calculating shares for personal split transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        from app.models import ExpenseShare

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            amount=5000,  # $50.00
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[ExpenseShare(user_id=user.id)],
        )

        shares = await transaction_service.calculate_shares_for_transaction(transaction.id)

        assert len(shares) == 1
        assert shares[user.id] == 5000  # Personal expense - payer owes full amount

    async def test_calculate_shares_not_expense_returns_empty(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test that calculating shares for non-expense returns empty dict."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
        )

        shares = await transaction_service.calculate_shares_for_transaction(transaction.id)

        assert shares == {}

    async def test_calculate_shares_transaction_not_exists(self, transaction_service: TransactionService):
        """Test calculating shares for non-existent transaction raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await transaction_service.calculate_shares_for_transaction(99999)

    async def test_update_transaction_status_approve(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to APPROVED."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.APPROVED

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.APPROVED

    async def test_update_transaction_status_reject(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to REJECTED."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.REJECTED)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.REJECTED

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.REJECTED

    async def test_update_transaction_status_submit(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to PENDING (submit)."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.DRAFT,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.PENDING)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.PENDING

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.PENDING

    async def test_update_transaction_status_draft(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to DRAFT."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.DRAFT)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.DRAFT

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.DRAFT

    async def test_update_transaction_status_not_exists(self, transaction_service: TransactionService):
        """Test updating status for non-existent transaction raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await transaction_service.update_transaction_status(99999, TransactionStatus.APPROVED)
