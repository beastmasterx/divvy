"""
Unit tests for UserService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ProfileRequest, UserRequest
from app.exceptions import NotFoundError
from app.services import UserService
from tests.fixtures.factories import create_test_user


@pytest.mark.unit
class TestUserService:
    """Test suite for UserService."""

    async def test_get_all_users(self, db_session: AsyncSession):
        """Test retrieving all users."""
        service = UserService(db_session)

        # Create some users
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        users = await service.get_all_users()
        assert len(users) >= 2
        emails = {user.email for user in users}
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    async def test_get_user_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a user by ID when it exists."""
        service = UserService(db_session)

        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        retrieved = await service.get_user_by_id(user.id)
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "test@example.com"

    async def test_get_user_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user by ID when it doesn't exist."""
        service = UserService(db_session)
        result = await service.get_user_by_id(99999)
        assert result is None

    async def test_get_user_by_email_exists(self, db_session: AsyncSession):
        """Test retrieving a user by email when it exists."""
        service = UserService(db_session)

        user = create_test_user(email="unique@example.com", name="Unique User")
        db_session.add(user)
        await db_session.commit()

        retrieved = await service.get_user_by_email("unique@example.com")
        assert retrieved is not None
        assert retrieved.email == "unique@example.com"

    async def test_get_user_by_email_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user by email when it doesn't exist."""
        service = UserService(db_session)
        result = await service.get_user_by_email("nonexistent@example.com")
        assert result is None

    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user."""
        service = UserService(db_session)

        request = UserRequest(email="newuser@example.com", name="New User", password="plain_password", is_active=True)

        created = await service.create_user(request)

        assert created.id is not None
        assert created.email == "newuser@example.com"
        assert created.name == "New User"
        assert created.is_active is True
        # Note: password should be hashed in real usage, but service accepts plain text

        # Verify it's in the database
        retrieved = await service.get_user_by_id(created.id)
        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    async def test_update_profile_user_exists(self, db_session: AsyncSession):
        """Test updating user profile for an existing user."""
        service = UserService(db_session)

        user = create_test_user(email="original@example.com", name="Original Name", is_active=True)
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        request = ProfileRequest(email="updated@example.com", name="Updated Name", is_active=False)

        updated = await service.update_profile(user_id, request)
        assert updated.email == "updated@example.com"
        assert updated.name == "Updated Name"
        assert updated.is_active is False

        # Verify the update persisted
        retrieved = await service.get_user_by_id(user_id)
        assert retrieved is not None
        assert retrieved.email == "updated@example.com"
        assert retrieved.name == "Updated Name"

    async def test_update_profile_partial_update(self, db_session: AsyncSession):
        """Test updating only some fields in user profile."""
        service = UserService(db_session)

        user = create_test_user(email="partial@example.com", name="Original Name", is_active=True)
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        # Only update name, leave email unchanged
        request = ProfileRequest(name="Updated Name")

        updated = await service.update_profile(user_id, request)
        assert updated.name == "Updated Name"
        assert updated.email == "partial@example.com"  # Unchanged

        # Verify the update persisted
        retrieved = await service.get_user_by_id(user_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.email == "partial@example.com"

    async def test_update_profile_user_not_exists(self, db_session: AsyncSession):
        """Test updating profile for a non-existent user raises NotFoundError."""
        service = UserService(db_session)

        request = ProfileRequest(name="Updated Name")

        with pytest.raises(NotFoundError):
            await service.update_profile(99999, request)

    async def test_delete_user_exists_no_groups(self, db_session: AsyncSession):
        """Test deleting a user who is not in any groups."""
        service = UserService(db_session)

        user = create_test_user(email="todelete@example.com", name="To Delete")
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        # Should succeed if user is not in any groups
        await service.delete_user(user_id)

        # Verify user is deleted
        retrieved = await service.get_user_by_id(user_id)
        assert retrieved is None

    async def test_delete_user_not_exists(self, db_session: AsyncSession):
        """Test deleting a non-existent user raises NotFoundError."""
        service = UserService(db_session)

        with pytest.raises(NotFoundError):
            await service.delete_user(99999)

    async def test_get_groups_by_user_id(self, db_session: AsyncSession):
        """Test retrieving groups for a user."""
        service = UserService(db_session)

        user = create_test_user(email="nogroups@example.com", name="No Groups")
        db_session.add(user)
        await db_session.commit()

        groups = await service.get_groups_by_user_id(user.id)
        assert isinstance(groups, list)
        # User should have no groups initially
        assert len(groups) == 0
