from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Settlement


class SettlementRepository:
    """Repository for managing settlement entities representing money transfers between users."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_settlement_by_id(self, settlement_id: int) -> Settlement | None:
        """Retrieve a specific settlement by its ID."""
        stmt = (
            select(Settlement)
            .where(Settlement.id == settlement_id)
            .options(
                joinedload(Settlement.period),
                joinedload(Settlement.payer),
                joinedload(Settlement.payee),
            )
        )
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_settlements_by_period_id(self, period_id: int) -> Sequence[Settlement]:
        """Retrieve all settlements associated with a specific period."""
        stmt = (
            select(Settlement)
            .where(Settlement.period_id == period_id)
            .options(
                joinedload(Settlement.period),
                joinedload(Settlement.payer),
                joinedload(Settlement.payee),
            )
        )
        return (await self.session.scalars(stmt)).all()

    async def create_settlement(self, settlement: Settlement) -> Settlement:
        """Create a new settlement and persist it to the database."""
        self.session.add(settlement)
        await self.session.flush()
        # Eagerly load relationships for response serialization
        stmt = (
            select(Settlement)
            .where(Settlement.id == settlement.id)
            .options(
                joinedload(Settlement.period),
                joinedload(Settlement.payer),
                joinedload(Settlement.payee),
            )
        )
        return (await self.session.scalars(stmt)).one()
