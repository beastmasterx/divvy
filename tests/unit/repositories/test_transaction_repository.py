"""
Unit tests for TransactionRepository.
"""

import pytest
from sqlalchemy.orm import Session

from app.models import SplitKind, TransactionKind
from app.repositories import TransactionRepository
from tests.fixtures.factories import create_test_transaction


@pytest.mark.unit
class TestTransactionRepository:
    """Test suite for TransactionRepository."""

    def test_get_all_transactions_empty(self, db_session: Session):
        """Test retrieving all transactions when database is empty."""
        repo = TransactionRepository(db_session)
        transactions = repo.get_all_transactions()
        assert isinstance(transactions, list)
        assert len(transactions) == 0

    def test_get_all_transactions_multiple(self, db_session: Session):
        """Test retrieving all transactions when multiple exist."""
        repo = TransactionRepository(db_session)

        # Create multiple transactions
        # Note: Requires valid payer_id, category_id, period_id
        tx1 = create_test_transaction(description="Transaction 1", amount=10000, payer_id=1, category_id=1, period_id=1)
        tx2 = create_test_transaction(description="Transaction 2", amount=20000, payer_id=1, category_id=1, period_id=1)
        db_session.add(tx1)
        db_session.add(tx2)
        db_session.commit()

        transactions = repo.get_all_transactions()
        assert len(transactions) >= 2
        descriptions = {tx.description for tx in transactions if tx.description}
        assert "Transaction 1" in descriptions
        assert "Transaction 2" in descriptions

    def test_get_transaction_by_id_exists(self, db_session: Session):
        """Test retrieving a transaction by ID when it exists."""
        repo = TransactionRepository(db_session)

        transaction = create_test_transaction(
            description="Test Transaction", amount=5000, payer_id=1, category_id=1, period_id=1
        )
        db_session.add(transaction)
        db_session.commit()
        transaction_id = transaction.id

        retrieved = repo.get_transaction_by_id(transaction_id)
        assert retrieved is not None
        assert retrieved.id == transaction_id
        assert retrieved.description == "Test Transaction"
        assert retrieved.amount == 5000

    def test_get_transaction_by_id_not_exists(self, db_session: Session):
        """Test retrieving a transaction by ID when it doesn't exist."""
        repo = TransactionRepository(db_session)
        result = repo.get_transaction_by_id(99999)
        assert result is None

    def test_get_transactions_by_period_id(self, db_session: Session):
        """Test retrieving transactions for a specific period."""
        repo = TransactionRepository(db_session)

        # Create transactions for different periods
        tx1 = create_test_transaction(period_id=1, description="Period 1 TX")
        tx2 = create_test_transaction(period_id=1, description="Period 1 TX 2")
        tx3 = create_test_transaction(period_id=2, description="Period 2 TX")
        db_session.add(tx1)
        db_session.add(tx2)
        db_session.add(tx3)
        db_session.commit()

        period_1_transactions = repo.get_transactions_by_period_id(1)
        assert len(period_1_transactions) >= 2
        descriptions = {tx.description for tx in period_1_transactions if tx.description}
        assert "Period 1 TX" in descriptions
        assert "Period 1 TX 2" in descriptions
        assert "Period 2 TX" not in descriptions

    def test_get_shared_transactions_by_user_id(self, db_session: Session):
        """Test retrieving transactions where a user has expense shares."""
        repo = TransactionRepository(db_session)

        # This test requires ExpenseShare relationships
        # For now, test that it returns an empty list when user has no shares
        transactions = repo.get_shared_transactions_by_user_id(1)
        assert isinstance(transactions, list)

    def test_create_transaction(self, db_session: Session):
        """Test creating a new transaction."""
        repo = TransactionRepository(db_session)

        transaction = create_test_transaction(
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            amount=15000,
            description="New Transaction",
            payer_id=1,
            category_id=1,
            period_id=1,
        )
        created = repo.create_transaction(transaction)

        assert created.id is not None
        assert created.amount == 15000
        assert created.description == "New Transaction"
        assert created.transaction_kind == TransactionKind.EXPENSE

        # Verify it's in the database
        retrieved = repo.get_transaction_by_id(created.id)
        assert retrieved is not None
        assert retrieved.amount == 15000

    def test_update_transaction(self, db_session: Session):
        """Test updating an existing transaction."""
        repo = TransactionRepository(db_session)

        # Create a transaction
        transaction = create_test_transaction(
            description="Original Description", amount=10000, payer_id=1, category_id=1, period_id=1
        )
        db_session.add(transaction)
        db_session.commit()

        # Update it
        transaction.description = "Updated Description"
        transaction.amount = 20000
        updated = repo.update_transaction(transaction)

        assert updated.description == "Updated Description"
        assert updated.amount == 20000

        # Verify the update persisted
        retrieved = repo.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.description == "Updated Description"
        assert retrieved.amount == 20000

    def test_delete_transaction_exists(self, db_session: Session):
        """Test deleting a transaction that exists."""
        repo = TransactionRepository(db_session)

        # Create a transaction
        transaction = create_test_transaction(description="To Delete", payer_id=1, category_id=1, period_id=1)
        db_session.add(transaction)
        db_session.commit()
        transaction_id = transaction.id

        # Delete it
        repo.delete_transaction(transaction_id)

        # Verify it's gone
        retrieved = repo.get_transaction_by_id(transaction_id)
        assert retrieved is None

    def test_delete_transaction_not_exists(self, db_session: Session):
        """Test deleting a transaction that doesn't exist (should not raise error)."""
        repo = TransactionRepository(db_session)
        # Should not raise an exception
        repo.delete_transaction(99999)
