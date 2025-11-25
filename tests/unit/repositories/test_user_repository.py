"""
Unit tests for UserRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserRepository
from tests.fixtures.factories import create_test_user


@pytest.mark.unit
class TestUserRepository:
    """Test suite for UserRepository."""

    async def test_get_all_users_empty(self, db_session: AsyncSession):
        """Test retrieving all users when database is empty."""
        repo = UserRepository(db_session)
        users = await repo.get_all_users()
        assert isinstance(users, list)
        assert len(users) == 0

    async def test_get_all_users_multiple(self, db_session: AsyncSession):
        """Test retrieving all users when multiple exist."""
        repo = UserRepository(db_session)

        # Create multiple users
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        users = await repo.get_all_users()
        assert len(users) == 2
        emails = {user.email for user in users}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_get_user_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a user by ID when it exists."""
        repo = UserRepository(db_session)

        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        retrieved = await repo.get_user_by_id(user_id)
        assert retrieved is not None
        assert retrieved.id == user_id
        assert retrieved.email == "test@example.com"
        assert retrieved.name == "Test User"

    async def test_get_user_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user by ID when it doesn't exist."""
        repo = UserRepository(db_session)
        result = await repo.get_user_by_id(99999)
        assert result is None

    async def test_get_user_by_email_exists(self, db_session: AsyncSession):
        """Test retrieving a user by email when it exists."""
        repo = UserRepository(db_session)

        user = create_test_user(email="unique@example.com", name="Unique User")
        db_session.add(user)
        await db_session.commit()

        retrieved = await repo.get_user_by_email("unique@example.com")
        assert retrieved is not None
        assert retrieved.email == "unique@example.com"
        assert retrieved.name == "Unique User"

    async def test_get_user_by_email_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user by email when it doesn't exist."""
        repo = UserRepository(db_session)
        result = await repo.get_user_by_email("nonexistent@example.com")
        assert result is None

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user."""
        repo = UserRepository(db_session)

        user = create_test_user(email="newuser@example.com", name="New User", is_active=True)
        created = await repo.create_user(user)

        assert created.id is not None
        assert created.email == "newuser@example.com"
        assert created.name == "New User"
        assert created.is_active is True

        # Verify it's in the database
        retrieved = await repo.get_user_by_id(created.id)
        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    async def test_update_user(self, db_session: AsyncSession):
        """Test updating an existing user."""
        repo = UserRepository(db_session)

        # Create a user
        user = create_test_user(email="original@example.com", name="Original Name")
        db_session.add(user)
        await db_session.commit()

        # Update it
        user.name = "Updated Name"
        user.email = "updated@example.com"
        updated = await repo.update_user(user)

        assert updated.name == "Updated Name"
        assert updated.email == "updated@example.com"

        # Verify the update persisted
        retrieved = await repo.get_user_by_id(user.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.email == "updated@example.com"

    async def test_delete_user_exists(self, db_session: AsyncSession):
        """Test deleting a user that exists."""
        repo = UserRepository(db_session)

        # Create a user
        user = create_test_user(email="todelete@example.com", name="To Delete")
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        # Delete it
        await repo.delete_user(user_id)

        # Verify it's gone
        retrieved = await repo.get_user_by_id(user_id)
        assert retrieved is None

    async def test_delete_user_not_exists(self, db_session: AsyncSession):
        """Test deleting a user that doesn't exist (should not raise error)."""
        repo = UserRepository(db_session)
        # Should not raise an exception
        await repo.delete_user(99999)
