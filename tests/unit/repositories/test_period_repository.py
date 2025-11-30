"""
Unit tests for PeriodRepository.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, Period
from app.repositories import PeriodRepository
from tests.fixtures.factories import create_test_period


@pytest.mark.unit
class TestPeriodRepository:
    """Test suite for PeriodRepository."""

    @pytest.fixture
    def period_repository(self, db_session: AsyncSession) -> PeriodRepository:
        return PeriodRepository(db_session)

    async def test_get_all_periods_empty(self, period_repository: PeriodRepository):
        """Test retrieving all periods when database is empty."""
        periods = await period_repository.get_all_periods()
        assert isinstance(periods, list)
        assert len(periods) == 0

    async def test_get_all_periods_multiple(
        self,
        period_repository: PeriodRepository,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving all periods when multiple exist."""
        # Create multiple periods (requires group_id)
        group = await group_factory(name="Test Group")
        period1 = await period_factory(group_id=group.id, name="Period 1")
        period2 = await period_factory(group_id=group.id, name="Period 2")

        periods = await period_repository.get_all_periods()

        assert len(periods) >= 2
        period_names = {p.name for p in periods}
        assert period1.name in period_names
        assert period2.name in period_names

    async def test_get_period_by_id_exists(
        self, period_repository: PeriodRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test retrieving a period by ID when it exists."""
        period = await period_factory(group_id=1, name="Test Period")

        retrieved = await period_repository.get_period_by_id(period.id)
        assert retrieved is not None
        assert retrieved.id == period.id
        assert retrieved.name == period.name

    async def test_get_period_by_id_not_exists(self, period_repository: PeriodRepository):
        """Test retrieving a period by ID when it doesn't exist."""
        result = await period_repository.get_period_by_id(99999)
        assert result is None

    async def test_create_period(self, period_repository: PeriodRepository):
        """Test creating a new period."""
        period = create_test_period(group_id=1, name="New Period")
        created = await period_repository.create_period(period)

        assert created.id is not None
        assert created.name == "New Period"
        assert created.is_closed is False
        assert created.group_id == 1

        # Verify it's in the database
        retrieved = await period_repository.get_period_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Period"

    async def test_update_period(
        self, period_repository: PeriodRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test updating an existing period."""
        # Create a period
        period = await period_factory(group_id=1, name="Original Name")

        # Update it
        period.name = "Updated Name"
        period.end_date = datetime.now(UTC)
        updated = await period_repository.update_period(period)

        assert updated.name == "Updated Name"
        assert updated.is_closed is True

        # Verify the update persisted
        retrieved = await period_repository.get_period_by_id(period.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.is_closed is True

    async def test_delete_period_exists(
        self, period_repository: PeriodRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test deleting a period that exists."""
        # Create a period
        period = await period_factory(group_id=1, name="To Delete")

        # Delete it
        await period_repository.delete_period(period.id)

        # Verify it's gone
        retrieved = await period_repository.get_period_by_id(period.id)

        assert retrieved is None

    async def test_delete_period_not_exists(self, period_repository: PeriodRepository):
        """Test deleting a period that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await period_repository.delete_period(99999)

    async def test_get_periods_by_group_id(
        self, period_repository: PeriodRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test retrieving periods for a specific group."""

        # Create periods for different groups
        period1 = await period_factory(group_id=1, name="Period 1")
        period2 = await period_factory(group_id=1, name="Period 2")
        period3 = await period_factory(group_id=2, name="Period 3")

        # Get periods for group 1
        periods = await period_repository.get_periods_by_group_id(1)

        assert len(periods) == 2

        period_names = {p.name for p in periods}

        assert period1.name in period_names
        assert period2.name in period_names
        assert period3.name not in period_names

        # Get periods for group 2
        periods = await period_repository.get_periods_by_group_id(2)

        assert len(periods) == 1
        assert periods[0].name == period3.name

        # Get periods for non-existent group
        periods = await period_repository.get_periods_by_group_id(999)

        assert len(periods) == 0

    async def test_get_current_period_by_group_id(
        self, period_repository: PeriodRepository, period_factory: Callable[..., Awaitable[Period]]
    ):
        """Test retrieving the current (unsettled) period for a group."""
        from datetime import UTC, datetime

        # Create a closed period and an open period for group 1
        _ = await period_factory(group_id=1, name="Closed Period", end_date=datetime.now(UTC))
        open_period = await period_factory(group_id=1, name="Open Period")

        # Get current period for group 1 (should be the open one)
        current = await period_repository.get_active_period_by_group_id(1)

        assert current is not None
        assert current.id == open_period.id
        assert current.name == open_period.name
        assert current.end_date is None

        # Get current period for group with no open periods
        current = await period_repository.get_active_period_by_group_id(2)

        assert current is None
