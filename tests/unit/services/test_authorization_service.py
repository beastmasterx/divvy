"""
Unit tests for AuthorizationService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import ValidationError
from app.models import Group, GroupRole, Permission, RolePermission, SystemRole, User
from app.services import AuthorizationService


@pytest.mark.unit
class TestAuthorizationService:
    """Test suite for AuthorizationService."""

    # ========== Permission Checking ==========

    async def test_has_permission_system_admin_has_all(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test system admin has all permissions."""
        user = await user_factory(email="admin@example.com", name="Admin")

        # Assign admin role
        await authorization_service.assign_system_role(user.id, SystemRole.ADMIN)

        # Admin should have any permission
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_READ) is True
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_WRITE) is True
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_DELETE) is True
        assert await authorization_service.has_permission(user.id, "custom:permission") is True  # Even invalid ones

    async def test_has_permission_system_user_with_permission(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        role_permission_factory: Callable[..., Awaitable[RolePermission]],
    ):
        """Test system user with role permission."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign system user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permission (system:user has groups:read)
        _ = await role_permission_factory(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)

        # User should have groups:read
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_READ) is True
        # But not groups:write
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_WRITE) is False

    async def test_has_permission_group_owner_has_all(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test group owner has all group permissions."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign system user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER.value)

        # Assign group owner role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.OWNER)

        # Owner should have all group permissions
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_READ, group_id=group.id) is True
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_WRITE, group_id=group.id) is True
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_DELETE, group_id=group.id) is True
        assert (
            await authorization_service.has_permission(user.id, Permission.TRANSACTIONS_READ, group_id=group.id) is True
        )

    async def test_has_permission_group_admin_with_permissions(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        role_permission_factory: Callable[..., Awaitable[RolePermission]],
    ):
        """Test group admin with role permissions."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign system user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER.value)

        # Assign group admin role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)

        # Create role permissions (group:admin has groups:read and groups:write)
        _ = await role_permission_factory(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_READ.value)
        _ = await role_permission_factory(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_WRITE.value)

        # Admin should have groups:read and groups:write
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_READ, group_id=group.id) is True
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_WRITE, group_id=group.id) is True
        # But not groups:delete (unless explicitly granted)
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_DELETE, group_id=group.id) is False

    async def test_has_permission_no_role(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test user with no roles has no permissions."""
        user = await user_factory(email="user@example.com", name="User")

        # No system role assigned
        assert await authorization_service.has_permission(user.id, Permission.GROUPS_READ) is False

    async def test_has_any_permission(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        role_permission_factory: Callable[..., Awaitable[RolePermission]],
    ):
        """Test has_any_permission returns True if user has at least one permission."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign system user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permission
        _ = await role_permission_factory(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)

        # Should return True if user has at least one permission
        assert (
            await authorization_service.has_any_permission(user.id, [Permission.GROUPS_READ, Permission.GROUPS_WRITE])
            is True
        )
        # Should return False if user has none
        assert (
            await authorization_service.has_any_permission(user.id, [Permission.GROUPS_WRITE, Permission.GROUPS_DELETE])
            is False
        )

    async def test_has_all_permissions(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        role_permission_factory: Callable[..., Awaitable[RolePermission]],
    ):
        """Test has_all_permissions returns True only if user has all permissions."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign system user role
        await authorization_service.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permissions
        _ = await role_permission_factory(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)
        _ = await role_permission_factory(role=SystemRole.USER.value, permission=Permission.GROUPS_WRITE.value)

        # Should return True if user has all permissions
        assert (
            await authorization_service.has_all_permissions(user.id, [Permission.GROUPS_READ, Permission.GROUPS_WRITE])
            is True
        )
        # Should return False if user is missing any
        assert (
            await authorization_service.has_all_permissions(user.id, [Permission.GROUPS_READ, Permission.GROUPS_DELETE])
            is False
        )

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

    async def test_assign_group_role_invalid(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test assigning invalid group role raises ValidationError."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        with pytest.raises(ValidationError, match="Invalid group role"):
            await authorization_service.assign_group_role(user.id, group.id, "invalid:role")

    async def test_assign_group_role_string_value(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test assigning group role using string value."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)

        role = await authorization_service.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    # ========== Role Permission Management ==========

    async def test_get_permissions(
        self,
        authorization_service: AuthorizationService,
        role_permission_factory: Callable[..., Awaitable[RolePermission]],
    ):
        """Test retrieving permissions for a role."""
        # Create role permissions
        _ = await role_permission_factory(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_READ.value)
        _ = await role_permission_factory(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_WRITE.value)

        permissions = await authorization_service.get_permissions(GroupRole.ADMIN.value)
        permission_set = set(permissions)

        assert Permission.GROUPS_READ.value in permission_set
        assert Permission.GROUPS_WRITE.value in permission_set

    async def test_grant_permission(self, authorization_service: AuthorizationService):
        """Test granting a permission to a role."""
        await authorization_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        permissions = await authorization_service.get_permissions(GroupRole.ADMIN.value)

        assert Permission.GROUPS_READ.value in permissions

    async def test_grant_permission_already_granted(self, authorization_service: AuthorizationService):
        """Test granting already granted permission is idempotent."""
        # Grant permission first time
        await authorization_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Grant again (should be no-op)
        await authorization_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Should still have the permission
        permissions = await authorization_service.get_permissions(GroupRole.ADMIN.value)

        assert Permission.GROUPS_READ.value in permissions
        assert len(permissions) == 1  # Only one instance

    async def test_grant_permission_invalid(self, authorization_service: AuthorizationService):
        """Test granting invalid permission raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid permission"):
            await authorization_service.grant_permission("test:role", "invalid:permission")

    async def test_revoke_permission(self, authorization_service: AuthorizationService):
        """Test revoking a permission from a role."""
        # Grant permission first
        await authorization_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        assert Permission.GROUPS_READ.value in await authorization_service.get_permissions(GroupRole.ADMIN.value)

        # Revoke permission
        await authorization_service.revoke_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Verify it's removed
        permissions = await authorization_service.get_permissions("test:role")

        assert Permission.GROUPS_READ.value not in permissions

    async def test_revoke_permission_invalid(self, authorization_service: AuthorizationService):
        """Test revoking invalid permission raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid permission"):
            await authorization_service.revoke_permission("test:role", "invalid:permission")
