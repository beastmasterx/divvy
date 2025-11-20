from collections.abc import Sequence

from sqlalchemy.orm import Session

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

    def create_period(self, period: Period) -> Period:
        """Create a new period."""
        return self.period_repository.create_period(period)

    def update_period(self, period: Period) -> Period:
        """Update an existing period."""
        return self.period_repository.update_period(period)

    def delete_period(self, period_id: int) -> None:
        """Delete a period by its ID."""
        return self.period_repository.delete_period(period_id)
