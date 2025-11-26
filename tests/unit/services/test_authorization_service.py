"""
Unit tests for AuthorizationService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models import GroupRole, Permission, SystemRole
from app.repositories import AuthorizationRepository
from app.services import AuthorizationService
from tests.fixtures.factories import create_test_group, create_test_user


@pytest.fixture
def auth_service(db_session: AsyncSession) -> AuthorizationService:
    """Create an AuthorizationService instance for testing."""
    return AuthorizationService(db_session)


@pytest.mark.unit
class TestAuthorizationService:
    """Test suite for AuthorizationService."""

    # ========== Permission Checking ==========

    async def test_has_permission_system_admin_has_all(
        self, db_session: AsyncSession, auth_service: AuthorizationService
    ):
        """Test system admin has all permissions."""
        user = create_test_user(email="admin@example.com", name="Admin")
        db_session.add(user)
        await db_session.commit()

        # Assign admin role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.ADMIN.value)

        # Admin should have any permission
        assert await auth_service.has_permission(user.id, Permission.GROUPS_READ) is True
        assert await auth_service.has_permission(user.id, Permission.GROUPS_WRITE) is True
        assert await auth_service.has_permission(user.id, Permission.GROUPS_DELETE) is True
        assert await auth_service.has_permission(user.id, "custom:permission") is True  # Even invalid ones

    async def test_has_permission_system_user_with_permission(
        self, db_session: AsyncSession, auth_service: AuthorizationService
    ):
        """Test system user with role permission."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign system user role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permission (system:user has groups:read)
        from app.models import RolePermission

        role_permission = RolePermission(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)
        db_session.add(role_permission)
        await db_session.commit()

        # User should have groups:read
        assert await auth_service.has_permission(user.id, Permission.GROUPS_READ) is True
        # But not groups:write
        assert await auth_service.has_permission(user.id, Permission.GROUPS_WRITE) is False

    async def test_has_permission_group_owner_has_all(
        self, db_session: AsyncSession, auth_service: AuthorizationService
    ):
        """Test group owner has all group permissions."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign system user role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.USER.value)

        # Assign group owner role
        await auth_repo.assign_group_role(user.id, group.id, GroupRole.OWNER.value)

        # Owner should have all group permissions
        assert await auth_service.has_permission(user.id, Permission.GROUPS_READ, group_id=group.id) is True
        assert await auth_service.has_permission(user.id, Permission.GROUPS_WRITE, group_id=group.id) is True
        assert await auth_service.has_permission(user.id, Permission.GROUPS_DELETE, group_id=group.id) is True
        assert await auth_service.has_permission(user.id, Permission.TRANSACTIONS_READ, group_id=group.id) is True

    async def test_has_permission_group_admin_with_permissions(
        self, db_session: AsyncSession, auth_service: AuthorizationService
    ):
        """Test group admin with role permissions."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign system user role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.USER.value)

        # Assign group admin role
        await auth_repo.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)

        # Create role permissions (group:admin has groups:read and groups:write)
        from app.models import RolePermission

        role_permission1 = RolePermission(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_READ.value)
        role_permission2 = RolePermission(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_WRITE.value)
        db_session.add_all([role_permission1, role_permission2])
        await db_session.commit()

        # Admin should have groups:read and groups:write
        assert await auth_service.has_permission(user.id, Permission.GROUPS_READ, group_id=group.id) is True
        assert await auth_service.has_permission(user.id, Permission.GROUPS_WRITE, group_id=group.id) is True
        # But not groups:delete (unless explicitly granted)
        assert await auth_service.has_permission(user.id, Permission.GROUPS_DELETE, group_id=group.id) is False

    async def test_has_permission_no_role(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test user with no roles has no permissions."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # No system role assigned
        assert await auth_service.has_permission(user.id, Permission.GROUPS_READ) is False

    async def test_has_any_permission(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test has_any_permission returns True if user has at least one permission."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign system user role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permission
        from app.models import RolePermission

        role_permission = RolePermission(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)
        db_session.add(role_permission)
        await db_session.commit()

        # Should return True if user has at least one permission
        assert await auth_service.has_any_permission(user.id, [Permission.GROUPS_READ, Permission.GROUPS_WRITE]) is True
        # Should return False if user has none
        assert (
            await auth_service.has_any_permission(user.id, [Permission.GROUPS_WRITE, Permission.GROUPS_DELETE]) is False
        )

    async def test_has_all_permissions(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test has_all_permissions returns True only if user has all permissions."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign system user role
        auth_repo = AuthorizationRepository(db_session)
        await auth_repo.assign_system_role(user.id, SystemRole.USER.value)

        # Create role permissions
        from app.models import RolePermission

        role_permission1 = RolePermission(role=SystemRole.USER.value, permission=Permission.GROUPS_READ.value)
        role_permission2 = RolePermission(role=SystemRole.USER.value, permission=Permission.GROUPS_WRITE.value)
        db_session.add_all([role_permission1, role_permission2])
        await db_session.commit()

        # Should return True if user has all permissions
        assert (
            await auth_service.has_all_permissions(user.id, [Permission.GROUPS_READ, Permission.GROUPS_WRITE]) is True
        )
        # Should return False if user is missing any
        assert (
            await auth_service.has_all_permissions(user.id, [Permission.GROUPS_READ, Permission.GROUPS_DELETE]) is False
        )

    # ========== System Role Management ==========

    async def test_get_system_role_exists(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test retrieving system role when it exists."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign system role
        await auth_service.assign_system_role(user.id, SystemRole.ADMIN)

        role = await auth_service.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    async def test_get_system_role_not_exists(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test retrieving system role when it doesn't exist."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        role = await auth_service.get_system_role(user.id)
        assert role is None

    async def test_assign_system_role_create(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test creating a new system role."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        await auth_service.assign_system_role(user.id, SystemRole.USER)

        role = await auth_service.get_system_role(user.id)
        assert role == SystemRole.USER.value

    async def test_assign_system_role_update(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test updating an existing system role (switching roles)."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign user role
        await auth_service.assign_system_role(user.id, SystemRole.USER)
        assert await auth_service.get_system_role(user.id) == SystemRole.USER.value

        # Switch to admin
        await auth_service.assign_system_role(user.id, SystemRole.ADMIN)
        assert await auth_service.get_system_role(user.id) == SystemRole.ADMIN.value

    async def test_assign_system_role_invalid(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test assigning invalid system role raises ValidationError."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(ValidationError, match="Invalid system role"):
            await auth_service.assign_system_role(user.id, "invalid:role")

    async def test_assign_system_role_string_value(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test assigning system role using string value."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        await auth_service.assign_system_role(user.id, SystemRole.ADMIN.value)

        role = await auth_service.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    # ========== Group Role Management ==========

    async def test_get_group_role_exists(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test retrieving group role when it exists."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign group role
        await auth_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)

        role = await auth_service.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    async def test_get_group_role_not_exists(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test retrieving group role when it doesn't exist."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        role = await auth_service.get_group_role(user.id, group.id)
        assert role is None

    async def test_assign_group_role_create(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test creating a new group role."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        await auth_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)

        role = await auth_service.get_group_role(user.id, group.id)
        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_update(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test updating an existing group role."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign member role
        await auth_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)
        assert await auth_service.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Update to admin
        await auth_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)
        assert await auth_service.get_group_role(user.id, group.id) == GroupRole.ADMIN.value

    async def test_assign_group_role_remove(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test removing a group role (role=None)."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign role
        await auth_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)
        assert await auth_service.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Remove role
        await auth_service.assign_group_role(user.id, group.id, None)

        # Verify it's removed
        role = await auth_service.get_group_role(user.id, group.id)
        assert role is None

    async def test_assign_group_role_invalid(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test assigning invalid group role raises ValidationError."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        with pytest.raises(ValidationError, match="Invalid group role"):
            await auth_service.assign_group_role(user.id, group.id, "invalid:role")

    async def test_assign_group_role_string_value(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test assigning group role using string value."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        await auth_service.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)

        role = await auth_service.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    # ========== Role Permission Management ==========

    async def test_get_permissions(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test retrieving permissions for a role."""
        # Create role permissions
        from app.models import RolePermission

        role_permission1 = RolePermission(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_READ.value)
        role_permission2 = RolePermission(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_WRITE.value)
        db_session.add_all([role_permission1, role_permission2])
        await db_session.commit()

        permissions = await auth_service.get_permissions(GroupRole.ADMIN.value)
        permission_set = set(permissions)
        assert Permission.GROUPS_READ.value in permission_set
        assert Permission.GROUPS_WRITE.value in permission_set

    async def test_grant_permission(self, auth_service: AuthorizationService):
        """Test granting a permission to a role."""
        await auth_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        permissions = await auth_service.get_permissions(GroupRole.ADMIN.value)
        assert Permission.GROUPS_READ.value in permissions

    async def test_grant_permission_already_granted(self, auth_service: AuthorizationService):
        """Test granting already granted permission is idempotent."""
        # Grant permission first time
        await auth_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Grant again (should be no-op)
        await auth_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Should still have the permission
        permissions = await auth_service.get_permissions(GroupRole.ADMIN.value)
        assert Permission.GROUPS_READ.value in permissions
        assert len(permissions) == 1  # Only one instance

    async def test_grant_permission_invalid(self, auth_service: AuthorizationService):
        """Test granting invalid permission raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid permission"):
            await auth_service.grant_permission("test:role", "invalid:permission")

    async def test_revoke_permission(self, auth_service: AuthorizationService):
        """Test revoking a permission from a role."""
        # Grant permission first
        await auth_service.grant_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)
        assert Permission.GROUPS_READ.value in await auth_service.get_permissions(GroupRole.ADMIN.value)

        # Revoke permission
        await auth_service.revoke_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ)

        # Verify it's removed
        permissions = await auth_service.get_permissions("test:role")
        assert Permission.GROUPS_READ.value not in permissions

    async def test_revoke_permission_invalid(self, db_session: AsyncSession, auth_service: AuthorizationService):
        """Test revoking invalid permission raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid permission"):
            await auth_service.revoke_permission("test:role", "invalid:permission")
