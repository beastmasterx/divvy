"""
Unit tests for AuthorizationRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, GroupRole, GroupRoleBinding, SystemRole, SystemRoleBinding
from app.models.user import User
from app.repositories import AuthorizationRepository


@pytest.mark.unit
class TestAuthorizationRepository:
    """Test suite for AuthorizationRepository."""

    @pytest.fixture
    def authorization_repository(self, db_session: AsyncSession) -> AuthorizationRepository:
        return AuthorizationRepository(db_session)

    # ========== System Role Bindings ==========

    async def test_get_system_role_exists(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        system_role_binding_factory: Callable[..., Awaitable[SystemRoleBinding]],
    ):
        """Test retrieving system role when it exists."""
        user = await user_factory(email="user@example.com", name="User")

        # Assign system role
        binding = await system_role_binding_factory(user_id=user.id, role=SystemRole.ADMIN.value)
        role = await authorization_repository.get_system_role(user.id)

        assert role == binding.role
        assert role == SystemRole.ADMIN.value

    async def test_get_system_role_not_exists(
        self, authorization_repository: AuthorizationRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving system role when it doesn't exist."""
        user = await user_factory(email="user@example.com", name="User")

        role = await authorization_repository.get_system_role(user.id)

        assert role is None

    async def test_assign_system_role_create(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        system_role_binding_factory: Callable[..., Awaitable[SystemRoleBinding]],
    ):
        """Test creating a new system role binding."""
        user = await user_factory(email="user@example.com", name="User")

        binding = await authorization_repository.assign_system_role(user.id, SystemRole.USER.value)

        assert binding is not None
        assert binding.user_id == user.id
        assert binding.role == SystemRole.USER.value

        # Verify it's in the database
        role = await authorization_repository.get_system_role(user.id)
        assert role == SystemRole.USER.value

    async def test_assign_system_role_update(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        system_role_binding_factory: Callable[..., Awaitable[SystemRoleBinding]],
    ):
        """Test updating an existing system role binding."""
        user = await user_factory(email="user@example.com", name="User")

        # Create initial role
        binding1 = await authorization_repository.assign_system_role(user.id, SystemRole.USER.value)

        assert binding1 is not None
        assert binding1.role == SystemRole.USER.value

        # Update to admin
        binding2 = await authorization_repository.assign_system_role(user.id, SystemRole.ADMIN.value)

        assert binding2 is not None
        assert binding2.user_id == user.id
        assert binding2.role == SystemRole.ADMIN.value

        # Verify update persisted
        role = await authorization_repository.get_system_role(user.id)
        assert role == SystemRole.ADMIN.value

    async def test_assign_system_role_remove(
        self, authorization_repository: AuthorizationRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test removing a system role binding."""
        user = await user_factory(email="user@example.com", name="User")

        # Create role
        await authorization_repository.assign_system_role(user.id, SystemRole.USER.value)
        assert await authorization_repository.get_system_role(user.id) == SystemRole.USER.value

        # Remove role
        result = await authorization_repository.assign_system_role(user.id, None)
        assert result is None

        # Verify it's removed
        role = await authorization_repository.get_system_role(user.id)
        assert role is None

    # ========== Group Role Bindings ==========

    async def test_get_group_role_exists(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test retrieving group role when it exists."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Assign group role
        await group_role_binding_factory(user_id=user.id, group_id=group.id, role=GroupRole.ADMIN.value)

        role = await authorization_repository.get_group_role(user.id, group.id)
        assert role == GroupRole.ADMIN.value

    async def test_get_group_role_not_exists(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group role when it doesn't exist."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        role = await authorization_repository.get_group_role(user.id, group.id)

        assert role is None

    async def test_assign_group_role_create(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test creating a new group role binding."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        binding = await authorization_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)

        assert binding is not None
        assert binding.user_id == user.id
        assert binding.group_id == group.id
        assert binding.role == GroupRole.MEMBER.value

        # Verify it's in the database
        role = await authorization_repository.get_group_role(user.id, group.id)

        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_update(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test updating an existing group role binding."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Create initial role
        binding1 = await authorization_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)

        assert binding1 is not None
        assert binding1.role == GroupRole.MEMBER.value

        # Update to admin
        binding2 = await authorization_repository.assign_group_role(user.id, group.id, GroupRole.ADMIN.value)

        assert binding2 is not None
        assert binding2.user_id == user.id
        assert binding2.group_id == group.id
        assert binding2.role == GroupRole.ADMIN.value

        # Verify update persisted
        role = await authorization_repository.get_group_role(user.id, group.id)

        assert role == GroupRole.ADMIN.value

    async def test_assign_group_role_remove(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test removing a group role binding."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Create role
        await authorization_repository.assign_group_role(user.id, group.id, GroupRole.MEMBER.value)
        assert await authorization_repository.get_group_role(user.id, group.id) == GroupRole.MEMBER.value

        # Remove role
        result = await authorization_repository.assign_group_role(user.id, group.id, None)
        assert result is None

        # Verify it's removed
        role = await authorization_repository.get_group_role(user.id, group.id)
        assert role is None

    async def test_assign_group_role_multiple_groups(
        self,
        authorization_repository: AuthorizationRepository,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test user can have different roles in different groups."""
        user = await user_factory(email="user@example.com", name="User")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")

        # Assign different roles in different groups
        await authorization_repository.assign_group_role(user.id, group1.id, GroupRole.MEMBER.value)
        await authorization_repository.assign_group_role(user.id, group2.id, GroupRole.ADMIN.value)

        # Verify different roles
        role1 = await authorization_repository.get_group_role(user.id, group1.id)
        role2 = await authorization_repository.get_group_role(user.id, group2.id)

        assert role1 == GroupRole.MEMBER.value
        assert role2 == GroupRole.ADMIN.value
