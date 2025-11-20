from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExpenseShare, Transaction


class TransactionRepository:
    """Repository for managing transaction entities and their associated expense shares."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_transactions(self) -> Sequence[Transaction]:
        """Retrieve all transactions from the database."""
        stmt = select(Transaction)
        return self.session.execute(stmt).scalars().all()

    def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        """Retrieve a specific transaction by its ID."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_transactions_by_period_id(self, period_id: int) -> Sequence[Transaction]:
        """Retrieve all transactions associated with a specific period."""
        stmt = select(Transaction).where(Transaction.period_id == period_id)
        return self.session.execute(stmt).scalars().all()

    def get_shared_transactions_by_user_id(self, user_id: int) -> Sequence[Transaction]:
        """Retrieve all transactions where a specific user has an expense share."""
        stmt = select(Transaction).join(ExpenseShare).where(ExpenseShare.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def create_transaction(self, transaction: Transaction) -> Transaction:
        """Create a new transaction and persist it to the database."""
        self.session.add(transaction)
        self.session.commit()
        return transaction

    def update_transaction(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction and commit changes to the database."""
        self.session.commit()
        return transaction

    def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction by its ID if it exists."""
        transaction = self.get_transaction_by_id(transaction_id)
        if transaction:
            self.session.delete(transaction)
            self.session.commit()
