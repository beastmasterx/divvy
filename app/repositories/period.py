from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Period


class PeriodRepository:
    """Repository for managing period entities, which represent time-based expense tracking intervals."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_periods(self) -> Sequence[Period]:
        """Retrieve all periods from the database."""
        stmt = select(Period)
        return self.session.execute(stmt).scalars().all()

    def get_period_by_id(self, period_id: int) -> Period | None:
        """Retrieve a specific period by its ID."""
        stmt = select(Period).where(Period.id == period_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_period(self, period: Period) -> Period:
        """Create a new period and persist it to the database."""
        self.session.add(period)
        self.session.commit()
        return period

    def update_period(self, period: Period) -> Period:
        """Update an existing period and commit changes to the database."""
        self.session.commit()
        return period

    def delete_period(self, period_id: int) -> None:
        """Delete a period by its ID if it exists."""
        period = self.get_period_by_id(period_id)
        if period:
            self.session.delete(period)
            self.session.commit()
