from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Period, PeriodStatus


class PeriodRepository:
    """Repository for managing period entities, which represent time-based expense tracking intervals."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_periods_by_group_id(self, group_id: int) -> Sequence[Period]:
        """Retrieve all periods associated with a specific group."""
        stmt = select(Period).where(Period.group_id == group_id)
        return (await self.session.scalars(stmt)).all()

    async def get_period_by_id(self, id: int) -> Period | None:
        """Retrieve a specific period by its ID."""
        return await self.session.get(Period, id)

    async def get_active_period_by_group_id(self, group_id: int) -> Period | None:
        """Retrieve the active period for a specific group."""
        stmt = (
            select(Period)
            .where(Period.group_id == group_id, Period.status == PeriodStatus.OPEN)
            .options(selectinload(Period.transactions))
        )
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_period_status_by_id(self, period_id: int) -> PeriodStatus | None:
        """Retrieve the status of a specific period."""
        stmt = select(Period.status).where(Period.id == period_id)
        return (await self.session.scalars(stmt)).one_or_none()

    async def create_period(self, period: Period) -> Period:
        """Create a new period and persist it to the database."""
        self.session.add(period)
        await self.session.flush()
        return period

    async def update_period(self, period: Period) -> Period:
        """Update an existing period and commit changes to the database."""
        await self.session.flush()
        return period

    async def delete_period(self, id: int) -> None:
        """Delete a period by its ID if it exists."""
        stmt = delete(Period).where(Period.id == id)
        await self.session.execute(stmt)
        await self.session.flush()
