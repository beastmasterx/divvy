"""
Unit tests for TransactionService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ExpenseShareRequest, TransactionRequest
from app.exceptions import NotFoundError, ValidationError
from app.models import SplitKind, TransactionKind
from app.services import TransactionService
from tests.fixtures.factories import create_test_category, create_test_period, create_test_transaction, create_test_user


@pytest.mark.unit
class TestTransactionService:
    """Test suite for TransactionService."""

    async def test_get_all_transactions(self, db_session: AsyncSession):
        """Test retrieving all transactions."""
        service = TransactionService(db_session)

        transactions = await service.get_all_transactions()
        assert isinstance(transactions, list)
        assert len(transactions) == 0

    async def test_get_transaction_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a transaction by ID when it exists."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="payer@example.com", name="Payer")
        category = create_test_category(name="Test Category")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="Test Transaction"
        )
        db_session.add(transaction)
        await db_session.commit()

        retrieved = await service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.id == transaction.id
        assert retrieved.description == "Test Transaction"

    async def test_get_transaction_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a transaction by ID when it doesn't exist."""
        service = TransactionService(db_session)
        result = await service.get_transaction_by_id(99999)
        assert result is None

    async def test_get_transactions_by_period_id(self, db_session: AsyncSession):
        """Test retrieving transactions for a specific period."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="payer@example.com", name="Payer")
        category = create_test_category(name="Test Category")
        period1 = create_test_period(group_id=1, name="Period 1")
        period2 = create_test_period(group_id=1, name="Period 2")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period1)
        db_session.add(period2)
        await db_session.commit()

        tx1 = create_test_transaction(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx2 = create_test_transaction(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx3 = create_test_transaction(payer_id=user.id, category_id=category.id, period_id=period2.id)
        db_session.add(tx1)
        db_session.add(tx2)
        db_session.add(tx3)
        await db_session.commit()

        period1_transactions = await service.get_transactions_by_period_id(period1.id)
        assert len(period1_transactions) >= 2
        transaction_ids = {tx.id for tx in period1_transactions}
        assert tx1.id in transaction_ids
        assert tx2.id in transaction_ids
        assert tx3.id not in transaction_ids

    async def test_create_transaction_expense_equal_split(self, db_session: AsyncSession):
        """Test creating an expense transaction with equal split."""
        service = TransactionService(db_session)

        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user1)
        db_session.add(user2)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

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

        created = await service.create_transaction(request)

        assert created.id is not None
        assert created.description == "Dinner"
        assert created.amount == 10000
        assert created.transaction_kind == TransactionKind.EXPENSE
        assert created.split_kind == SplitKind.EQUAL
        assert len(created.expense_shares or []) == 2

    async def test_create_transaction_deposit(self, db_session: AsyncSession):
        """Test creating a deposit transaction."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Deposit")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

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

        created = await service.create_transaction(request)

        assert created.id is not None
        assert created.description == "Monthly deposit"
        assert created.amount == 50000
        assert created.transaction_kind == TransactionKind.DEPOSIT

    async def test_create_transaction_expense_no_shares_raises_error(self, db_session: AsyncSession):
        """Test that creating an expense without expense_shares raises ValidationError."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

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
            await service.create_transaction(request)

    async def test_create_transaction_deposit_with_shares_raises_error(self, db_session: AsyncSession):
        """Test that creating a deposit with expense_shares raises ValidationError."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Deposit")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

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
            await service.create_transaction(request)

    async def test_update_transaction_exists(self, db_session: AsyncSession):
        """Test updating an existing transaction."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Original Description",
            amount=10000,
        )
        db_session.add(transaction)
        await db_session.commit()

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

        updated = await service.update_transaction(transaction.id, request)

        assert updated.description == "Updated Description"
        assert updated.amount == 20000

        # Verify the update persisted
        retrieved = await service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.description == "Updated Description"
        assert retrieved.amount == 20000

    async def test_update_transaction_not_exists(self, db_session: AsyncSession):
        """Test updating a non-existent transaction raises NotFoundError."""
        service = TransactionService(db_session)

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
            await service.update_transaction(99999, request)

    async def test_delete_transaction_exists(self, db_session: AsyncSession):
        """Test deleting a transaction that exists."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="To Delete"
        )
        db_session.add(transaction)
        await db_session.commit()
        transaction_id = transaction.id

        # Delete it
        await service.delete_transaction(transaction_id)

        # Verify it's gone
        retrieved = await service.get_transaction_by_id(transaction_id)
        assert retrieved is None

    async def test_calculate_shares_equal_split(self, db_session: AsyncSession):
        """Test calculating shares for equal split transaction."""
        service = TransactionService(db_session)

        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        user3 = create_test_user(email="user3@example.com", name="User 3")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user1)
        db_session.add(user2)
        db_session.add(user3)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        # Create transaction with equal split: $10.00 / 3 = $3.33 each with 1 cent remainder
        transaction = create_test_transaction(
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            amount=1000,  # $10.00
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
        )
        db_session.add(transaction)
        await db_session.commit()

        # Add expense shares
        from app.models import ExpenseShare

        share1 = ExpenseShare(transaction_id=transaction.id, user_id=user1.id)
        share2 = ExpenseShare(transaction_id=transaction.id, user_id=user2.id)
        share3 = ExpenseShare(transaction_id=transaction.id, user_id=user3.id)
        db_session.add(share1)
        db_session.add(share2)
        db_session.add(share3)
        await db_session.commit()

        shares = await service.calculate_shares_for_transaction(transaction.id)

        assert len(shares) == 3
        # Base share: 1000 / 3 = 333 cents each
        # Remainder: 1 cent goes to first user (sorted by user_id)
        total = sum(shares.values())
        assert total == 1000  # Should sum to transaction amount
        # One user should have 334 cents, others 333 cents
        share_values = sorted(shares.values())
        assert share_values == [333, 333, 334]

    async def test_calculate_shares_personal_split(self, db_session: AsyncSession):
        """Test calculating shares for personal split transaction."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Groceries")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            amount=5000,  # $50.00
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
        )
        db_session.add(transaction)
        await db_session.commit()

        # Add expense share for payer only
        from app.models import ExpenseShare

        share = ExpenseShare(transaction_id=transaction.id, user_id=user.id)
        db_session.add(share)
        await db_session.commit()

        shares = await service.calculate_shares_for_transaction(transaction.id)

        assert len(shares) == 1
        assert shares[user.id] == 5000  # Personal expense - payer owes full amount

    async def test_calculate_shares_not_expense_returns_empty(self, db_session: AsyncSession):
        """Test that calculating shares for non-expense returns empty dict."""
        service = TransactionService(db_session)

        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        category = create_test_category(name="Deposit")
        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(user)
        db_session.add(category)
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
        )
        db_session.add(transaction)
        await db_session.commit()

        shares = await service.calculate_shares_for_transaction(transaction.id)

        assert shares == {}

    async def test_calculate_shares_transaction_not_exists(self, db_session: AsyncSession):
        """Test calculating shares for non-existent transaction raises NotFoundError."""
        service = TransactionService(db_session)

        with pytest.raises(NotFoundError):
            await service.calculate_shares_for_transaction(99999)
