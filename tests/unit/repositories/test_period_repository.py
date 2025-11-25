"""
Unit tests for PeriodRepository.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import PeriodRepository
from tests.fixtures.factories import create_test_period


@pytest.mark.unit
class TestPeriodRepository:
    """Test suite for PeriodRepository."""

    async def test_get_all_periods_empty(self, db_session: AsyncSession):
        """Test retrieving all periods when database is empty."""
        repo = PeriodRepository(db_session)
        periods = await repo.get_all_periods()
        assert isinstance(periods, list)
        assert len(periods) == 0

    async def test_get_all_periods_multiple(self, db_session: AsyncSession):
        """Test retrieving all periods when multiple exist."""
        repo = PeriodRepository(db_session)

        # Create multiple periods (requires group_id)
        # Note: This test assumes a group exists or we need to create one
        period1 = create_test_period(group_id=1, name="Period 1")
        period2 = create_test_period(group_id=1, name="Period 2")
        db_session.add(period1)
        db_session.add(period2)
        await db_session.commit()

        periods = await repo.get_all_periods()
        assert len(periods) >= 2
        period_names = {p.name for p in periods}
        assert "Period 1" in period_names
        assert "Period 2" in period_names

    async def test_get_period_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a period by ID when it exists."""
        repo = PeriodRepository(db_session)

        period = create_test_period(group_id=1, name="Test Period")
        db_session.add(period)
        await db_session.commit()
        period_id = period.id

        retrieved = await repo.get_period_by_id(period_id)
        assert retrieved is not None
        assert retrieved.id == period_id
        assert retrieved.name == "Test Period"

    async def test_get_period_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a period by ID when it doesn't exist."""
        repo = PeriodRepository(db_session)
        result = await repo.get_period_by_id(99999)
        assert result is None

    async def test_create_period(self, db_session: AsyncSession):
        """Test creating a new period."""
        repo = PeriodRepository(db_session)

        period = create_test_period(group_id=1, name="New Period")
        created = await repo.create_period(period)

        assert created.id is not None
        assert created.name == "New Period"
        assert created.is_closed is False
        assert created.group_id == 1

        # Verify it's in the database
        retrieved = await repo.get_period_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Period"

    async def test_update_period(self, db_session: AsyncSession):
        """Test updating an existing period."""
        repo = PeriodRepository(db_session)

        # Create a period
        period = create_test_period(group_id=1, name="Original Name")
        db_session.add(period)
        await db_session.commit()

        # Update it
        period.name = "Updated Name"
        period.end_date = datetime.now(UTC)
        updated = await repo.update_period(period)

        assert updated.name == "Updated Name"
        assert updated.is_closed is True

        # Verify the update persisted
        retrieved = await repo.get_period_by_id(period.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.is_closed is True

    async def test_delete_period_exists(self, db_session: AsyncSession):
        """Test deleting a period that exists."""
        repo = PeriodRepository(db_session)

        # Create a period
        period = create_test_period(group_id=1, name="To Delete")
        db_session.add(period)
        await db_session.commit()
        period_id = period.id

        # Delete it
        await repo.delete_period(period_id)

        # Verify it's gone
        retrieved = await repo.get_period_by_id(period_id)
        assert retrieved is None

    async def test_delete_period_not_exists(self, db_session: AsyncSession):
        """Test deleting a period that doesn't exist (should not raise error)."""
        repo = PeriodRepository(db_session)
        # Should not raise an exception
        await repo.delete_period(99999)
