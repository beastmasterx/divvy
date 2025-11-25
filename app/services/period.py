from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models.models import Period
from app.repositories import PeriodRepository
from app.schemas import PeriodCreateRequest, PeriodResponse, PeriodUpdateRequest


class PeriodService:
    """Service layer for period-related business logic and operations."""

    def __init__(self, session: AsyncSession):
        self.period_repository = PeriodRepository(session)

    async def get_all_periods(self) -> Sequence[PeriodResponse]:
        """Retrieve all periods."""
        periods = await self.period_repository.get_all_periods()
        return [PeriodResponse.model_validate(period) for period in periods]

    async def get_period_by_id(self, period_id: int) -> PeriodResponse | None:
        """Retrieve a specific period by its ID."""
        period = await self.period_repository.get_period_by_id(period_id)
        return PeriodResponse.model_validate(period) if period else None

    async def _validate_start_date(self, start_date: datetime | None) -> datetime:
        date: datetime = start_date if start_date else datetime.now(UTC)

        if date > datetime.now(UTC):
            raise BusinessRuleError(_("Period start date cannot be in the future"))

        return date

    async def create_period(self, request: PeriodCreateRequest) -> PeriodResponse:
        """Create a new period."""
        period = Period(name=request.name, group_id=request.group_id)
        period.start_date = await self._validate_start_date(request.start_date)
        period = await self.period_repository.create_period(period)
        return PeriodResponse.model_validate(period)

    async def update_period(self, period_id: int, request: PeriodUpdateRequest) -> PeriodResponse:
        """Update an existing period."""
        # Fetch from repository (need ORM for modification)
        period = await self.period_repository.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if request.name:
            period.name = request.name

        if request.start_date:
            period.start_date = await self._validate_start_date(request.start_date)

        updated_period = await self.period_repository.update_period(period)
        return PeriodResponse.model_validate(updated_period)

    async def close_period(self, period_id: int) -> PeriodResponse:
        """Close an existing period."""
        # Fetch from repository (need ORM for modification)
        period = await self.period_repository.get_period_by_id(period_id)

        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if period.is_closed:
            raise BusinessRuleError(_("Period %s is already settled") % period_id)

        period.end_date = datetime.now(UTC)
        updated_period = await self.period_repository.update_period(period)
        return PeriodResponse.model_validate(updated_period)

    async def delete_period(self, id: int) -> None:
        """Delete a period by its ID."""
        # Fetch from repository (need ORM for relationship access)
        period = await self.period_repository.get_period_by_id(id)
        if not period:
            raise NotFoundError(_("Period %s not found") % id)

        if not period.is_closed and period.transactions:
            raise BusinessRuleError(
                _(
                    "Period %s is not settled and has transactions. Please settle the period or delete the transactions first."
                )
                % id
            )

        await self.period_repository.delete_period(id)
