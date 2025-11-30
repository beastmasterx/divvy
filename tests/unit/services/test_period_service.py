"""
Unit tests for PeriodService.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest

from app.exceptions import NotFoundError
from app.models import Group, Period, User
from app.schemas import PeriodRequest
from app.services import PeriodService


@pytest.mark.unit
class TestPeriodService:
    """Test suite for PeriodService."""

    async def test_get_all_periods(self, period_service: PeriodService):
        """Test retrieving all periods."""
        periods = await period_service.get_all_periods()

        assert isinstance(periods, list)
        assert len(periods) == 0

    async def test_get_period_by_id_exists(
        self,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving a period by ID when it exists."""
        user = await user_factory(email="owner@example.com", name="Owner")
        group = await group_factory(name="Test Group")

        period = await period_factory(group_id=group.id, name="Test Period", created_by=user.id)

        retrieved = await period_service.get_period_by_id(period.id)

        assert retrieved is not None
        assert retrieved.id == period.id
        assert retrieved.name == "Test Period"

    async def test_get_period_by_id_not_exists(self, period_service: PeriodService):
        """Test retrieving a period by ID when it doesn't exist."""
        result = await period_service.get_period_by_id(99999)

        assert result is None

    async def test_create_period(
        self,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test creating a new period."""
        group = await group_factory(name="Test Group")
        request = PeriodRequest(name="New Period")

        created = await period_service.create_period(group.id, request)

        assert created.name == "New Period"
        assert created.group_id == group.id

    async def test_update_period_exists(
        self,
        period_service: PeriodService,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test updating an existing period."""
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Original Name")

        request = PeriodRequest(name="Updated Name")

        updated = await period_service.update_period(period.id, request)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await period_service.get_period_by_id(period.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_update_period_not_exists(self, period_service: PeriodService):
        """Test updating a non-existent period raises NotFoundError."""
        request = PeriodRequest(name="Updated Name")

        with pytest.raises(NotFoundError):
            await period_service.update_period(99999, request)

    async def test_close_period(
        self,
        period_service: PeriodService,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test closing a period."""
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="To Settle")

        settled = await period_service.close_period(period.id)

        assert settled.end_date is not None
        assert settled.is_closed is True

        # Check that the date is approximately correct (within 1 second)
        time_diff = abs((settled.end_date.replace(tzinfo=UTC) - datetime.now(UTC)).total_seconds())
        assert time_diff < 1.0

        # Verify the update persisted
        retrieved = await period_service.get_period_by_id(period.id)

        assert retrieved is not None
        assert retrieved.is_closed is True

    async def test_close_period_not_exists(self, period_service: PeriodService):
        """Test closing a non-existent period raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await period_service.close_period(99999)

    async def test_delete_period_exists_settled(
        self,
        period_service: PeriodService,
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test deleting a closed period."""
        period = await period_factory(group_id=1, name="Closed Period", end_date=datetime.now(UTC))

        # Should succeed if period is closed
        await period_service.delete_period(period.id)

        # Verify period is deleted
        retrieved = await period_service.get_period_by_id(period.id)

        assert retrieved is None

    async def test_delete_period_not_exists(self, period_service: PeriodService):
        """Test deleting a non-existent period raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await period_service.delete_period(99999)

    async def test_get_periods_by_group_id(
        self,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving periods for a specific group."""
        group = await group_factory(name="Test Group")

        # Create periods for the group
        period1 = await period_factory(group_id=group.id, name="Period 1")
        period2 = await period_factory(group_id=group.id, name="Period 2")

        # Get periods for the group
        periods = await period_service.get_periods_by_group_id(group.id)

        assert len(periods) == 2

        period_names = {p.name for p in periods}

        assert period1.name in period_names
        assert period2.name in period_names

        # Get periods for non-existent group
        periods = await period_service.get_periods_by_group_id(999)

        assert len(periods) == 0

    async def test_get_current_period_by_group_id(
        self,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving the current (unsettled) period for a group."""
        group = await group_factory(name="Test Group")

        # Create a closed period and an open period
        _ = await period_factory(group_id=group.id, name="Closed Period", end_date=datetime.now(UTC))
        open_period = await period_factory(group_id=group.id, name="Open Period")

        # Get current period (should be the open one)
        current = await period_service.get_current_period_by_group_id(group.id)

        assert current is not None
        assert current.id == open_period.id
        assert current.name == "Open Period"
        assert current.end_date is None

        # Get current period for group with no open periods
        empty_group = await group_factory(name="Empty Group")

        current = await period_service.get_current_period_by_group_id(empty_group.id)

        assert current is None
