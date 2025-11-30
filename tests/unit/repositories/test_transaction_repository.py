"""
Unit tests for TransactionRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SplitKind, Transaction, TransactionKind
from app.repositories import TransactionRepository
from tests.fixtures.factories import create_test_transaction


@pytest.mark.unit
class TestTransactionRepository:
    """Test suite for TransactionRepository."""

    @pytest.fixture
    def transaction_repository(self, db_session: AsyncSession) -> TransactionRepository:
        return TransactionRepository(db_session)

    async def test_get_transaction_by_id_exists(
        self, transaction_repository: TransactionRepository, transaction_factory: Callable[..., Awaitable[Transaction]]
    ):
        """Test retrieving a transaction by ID when it exists."""
        transaction = await transaction_factory(
            description="Test Transaction", amount=5000, payer_id=1, category_id=1, period_id=1
        )

        retrieved = await transaction_repository.get_transaction_by_id(transaction.id)

        assert retrieved is not None
        assert retrieved.id == transaction.id
        assert retrieved.description == transaction.description
        assert retrieved.amount == 5000

    async def test_get_transaction_by_id_not_exists(self, transaction_repository: TransactionRepository):
        """Test retrieving a transaction by ID when it doesn't exist."""
        result = await transaction_repository.get_transaction_by_id(99999)

        assert result is None

    async def test_get_transactions_by_period_id(
        self, transaction_repository: TransactionRepository, transaction_factory: Callable[..., Awaitable[Transaction]]
    ):
        """Test retrieving transactions for a specific period."""
        # Create transactions for different periods
        tx1 = await transaction_factory(period_id=1, description="Period 1 TX")
        tx2 = await transaction_factory(period_id=1, description="Period 1 TX 2")
        tx3 = await transaction_factory(period_id=2, description="Period 2 TX")

        period_1_transactions = await transaction_repository.get_transactions_by_period_id(1)

        assert len(period_1_transactions) >= 2

        descriptions = {tx.description for tx in period_1_transactions if tx.description}

        assert tx1.description in descriptions
        assert tx2.description in descriptions
        assert tx3.description not in descriptions

    async def test_create_transaction(self, transaction_repository: TransactionRepository):
        """Test creating a new transaction."""
        transaction = create_test_transaction(
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            amount=15000,
            description="New Transaction",
            payer_id=1,
            category_id=1,
            period_id=1,
        )

        created = await transaction_repository.create_transaction(transaction)

        assert created.id is not None
        assert created.amount == 15000
        assert created.description == "New Transaction"
        assert created.transaction_kind == TransactionKind.EXPENSE

        # Verify it's in the database
        retrieved = await transaction_repository.get_transaction_by_id(created.id)

        assert retrieved is not None
        assert retrieved.amount == 15000

    async def test_update_transaction(
        self, transaction_repository: TransactionRepository, transaction_factory: Callable[..., Awaitable[Transaction]]
    ):
        """Test updating an existing transaction."""
        # Create a transaction
        transaction = await transaction_factory(
            description="Original Description", amount=10000, payer_id=1, category_id=1, period_id=1
        )
        # Update it
        transaction.description = "Updated Description"
        transaction.amount = 20000

        updated = await transaction_repository.update_transaction(transaction)

        assert updated.description == "Updated Description"
        assert updated.amount == 20000

        # Verify the update persisted
        retrieved = await transaction_repository.get_transaction_by_id(transaction.id)

        assert retrieved is not None
        assert retrieved.description == "Updated Description"
        assert retrieved.amount == 20000

    async def test_delete_transaction_exists(
        self, transaction_repository: TransactionRepository, transaction_factory: Callable[..., Awaitable[Transaction]]
    ):
        """Test deleting a transaction that exists."""
        # Create a transaction
        transaction = await transaction_factory(description="To Delete", payer_id=1, category_id=1, period_id=1)

        # Delete it
        await transaction_repository.delete_transaction(transaction.id)

        # Verify it's gone
        retrieved = await transaction_repository.get_transaction_by_id(transaction.id)

        assert retrieved is None

    async def test_delete_transaction_not_exists(self, transaction_repository: TransactionRepository):
        """Test deleting a transaction that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await transaction_repository.delete_transaction(99999)
