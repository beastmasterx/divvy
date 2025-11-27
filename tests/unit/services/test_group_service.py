"""
Unit tests for GroupService.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from app.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.models import Category, Group, GroupRole, Period, Transaction, User
from app.schemas import GroupRequest
from app.services import AuthorizationService, GroupService, UserService


@pytest.mark.unit
class TestGroupService:
    """Test suite for GroupService."""

    # ========== Get Operations ==========

    async def test_get_all_groups(self, group_service: GroupService, group_factory: Callable[..., Awaitable[Group]]):
        """Test retrieving all groups."""
        # Create some groups
        await group_factory(name="Group 1")
        await group_factory(name="Group 2")

        groups = await group_service.get_all_groups()
        assert len(groups) >= 2

        group_names = {g.name for g in groups}
        assert "Group 1" in group_names
        assert "Group 2" in group_names

    async def test_get_group_by_id_exists(self, group_service: GroupService, group_with_owner: Group):
        """Test retrieving a group by ID when it exists."""
        retrieved = await group_service.get_group_by_id(group_with_owner.id)
        assert retrieved is not None
        assert retrieved.id == group_with_owner.id
        assert retrieved.name == "Test Group"

    async def test_get_group_by_id_not_exists(self, group_service: GroupService):
        """Test retrieving a group by ID when it doesn't exist."""
        result = await group_service.get_group_by_id(99999)
        assert result is None

    async def test_get_groups_by_user_id(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        member_user: User,
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving groups that a user is a member of."""
        # Create groups
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")
        group3 = await group_factory(name="Group 3")

        # Add user to group1 and group2
        await authorization_service.assign_group_role(member_user.id, group1.id, GroupRole.MEMBER)
        await authorization_service.assign_group_role(member_user.id, group2.id, GroupRole.MEMBER)

        # Get user's groups
        groups = await group_service.get_groups_by_user_id(member_user.id)
        group_ids = {g.id for g in groups}
        assert group1.id in group_ids
        assert group2.id in group_ids
        assert group3.id not in group_ids

    async def test_get_groups_by_user_id_no_groups(self, group_service: GroupService, member_user: User):
        """Test retrieving groups for a user with no groups."""
        groups = await group_service.get_groups_by_user_id(member_user.id)
        assert len(groups) == 0

    async def test_get_group_owner(self, group_service: GroupService, owner_user: User, group_with_owner: Group):
        """Test retrieving group owner."""
        owner_id = await group_service.get_group_owner(group_with_owner.id)
        assert owner_id == owner_user.id

    async def test_get_group_owner_no_owner(
        self, group_service: GroupService, group_factory: Callable[..., Awaitable[Group]]
    ):
        """Test retrieving owner for group with no owner."""
        # Create a group without owner (we'll need to manually create one)
        group = await group_factory(name="Group without owner")

        owner_id = await group_service.get_group_owner(group.id)
        assert owner_id is None

    # ========== Create Operations ==========

    async def test_create_group(self, group_service: GroupService, owner_user: User):
        """Test creating a new group."""
        request = GroupRequest(name="New Group")
        created = await group_service.create_group(request, owner_id=owner_user.id)

        assert created.id is not None
        assert created.name == "New Group"

        # Verify it's in the database
        retrieved = await group_service.get_group_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Group"

        # Verify owner role binding exists
        owner_id = await group_service.get_group_owner(created.id)
        assert owner_id == owner_user.id

    # ========== Update Operations ==========

    async def test_update_group_exists(
        self, group_service: GroupService, group_factory: Callable[..., Awaitable[Group]]
    ):
        """Test updating an existing group."""
        group = await group_factory(name="Original Name")

        request = GroupRequest(name="Updated Name")
        updated = await group_service.update_group(group.id, request)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await group_service.get_group_by_id(group.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_update_group_not_exists(self, group_service: GroupService):
        """Test updating a non-existent group raises NotFoundError."""
        request = GroupRequest(name="Updated Name")

        with pytest.raises(NotFoundError):
            await group_service.update_group(99999, request)

    # ========== Delete Operations ==========

    async def test_delete_group_exists(self, group_service: GroupService, owner_user: User, group_with_owner: Group):
        """Test deleting a group by owner."""
        # Should succeed if no active period with transactions
        await group_service.delete_group(group_with_owner.id, current_user_id=owner_user.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group_with_owner.id)
        assert retrieved is None

    async def test_delete_group_not_exists(self, group_service: GroupService):
        """Test deleting a non-existent group raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.delete_group(99999, current_user_id=1)

    async def test_delete_group_not_owner(
        self,
        group_service: GroupService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test deleting a group by non-owner raises ForbiddenError."""
        other_user = await user_factory(email="other@example.com", name="Other")
        group = await group_factory(name="Test Group")

        # Try to delete as non-owner
        with pytest.raises(ForbiddenError, match="Only the group owner can delete"):
            await group_service.delete_group(group.id, current_user_id=other_user.id)

    # ========== Role Assignment Operations ==========

    async def test_assign_group_role_add_member(
        self,
        user_service: UserService,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test assigning member role adds user to group."""

        # Assign member role (adds user to group)
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Verify user is in group
        users = await user_service.get_users_by_group_id(group_with_owner.id)
        user_ids = {u.id for u in users}
        assert member_user.id in user_ids

        # Verify role is member
        role = await authorization_service.get_group_role(member_user.id, group_with_owner.id)
        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_add_member_already_member(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test assigning member role to existing member raises ConflictError."""
        # Add user to group first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Try to add again
        with pytest.raises(ConflictError, match="already a member"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=member_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_assign_admin(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test assigning admin role to existing member."""
        # Add user as member first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Promote to admin
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.ADMIN,
            assigned_by_user_id=owner_user.id,
        )

        # Verify role is admin
        role = await authorization_service.get_group_role(member_user.id, group_with_owner.id)
        assert role == GroupRole.ADMIN.value

    async def test_assign_group_role_assign_admin_not_member(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test assigning admin role to non-member raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=member_user.id,
                role=GroupRole.ADMIN,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_transfer_ownership(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test transferring ownership."""
        # Add user as member first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Transfer ownership
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.OWNER,
            assigned_by_user_id=owner_user.id,
        )

        # Verify new owner
        owner_id = await group_service.get_group_owner(group_with_owner.id)
        assert owner_id == member_user.id

        # Verify old owner is now member
        old_owner_role = await authorization_service.get_group_role(owner_user.id, group_with_owner.id)
        assert old_owner_role == GroupRole.MEMBER.value

    async def test_assign_group_role_transfer_ownership_not_owner(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        user_factory: Any,
    ):
        """Test transferring ownership by non-owner raises ForbiddenError."""
        # Add user as member
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Create another user
        other_user = await user_factory(email="other@example.com", name="Other")

        # Add other user as admin
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=other_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=other_user.id,
            role=GroupRole.ADMIN,
            assigned_by_user_id=owner_user.id,
        )

        # Try to transfer ownership as admin (not owner)
        with pytest.raises(ForbiddenError, match="Only the current owner can transfer"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=member_user.id,
                role=GroupRole.OWNER,
                assigned_by_user_id=other_user.id,
            )

    async def test_assign_group_role_transfer_to_non_member(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test transferring ownership to non-member (auto-adds as member first)."""
        # Transfer ownership to non-member
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.OWNER,
            assigned_by_user_id=owner_user.id,
        )

        # Verify new owner
        owner_id = await group_service.get_group_owner(group_with_owner.id)
        assert owner_id == member_user.id

    async def test_assign_group_role_remove_user(
        self,
        user_service: UserService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test removing user from group (role=None)."""
        # Add user to group first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Remove user from group
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=None,
            assigned_by_user_id=owner_user.id,
        )

        # Verify user is not in group
        users = await user_service.get_users_by_group_id(group_with_owner.id)
        user_ids = {u.id for u in users}
        assert member_user.id not in user_ids

    async def test_assign_group_role_remove_user_not_member(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test removing non-member raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=member_user.id,
                role=None,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_invalid_group(
        self, group_service: GroupService, owner_user: User, member_user: User
    ):
        """Test assigning role with invalid group raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.assign_group_role(
                group_id=99999,
                user_id=member_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_invalid_user(
        self, group_service: GroupService, owner_user: User, group_with_owner: Group
    ):
        """Test assigning role with invalid user raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=99999,
                role=GroupRole.MEMBER,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_no_permission(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test assigning role without permission raises ForbiddenError."""
        # Add user as member (not admin)
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Create another user
        other_user = await user_factory(email="other@example.com", name="Other")

        # Try to assign role as member (no permission)
        with pytest.raises(ForbiddenError, match="Permission denied"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=other_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=member_user.id,  # Member trying to assign
            )

    async def test_assign_group_role_remove_user_with_unsettled_period(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test removing user when active period has transactions raises BusinessRuleError."""

        # Add user to group
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Create active period with transactions
        category = await category_factory(name="Test Category")

        period = await period_factory(group_id=group_with_owner.id, name="Active Period")

        _ = await transaction_factory(payer_id=owner_user.id, category_id=category.id, period_id=period.id)

        # Try to remove user - should fail
        with pytest.raises(BusinessRuleError, match="not settled"):
            await group_service.assign_group_role(
                group_id=group_with_owner.id,
                user_id=member_user.id,
                role=None,
                assigned_by_user_id=owner_user.id,
            )

    async def test_assign_group_role_remove_user_with_settled_period(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test removing user when active period is settled succeeds."""
        from datetime import UTC, datetime

        # Add user to group
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Create settled period (has end_date)
        _ = await period_factory(group_id=group_with_owner.id, name="Settled Period", end_date=datetime.now(UTC))

        # Should succeed - period is settled
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=None,
            assigned_by_user_id=owner_user.id,
        )

        # Verify user is removed
        role = await authorization_service.get_group_role(member_user.id, group_with_owner.id)
        assert role is None

    async def test_assign_group_role_remove_user_no_active_period(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test removing user when no active period succeeds."""
        # Add user to group
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=owner_user.id,
        )

        # Should succeed - no active period
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=None,
            assigned_by_user_id=owner_user.id,
        )

        # Verify user is removed
        role = await authorization_service.get_group_role(member_user.id, group_with_owner.id)
        assert role is None

    async def test_delete_group_with_unsettled_period(
        self,
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
        group_service: GroupService,
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test deleting group with active period and transactions raises BusinessRuleError."""

        # Create active period with transactions
        category = await category_factory(name="Test Category")

        period = await period_factory(group_id=group_with_owner.id, name="Active Period")

        _ = await transaction_factory(payer_id=owner_user.id, category_id=category.id, period_id=period.id)

        # Try to delete group - should fail
        with pytest.raises(BusinessRuleError, match="not settled"):
            await group_service.delete_group(group_with_owner.id, current_user_id=owner_user.id)

    async def test_delete_group_with_settled_period(
        self,
        period_factory: Callable[..., Awaitable[Period]],
        group_service: GroupService,
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test deleting group with settled period succeeds."""
        from datetime import UTC, datetime

        # Create settled period (has end_date)
        _ = await period_factory(group_id=group_with_owner.id, name="Settled Period", end_date=datetime.now(UTC))

        # Should succeed - period is settled
        await group_service.delete_group(group_with_owner.id, current_user_id=owner_user.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group_with_owner.id)
        assert retrieved is None
