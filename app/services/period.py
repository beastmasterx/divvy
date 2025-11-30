from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Period, PeriodStatus
from app.repositories import PeriodRepository
from app.schemas import PeriodRequest, PeriodResponse


class PeriodService:
    """Service layer for period-related business logic and operations."""

    def __init__(self, session: AsyncSession):
        self._period_repository = PeriodRepository(session)

    async def get_periods_by_group_id(self, group_id: int) -> Sequence[Period]:
        """Retrieve all periods associated with a specific group."""
        return await self._period_repository.get_periods_by_group_id(group_id)

    async def get_period_by_id(self, period_id: int) -> PeriodResponse | None:
        """Retrieve a specific period by its ID."""
        period = await self._period_repository.get_period_by_id(period_id)
        return PeriodResponse.model_validate(period) if period else None

    async def get_active_period_by_group_id(self, group_id: int) -> Period | None:
        """Retrieve the active period for a specific group."""
        return await self._period_repository.get_active_period_by_group_id(group_id)

    async def get_period_status_by_id(self, period_id: int) -> PeriodStatus | None:
        """Retrieve the status of a specific period."""
        return await self._period_repository.get_period_status_by_id(period_id)

    async def create_period(self, group_id: int, request: PeriodRequest) -> PeriodResponse:
        """Create a new period."""
        period = Period(name=request.name, group_id=group_id)
        period = await self._period_repository.create_period(period)

        return PeriodResponse.model_validate(period)

    async def update_period_name(self, period_id: int, name: str) -> PeriodResponse:
        """Update the name of an existing period."""
        # Fetch from repository (need ORM for modification)
        period = await self._period_repository.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        period.name = name
        updated_period = await self._period_repository.update_period(period)

        return PeriodResponse.model_validate(updated_period)

    async def close_period(self, period_id: int) -> PeriodResponse:
        """Close an existing period."""
        # Fetch from repository (need ORM for modification)
        period = await self._period_repository.get_period_by_id(period_id)

        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        period.end_date = period.end_date or datetime.now(UTC)
        period.status = PeriodStatus.CLOSED
        period.closed_at = datetime.now(UTC)
        updated_period = await self._period_repository.update_period(period)

        return PeriodResponse.model_validate(updated_period)

    async def settle_period(self, period_id: int) -> PeriodResponse:
        """Settle a period."""
        period = await self._period_repository.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)
        if period.status != PeriodStatus.CLOSED:
            raise BusinessRuleError(_("Period %s is not closed") % period_id)
        period.status = PeriodStatus.SETTLED
        updated_period = await self._period_repository.update_period(period)

        return PeriodResponse.model_validate(updated_period)
