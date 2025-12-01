"""
Unit tests for GroupRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, GroupRole, GroupRoleBinding, User
from app.repositories import GroupRepository
from tests.fixtures.factories import create_test_group


@pytest.mark.unit
class TestGroupRepository:
    """Test suite for GroupRepository."""

    @pytest.fixture
    def group_repository(self, db_session: AsyncSession) -> GroupRepository:
        return GroupRepository(db_session)

    async def test_get_all_groups_empty(self, group_repository: GroupRepository):
        """Test retrieving all groups when database is empty."""
        groups = await group_repository.get_all_groups()

        assert isinstance(groups, list)
        assert len(groups) == 0

    async def test_get_all_groups_multiple(
        self, group_repository: GroupRepository, group_factory: Callable[..., Awaitable[Group]]
    ):
        """Test retrieving all groups when multiple exist."""
        # Create multiple groups
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")

        groups = await group_repository.get_all_groups()

        assert len(groups) >= 2

        group_names = {group.name for group in groups}

        assert group1.name in group_names
        assert group2.name in group_names

    async def test_get_group_by_id_exists(
        self, group_repository: GroupRepository, group_factory: Callable[..., Awaitable[Group]]
    ):
        """Test retrieving a group by ID when it exists."""
        group = await group_factory(name="Test Group")

        retrieved = await group_repository.get_group_by_id(group.id)

        assert retrieved is not None
        assert retrieved.id == group.id
        assert retrieved.name == "Test Group"

    async def test_get_group_by_id_not_exists(self, group_repository: GroupRepository):
        """Test retrieving a group by ID when it doesn't exist."""
        result = await group_repository.get_group_by_id(99999)

        assert result is None

    async def test_get_groups_by_user_id_empty(
        self, group_repository: GroupRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving groups for a user with no group memberships."""
        user = await user_factory(email="user@example.com", name="User")

        groups = await group_repository.get_groups_by_user_id(user.id)

        assert isinstance(groups, list)
        assert len(groups) == 0

    async def test_get_groups_by_user_id_single_user_multiple_groups(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test retrieving groups for a user who is a member of multiple groups."""
        user = await user_factory(email="user@example.com", name="User")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")
        group3 = await group_factory(name="Group 3")

        # Add user to group1 and group2, but not group3
        await group_role_binding_factory(user_id=user.id, group_id=group1.id, role=GroupRole.MEMBER.value)
        await group_role_binding_factory(user_id=user.id, group_id=group2.id, role=GroupRole.ADMIN.value)

        groups = await group_repository.get_groups_by_user_id(user.id)

        assert len(groups) >= 2

        group_ids = {group.id for group in groups}

        assert group1.id in group_ids
        assert group2.id in group_ids
        assert group3.id not in group_ids

    async def test_get_groups_by_user_id_multiple_users(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test that get_groups_by_user_id only returns groups for the specified user."""
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")

        # User1 in group1, User2 in group2
        await group_role_binding_factory(user_id=user1.id, group_id=group1.id, role=GroupRole.MEMBER.value)
        await group_role_binding_factory(user_id=user2.id, group_id=group2.id, role=GroupRole.MEMBER.value)

        # Get groups for user1
        user1_groups = await group_repository.get_groups_by_user_id(user1.id)

        assert len(user1_groups) >= 1
        assert any(group.id == group1.id for group in user1_groups)
        assert not any(group.id == group2.id for group in user1_groups)

        # Get groups for user2
        user2_groups = await group_repository.get_groups_by_user_id(user2.id)

        assert len(user2_groups) >= 1
        assert any(group.id == group2.id for group in user2_groups)
        assert not any(group.id == group1.id for group in user2_groups)

    async def test_is_member_true(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test is_member returns True when user is a member of the group."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Add user as member
        await group_role_binding_factory(user_id=user.id, group_id=group.id, role=GroupRole.MEMBER.value)

        is_member = await group_repository.is_member(group.id, user.id)

        assert is_member is True

    async def test_is_member_false(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test is_member returns False when user is not a member of the group."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        is_member = await group_repository.is_member(group.id, user.id)

        assert is_member is False

    async def test_is_member_with_different_role(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test is_member returns True regardless of role (member, admin, owner)."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Add user as admin (not member role, but still a member)
        await group_role_binding_factory(user_id=user.id, group_id=group.id, role=GroupRole.ADMIN.value)

        is_member = await group_repository.is_member(group.id, user.id)

        assert is_member is True

    async def test_is_owner_true(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test is_owner returns True when user is the owner of the group."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Add user as owner
        await group_role_binding_factory(user_id=user.id, group_id=group.id, role=GroupRole.OWNER.value)

        is_owner = await group_repository.is_owner(group.id, user.id)

        assert is_owner is True

    async def test_is_owner_false_not_owner(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
        group_role_binding_factory: Callable[..., Awaitable[GroupRoleBinding]],
    ):
        """Test is_owner returns False when user is a member but not owner."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Add user as member (not owner)
        await group_role_binding_factory(user_id=user.id, group_id=group.id, role=GroupRole.MEMBER.value)

        is_owner = await group_repository.is_owner(group.id, user.id)

        assert is_owner is False

    async def test_is_owner_false_not_member(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test is_owner returns False when user is not a member at all."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        is_owner = await group_repository.is_owner(group.id, user.id)

        assert is_owner is False

    async def test_create_group(
        self,
        group_repository: GroupRepository,
    ):
        """Test creating a new group."""
        group = create_test_group(name="New Group")

        created = await group_repository.create_group(group)

        assert created.id is not None
        assert created.name == "New Group"

        # Verify it's in the database
        retrieved = await group_repository.get_group_by_id(created.id)

        assert retrieved is not None
        assert retrieved.name == "New Group"

    async def test_update_group(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test updating an existing group."""
        # Create a group
        group = await group_factory(name="Original Name")

        # Update it
        group.name = "Updated Name"

        updated = await group_repository.update_group(group)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await group_repository.get_group_by_id(group.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_delete_group_exists(
        self,
        group_repository: GroupRepository,
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test deleting a group that exists."""
        # Create a group
        group = await group_factory(name="To Delete")

        # Delete it
        await group_repository.delete_group(group.id)

        # Verify it's gone
        retrieved = await group_repository.get_group_by_id(group.id)

        assert retrieved is None

    async def test_delete_group_not_exists(self, group_repository: GroupRepository):
        """Test deleting a group that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await group_repository.delete_group(99999)
