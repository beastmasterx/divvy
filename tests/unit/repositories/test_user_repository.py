"""
Unit tests for UserRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import UserRepository
from tests.fixtures.factories import create_test_user


@pytest.mark.unit
class TestUserRepository:
    """Test suite for UserRepository."""

    @pytest.fixture
    def user_repository(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    async def test_get_all_users_empty(self, user_repository: UserRepository):
        """Test retrieving all users when database is empty."""
        users = await user_repository.get_all_users()
        assert isinstance(users, list)
        assert len(users) == 0

    async def test_get_all_users_multiple(
        self, user_repository: UserRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving all users when multiple exist."""
        # Create multiple users
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")

        users = await user_repository.get_all_users()

        assert len(users) == 2

        emails = {user.email for user in users}

        assert user1.email in emails
        assert user2.email in emails

    async def test_get_user_by_id_exists(
        self, user_repository: UserRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving a user by ID when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        retrieved = await user_repository.get_user_by_id(user.id)

        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "test@example.com"
        assert retrieved.name == "Test User"

    async def test_get_user_by_id_not_exists(self, user_repository: UserRepository):
        """Test retrieving a user by ID when it doesn't exist."""
        result = await user_repository.get_user_by_id(99999)

        assert result is None

    async def test_get_user_by_email_exists(
        self, user_repository: UserRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving a user by email when it exists."""
        user = await user_factory(email="unique@example.com", name="Unique User")

        retrieved = await user_repository.get_user_by_email(user.email)

        assert retrieved is not None
        assert retrieved.email == user.email
        assert retrieved.name == user.name

    async def test_get_user_by_email_not_exists(self, user_repository: UserRepository):
        """Test retrieving a user by email when it doesn't exist."""
        result = await user_repository.get_user_by_email("nonexistent@example.com")

        assert result is None

    async def test_create_user(self, user_repository: UserRepository):
        """Test creating a new user."""
        user = create_test_user(email="newuser@example.com", name="New User", is_active=True)

        created = await user_repository.create_user(user)

        assert created.id is not None
        assert created.email == "newuser@example.com"
        assert created.name == "New User"
        assert created.is_active is True

        # Verify it's in the database
        retrieved = await user_repository.get_user_by_id(created.id)

        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    async def test_update_user(self, user_repository: UserRepository, user_factory: Callable[..., Awaitable[User]]):
        """Test updating an existing user."""
        # Create a user
        user = await user_factory(email="original@example.com", name="Original Name")

        # Update it
        user.name = "Updated Name"
        user.email = "updated@example.com"

        updated = await user_repository.update_user(user)

        assert updated.name == "Updated Name"
        assert updated.email == "updated@example.com"

        # Verify the update persisted
        retrieved = await user_repository.get_user_by_id(user.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.email == "updated@example.com"

    async def test_delete_user_exists(
        self, user_repository: UserRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test deleting a user that exists."""
        # Create a user
        user = await user_factory(email="todelete@example.com", name="To Delete")

        # Delete it
        await user_repository.delete_user(user.id)

        # Verify it's gone
        retrieved = await user_repository.get_user_by_id(user.id)

        assert retrieved is None

    async def test_delete_user_not_exists(self, user_repository: UserRepository):
        """Test deleting a user that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await user_repository.delete_user(99999)
