from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.api.schemas import PeriodRequest
from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models.models import Period
from app.repositories import PeriodRepository


class PeriodService:
    """Service layer for period-related business logic and operations."""

    def __init__(self, session: Session):
        self.period_repository = PeriodRepository(session)

    def get_all_periods(self) -> Sequence[Period]:
        """Retrieve all periods."""
        return self.period_repository.get_all_periods()

    def get_period_by_id(self, period_id: int) -> Period | None:
        """Retrieve a specific period by its ID."""
        return self.period_repository.get_period_by_id(period_id)

    def create_period(self, p: PeriodRequest) -> Period:
        """Create a new period."""
        period = Period(name=p.name, start_date=p.start_date, end_date=p.end_date)
        return self.period_repository.create_period(period)

    def update_period(self, period_id: int, p: PeriodRequest) -> Period:
        """Update an existing period."""
        period = self.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)
        period.name = p.name
        period.start_date = p.start_date
        period.end_date = p.end_date
        return self.period_repository.update_period(period)

    def delete_period(self, period_id: int) -> None:
        """Delete a period by its ID."""
        period = self.get_period_by_id(period_id)
        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        if not period.is_settled and period.transactions:
            raise BusinessRuleError(
                _(
                    "Period %s is not settled and has transactions. Please settle the period or delete the transactions first."
                )
                % period_id
            )

        return self.period_repository.delete_period(period_id)
