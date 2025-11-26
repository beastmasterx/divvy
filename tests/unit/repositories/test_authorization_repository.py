"""
Unit tests for AuthorizationRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GroupRole, GroupRoleBinding, Permission, RolePermission, SystemRole, SystemRoleBinding
from app.repositories import AuthorizationRepository
from tests.fixtures.factories import create_test_group, create_test_user


@pytest.fixture
def auth_repository(db_session: AsyncSession) -> AuthorizationRepository:
    """Create an AuthorizationRepository instance for testing."""
    return AuthorizationRepository(db_session)


@pytest.mark.unit
class TestAuthorizationRepository:
    """Test suite for AuthorizationRepository."""

    # ========== System Role Bindings ==========

    async def test_get_system_role_exists(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving system role when it exists."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Assign system role
        binding = SystemRoleBinding(user_id=user.id, role=SystemRole.ADMIN.value)
        db_session.add(binding)
        await db_session.commit()

        role = await auth_repository.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    async def test_get_system_role_not_exists(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving system role when it doesn't exist."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        role = await auth_repository.get_system_role(user.id)
        assert role is None

    async def test_assign_system_role_create(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test creating a new system role binding."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        binding = await auth_repository.assign_system_role(user.id, SystemRole.USER.value)

        assert binding is not None
        assert binding.user_id == user.id
        assert binding.role == SystemRole.USER.value

        # Verify it's in the database
        role = await auth_repository.get_system_role(user.id)
        assert role == SystemRole.USER.value

    async def test_assign_system_role_update(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test updating an existing system role binding."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Create initial role
        binding1 = await auth_repository.assign_system_role(user.id, SystemRole.USER.value)
        assert binding1 is not None
        assert binding1.role == SystemRole.USER.value

        # Update to admin
        binding2 = await auth_repository.assign_system_role(user.id, SystemRole.ADMIN.value)
        assert binding2 is not None
        assert binding2.user_id == user.id
        assert binding2.role == SystemRole.ADMIN.value

        # Verify update persisted
        role = await auth_repository.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    async def test_assign_system_role_remove(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test removing a system role binding."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Create role
        await auth_repository.assign_system_role(user.id, SystemRole.USER.value)
        assert await auth_repository.get_system_role(user.id) == SystemRole.USER.value

        # Remove role
        result = await auth_repository.assign_system_role(user.id, None)
        assert result is None

        # Verify it's removed
        role = await auth_repository.get_system_role(user.id)
        assert role is None

    # ========== Group Role Bindings ==========

    async def test_get_group_role_exists(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving group role when it exists."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Assign group role
        binding = GroupRoleBinding(user_id=user.id, group_id=group.id, role=GroupRole.ADMIN.value)
        db_session.add(binding)
        await db_session.commit()

        role = await auth_repository.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    async def test_get_group_role_not_exists(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving group role when it doesn't exist."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        role = await auth_repository.get_group_role(user.id, group.id)
        assert role is None

    async def test_assign_group_role_create(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test creating a new group role binding."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        binding = await auth_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)

        assert binding is not None
        assert binding.user_id == user.id
        assert binding.group_id == group.id
        assert binding.role == GroupRole.MEMBER.value

        # Verify it's in the database
        role = await auth_repository.get_group_role(user.id, group.id)
        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_update(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test updating an existing group role binding."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Create initial role
        binding1 = await auth_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)
        assert binding1 is not None
        assert binding1.role == GroupRole.MEMBER.value

        # Update to admin
        binding2 = await auth_repository.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)
        assert binding2 is not None
        assert binding2.user_id == user.id
        assert binding2.group_id == group.id
        assert binding2.role == GroupRole.ADMIN.value

        # Verify update persisted
        role = await auth_repository.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    async def test_assign_group_role_remove(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test removing a group role binding."""
        user = create_test_user(email="user@example.com", name="User")
        group = create_test_group(name="Test Group")
        db_session.add_all([user, group])
        await db_session.commit()

        # Create role
        await auth_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)
        assert await auth_repository.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Remove role
        result = await auth_repository.assign_group_role(user.id, group.id, None)
        assert result is None

        # Verify it's removed
        role = await auth_repository.get_group_role(user.id, group.id)
        assert role is None

    async def test_assign_group_role_multiple_groups(
        self, db_session: AsyncSession, auth_repository: AuthorizationRepository
    ):
        """Test user can have different roles in different groups."""
        user = create_test_user(email="user@example.com", name="User")
        group1 = create_test_group(name="Group 1")
        group2 = create_test_group(name="Group 2")
        db_session.add_all([user, group1, group2])
        await db_session.commit()

        # Assign different roles in different groups
        await auth_repository.assign_group_role(user.id, group1.id, GroupRole.MEMBER.value)
        await auth_repository.assign_group_role(user.id, group2.id, GroupRole.ADMIN.value)

        # Verify different roles
        role1 = await auth_repository.get_group_role(user.id, group1.id)
        role2 = await auth_repository.get_group_role(user.id, group2.id)
        assert role1 == GroupRole.MEMBER.value
        assert role2 == GroupRole.ADMIN.value

    # ========== Role Permissions ==========

    async def test_get_role_permissions(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving permissions for a role."""
        # Create role permissions (these should be seeded, but create explicitly for test)
        role_permission1 = RolePermission(role=GroupRole.ADMIN.value, permission="groups:read")
        role_permission2 = RolePermission(role=GroupRole.ADMIN.value, permission="groups:write")
        db_session.add_all([role_permission1, role_permission2])
        await db_session.commit()

        permissions = await auth_repository.get_role_permissions(GroupRole.ADMIN.value)
        permission_set = set(permissions)
        assert "groups:read" in permission_set
        assert "groups:write" in permission_set

    async def test_get_role_permissions_empty(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test retrieving permissions for role with no permissions."""
        permissions = await auth_repository.get_role_permissions("nonexistent:role")
        assert len(permissions) == 0

    async def test_create_role_permission(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test creating a role permission mapping."""
        role_permission = await auth_repository.create_role_permission(
            GroupRole.ADMIN.value, Permission.GROUPS_READ.value
        )

        assert role_permission.role == GroupRole.ADMIN.value
        assert role_permission.permission == Permission.GROUPS_READ.value

        # Verify it's in the database
        permissions = await auth_repository.get_role_permissions(GroupRole.ADMIN.value)
        assert Permission.GROUPS_READ.value in permissions

    async def test_delete_role_permission(self, db_session: AsyncSession, auth_repository: AuthorizationRepository):
        """Test deleting a role permission mapping."""
        # Create role permission
        role_permission = RolePermission(role=GroupRole.ADMIN.value, permission=Permission.GROUPS_READ.value)
        db_session.add(role_permission)
        await db_session.commit()

        # Verify it exists
        permissions = await auth_repository.get_role_permissions(GroupRole.ADMIN.value)
        assert Permission.GROUPS_READ.value in permissions

        # Delete it
        await auth_repository.delete_role_permission(GroupRole.ADMIN.value, Permission.GROUPS_READ.value)

        # Verify it's removed
        permissions = await auth_repository.get_role_permissions(GroupRole.ADMIN.value)
        assert "test:permission" not in permissions
