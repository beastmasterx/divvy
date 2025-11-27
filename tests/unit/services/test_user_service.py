"""
Unit tests for UserService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import NotFoundError
from app.models import User
from app.schemas import ProfileRequest, UserRequest
from app.services import UserService


@pytest.mark.unit
class TestUserService:
    """Test suite for UserService."""

    async def test_get_all_users(self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]):
        """Test retrieving all users."""
        # Create some users
        await user_factory(email="user1@example.com", name="User 1")
        await user_factory(email="user2@example.com", name="User 2")

        users = await user_service.get_all_users()
        assert len(users) >= 2
        emails = {user.email for user in users}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_get_user_by_id_exists(self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]):
        """Test retrieving a user by ID when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        retrieved = await user_service.get_user_by_id(user.id)
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "test@example.com"

    async def test_get_user_by_id_not_exists(self, user_service: UserService):
        """Test retrieving a user by ID when it doesn't exist."""
        result = await user_service.get_user_by_id(99999)
        assert result is None

    async def test_get_user_by_email_exists(
        self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving a user by email when it exists."""
        user = await user_factory(email="unique@example.com", name="Unique User")

        retrieved = await user_service.get_user_by_email("unique@example.com")
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "unique@example.com"

    async def test_get_user_by_email_not_exists(self, user_service: UserService):
        """Test retrieving a user by email when it doesn't exist."""
        result = await user_service.get_user_by_email("nonexistent@example.com")
        assert result is None

    async def test_create_user(self, user_service: UserService):
        """Test creating a new user."""
        request = UserRequest(email="newuser@example.com", name="New User", password="plain_password", is_active=True)

        created = await user_service.create_user(request)

        assert created.id is not None
        assert created.email == "newuser@example.com"
        assert created.name == "New User"
        assert created.is_active is True
        # Note: password should be hashed in real usage, but service accepts plain text

        # Verify it's in the database
        retrieved = await user_service.get_user_by_id(created.id)
        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    async def test_update_profile_user_exists(
        self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test updating user profile for an existing user."""
        user = await user_factory(email="original@example.com", name="Original Name", is_active=True)
        user_id = user.id

        request = ProfileRequest(email="updated@example.com", name="Updated Name", is_active=False)

        updated = await user_service.update_profile(user_id, request)
        assert updated.email == "updated@example.com"
        assert updated.name == "Updated Name"
        assert updated.is_active is False

        # Verify the update persisted
        retrieved = await user_service.get_user_by_id(user_id)
        assert retrieved is not None
        assert retrieved.email == "updated@example.com"
        assert retrieved.name == "Updated Name"

    async def test_update_profile_partial_update(
        self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test updating only some fields in user profile."""
        user = await user_factory(email="partial@example.com", name="Original Name", is_active=True)
        user_id = user.id

        # Only update name, leave email unchanged
        request = ProfileRequest(name="Updated Name")

        updated = await user_service.update_profile(user_id, request)
        assert updated.name == "Updated Name"
        assert updated.email == "partial@example.com"  # Unchanged

        # Verify the update persisted
        retrieved = await user_service.get_user_by_id(user_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.email == "partial@example.com"

    async def test_update_profile_user_not_exists(self, user_service: UserService):
        """Test updating profile for a non-existent user raises NotFoundError."""
        request = ProfileRequest(name="Updated Name")

        with pytest.raises(NotFoundError):
            await user_service.update_profile(99999, request)

    async def test_delete_user_exists_no_groups(
        self, user_service: UserService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test deleting a user who is not in any groups."""
        user = await user_factory(email="todelete@example.com", name="To Delete")
        user_id = user.id

        # Should succeed if user is not in any groups
        await user_service.delete_user(user_id)

        # Verify user is deleted
        retrieved = await user_service.get_user_by_id(user_id)
        assert retrieved is None

    async def test_delete_user_not_exists(self, user_service: UserService):
        """Test deleting a non-existent user raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await user_service.delete_user(99999)
