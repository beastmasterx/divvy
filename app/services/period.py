from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.api.schemas import PeriodCreateRequest, PeriodResponse, PeriodUpdateRequest
from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models.models import Period
from app.repositories import PeriodRepository


class PeriodService:
    """Service layer for period-related business logic and operations."""

    def __init__(self, session: Session):
        self.period_repository = PeriodRepository(session)

    def get_all_periods(self) -> Sequence[PeriodResponse]:
        """Retrieve all periods."""
        periods = self.period_repository.get_all_periods()
        return [PeriodResponse.model_validate(period) for period in periods]

    def get_period_by_id(self, period_id: int) -> PeriodResponse | None:
        """Retrieve a specific period by its ID."""
        period = self.period_repository.get_period_by_id(period_id)
        return PeriodResponse.model_validate(period) if period else None

    def _validate_start_date(self, start_date: datetime | None) -> datetime:
        date: datetime = start_date if start_date else datetime.now(UTC)

        if date > datetime.now(UTC):
            raise BusinessRuleError(_("Period start date cannot be in the future"))

        return date

    def create_period(self, request: PeriodCreateRequest) -> PeriodResponse:
        """Create a new period."""
        period = Period(name=request.name, group_id=request.group_id)
        period.start_date = self._validate_start_date(request.start_date)
        period = self.period_repository.create_period(period)
        return PeriodResponse.model_validate(period)

    def update_period(self, period_id: int, request: PeriodUpdateRequest) -> PeriodResponse:
        """Update an existing period."""
        # Fetch from repository (need ORM for modification)
        period = self.period_repository.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if request.name:
            period.name = request.name

        if request.start_date:
            period.start_date = self._validate_start_date(request.start_date)

        updated_period = self.period_repository.update_period(period)
        return PeriodResponse.model_validate(updated_period)

    def close_period(self, period_id: int) -> PeriodResponse:
        """Close an existing period."""
        # Fetch from repository (need ORM for modification)
        period = self.period_repository.get_period_by_id(period_id)

        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if period.is_closed:
            raise BusinessRuleError(_("Period %s is already settled") % period_id)

        period.end_date = datetime.now(UTC)
        updated_period = self.period_repository.update_period(period)
        return PeriodResponse.model_validate(updated_period)

    def delete_period(self, period_id: int) -> None:
        """Delete a period by its ID."""
        # Fetch from repository (need ORM for relationship access)
        period = self.period_repository.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if not period.is_closed and period.transactions:
            raise BusinessRuleError(
                _(
                    "Period %s is not settled and has transactions. Please settle the period or delete the transactions first."
                )
                % period_id
            )

        return self.period_repository.delete_period(period_id)
