from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import Transaction


class TransactionRepository:
    """Repository for managing transaction entities and their associated expense shares."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        """Retrieve a specific transaction by its ID."""
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                joinedload(Transaction.payer),
                joinedload(Transaction.category),
                joinedload(Transaction.period),
                selectinload(Transaction.expense_shares),
            )
        )
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_transactions_by_period_id(self, period_id: int) -> Sequence[Transaction]:
        """Retrieve all transactions associated with a specific period."""
        stmt = (
            select(Transaction)
            .where(Transaction.period_id == period_id)
            .options(
                joinedload(Transaction.payer),
                joinedload(Transaction.category),
                joinedload(Transaction.period),
                selectinload(Transaction.expense_shares),
            )
        )
        return (await self.session.scalars(stmt)).all()

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        """Create a new transaction and persist it to the database."""
        self.session.add(transaction)
        await self.session.flush()
        # Eagerly load relationships for response serialization
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction.id)
            .options(
                joinedload(Transaction.payer),
                joinedload(Transaction.category),
                joinedload(Transaction.period),
                selectinload(Transaction.expense_shares),
            )
        )
        return (await self.session.scalars(stmt)).one()

    async def update_transaction(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction and commit changes to the database."""
        await self.session.flush()
        # Eagerly load relationships for response serialization
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction.id)
            .options(
                joinedload(Transaction.payer),
                joinedload(Transaction.category),
                joinedload(Transaction.period),
                selectinload(Transaction.expense_shares),
            )
        )
        return (await self.session.scalars(stmt)).one()

    async def delete_transaction(self, id: int) -> None:
        """Delete a transaction by its ID if it exists."""
        stmt = delete(Transaction).where(Transaction.id == id)
        await self.session.execute(stmt)
        await self.session.flush()
