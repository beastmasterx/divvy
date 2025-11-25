"""
Unit tests for PeriodService.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PeriodCreateRequest, PeriodUpdateRequest
from app.exceptions import NotFoundError
from app.services import PeriodService
from tests.fixtures.factories import create_test_group, create_test_period, create_test_user


@pytest.mark.unit
class TestPeriodService:
    """Test suite for PeriodService."""

    async def test_get_all_periods(self, db_session: AsyncSession):
        """Test retrieving all periods."""
        service = PeriodService(db_session)

        periods = await service.get_all_periods()
        assert isinstance(periods, list)
        assert len(periods) == 0

    async def test_get_period_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a period by ID when it exists."""
        service = PeriodService(db_session)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period", created_by=user.id)
        db_session.add(period)
        await db_session.commit()

        retrieved = await service.get_period_by_id(period.id)
        assert retrieved is not None
        assert retrieved.id == period.id
        assert retrieved.name == "Test Period"

    async def test_get_period_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a period by ID when it doesn't exist."""
        service = PeriodService(db_session)
        result = await service.get_period_by_id(99999)
        assert result is None

    async def test_create_period(self, db_session: AsyncSession):
        """Test creating a new period."""
        from tests.fixtures.factories import create_test_group, create_test_user

        service = PeriodService(db_session)

        # Create a group first (periods require group_id)
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        request = PeriodCreateRequest(name="New Period", group_id=group.id)

        created = await service.create_period(request)
        assert created.name == "New Period"
        assert created.group_id == group.id

    async def test_update_period_exists(self, db_session: AsyncSession):
        """Test updating an existing period."""
        from tests.fixtures.factories import create_test_group, create_test_user

        service = PeriodService(db_session)

        # Create a group first
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Original Name", created_by=user.id)
        db_session.add(period)
        await db_session.commit()

        new_start = datetime.now(UTC)
        request = PeriodUpdateRequest(name="Updated Name", start_date=new_start)

        updated = await service.update_period(period.id, request)

        assert updated.name == "Updated Name"
        # Compare dates without timezone (database may store without tzinfo)
        time_diff = abs((updated.start_date.replace(tzinfo=None) - new_start.replace(tzinfo=None)).total_seconds())
        assert time_diff < 1.0

        # Verify the update persisted
        retrieved = await service.get_period_by_id(period.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_update_period_not_exists(self, db_session: AsyncSession):
        """Test updating a non-existent period raises NotFoundError."""
        service = PeriodService(db_session)

        request = PeriodUpdateRequest(name="Updated Name", start_date=datetime.now(UTC))

        with pytest.raises(NotFoundError):
            await service.update_period(99999, request)

    async def test_close_period(self, db_session: AsyncSession):
        """Test closing a period."""
        from tests.fixtures.factories import create_test_group, create_test_user

        service = PeriodService(db_session)

        # Create a group first
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="To Settle", created_by=user.id)
        db_session.add(period)
        await db_session.commit()

        settled = await service.close_period(period.id)

        assert settled.end_date is not None
        assert settled.is_closed is True

        # Check that the date is approximately correct (within 1 second)
        time_diff = abs((settled.end_date.replace(tzinfo=UTC) - datetime.now(UTC)).total_seconds())
        assert time_diff < 1.0

        # Verify the update persisted
        retrieved = await service.get_period_by_id(period.id)
        assert retrieved is not None
        assert retrieved.is_closed is True

    async def test_close_period_not_exists(self, db_session: AsyncSession):
        """Test closing a non-existent period raises NotFoundError."""
        service = PeriodService(db_session)

        with pytest.raises(NotFoundError):
            await service.close_period(99999)

    async def test_delete_period_exists_settled(self, db_session: AsyncSession):
        """Test deleting a closed period."""
        service = PeriodService(db_session)

        period = create_test_period(group_id=1, name="Closed Period", created_by=1)
        period.end_date = datetime.now(UTC)
        db_session.add(period)
        await db_session.commit()
        period_id = period.id

        # Should succeed if period is closed
        await service.delete_period(period_id)

        # Verify period is deleted
        retrieved = await service.get_period_by_id(period_id)
        assert retrieved is None

    async def test_delete_period_not_exists(self, db_session: AsyncSession):
        """Test deleting a non-existent period raises NotFoundError."""
        service = PeriodService(db_session)

        with pytest.raises(NotFoundError):
            await service.delete_period(99999)
