"""
Unit tests for AuthorizationService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import ValidationError
from app.models import Group, GroupRole, SystemRole, User
from app.services import AuthorizationService


@pytest.mark.unit
class TestAuthorizationService:
    """Test suite for AuthorizationService."""

    # ========== System Role Management ==========

    async def test_get_system_role_exists(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving system role when it exists."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign system role
        await authorization_service.assign_system_role(user.id, SystemRole.ADMIN)

        role = await authorization_service.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    async def test_get_system_role_not_exists(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving system role when it doesn't exist."""
        user = await user_factory(email="user@example.com", name="User")

        role = await authorization_service.get_system_role(user.id)
        assert role is None

    async def test_assign_system_role_create(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test creating a new system role."""
        user = await user_factory(email="user@example.com", name="User")

        await authorization_service.assign_system_role(user.id, SystemRole.USER)

        role = await authorization_service.get_system_role(user.id)
        assert role == SystemRole.USER.value

    async def test_assign_system_role_update(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test updating an existing system role (switching roles)."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER)
        assert await authorization_service.get_system_role(user.id) == SystemRole.USER.value

        # Switch to admin
        await authorization_service.assign_system_role(user.id, SystemRole.ADMIN)
        assert await authorization_service.get_system_role(user.id) == SystemRole.ADMIN.value

    async def test_assign_system_role_invalid(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test assigning invalid system role raises ValidationError."""
        user = await user_factory(email="user@example.com", name="User")

        with pytest.raises(ValidationError, match="Invalid system role"):
            await authorization_service.assign_system_role(user.id, "invalid:role")

    async def test_assign_system_role_string_value(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test assigning system role using string value."""
        user = await user_factory(email="user@example.com", name="User")

        await authorization_service.assign_system_role(user.id, SystemRole.ADMIN.value)

        role = await authorization_service.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    # ========== Group Role Management ==========

    async def test_get_group_role_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group role when it exists."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign group role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)

        role = await authorization_service.get_group_role(user.id, group.id)

        assert role == GroupRole.ADMIN.value

    async def test_get_group_role_not_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group role when it doesn't exist."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        role = await authorization_service.get_group_role(user.id, group.id)

        assert role is None

    async def test_assign_group_role_create(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test creating a new group role."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        await authorization_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)

        role = await authorization_service.get_group_role(user.id, group.id)

        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_update(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test updating an existing group role."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign member role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)

        assert await authorization_service.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Update to admin
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)

        assert await authorization_service.get_group_role(user.id, group.id) == GroupRole.ADMIN.value

    async def test_assign_group_role_remove(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test removing a group role (role=None)."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)

        assert await authorization_service.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Remove role
        await authorization_service.assign_group_role(user.id, group.id, None)

        # Verify it's removed
        role = await authorization_service.get_group_role(user.id, group.id)

        assert role is None
