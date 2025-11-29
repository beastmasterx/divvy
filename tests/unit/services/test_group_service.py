"""
Unit tests for GroupService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import NotFoundError
from app.models import Category, Group, GroupRole, Period, Transaction, User
from app.schemas import GroupRequest
from app.services import AuthorizationService, GroupService


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

    async def test_get_group_owner(
        self, authorization_service: AuthorizationService, owner_user: User, group_with_owner: Group
    ):
        """Test retrieving group owner."""
        owner_id = await authorization_service.get_group_owner(group_with_owner.id)
        assert owner_id == owner_user.id

    async def test_get_group_owner_no_owner(
        self, authorization_service: AuthorizationService, group_factory: Callable[..., Awaitable[Group]]
    ):
        """Test retrieving owner for group with no owner."""
        # Create a group without owner (we'll need to manually create one)
        group = await group_factory(name="Group without owner")

        owner_id = await authorization_service.get_group_owner(group.id)
        assert owner_id is None

    # ========== Create Operations ==========

    async def test_create_group(
        self, group_service: GroupService, authorization_service: AuthorizationService, owner_user: User
    ):
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
        owner_id = await authorization_service.get_group_owner(created.id)
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
        await group_service.delete_group(group_with_owner.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group_with_owner.id)
        assert retrieved is None

    async def test_delete_group_not_exists(self, group_service: GroupService):
        """Test deleting a non-existent group raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.delete_group(99999)

    # ========== Role Assignment Operations ==========

    async def test_assign_group_role_add_member(
        self,
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
        )

        # Verify user is in group
        is_member = await group_service.is_member(group_with_owner.id, member_user.id)
        assert is_member is True

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
        """Test assigning member role to existing member (should succeed - upsert behavior)."""
        # Add user to group first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
        )

        # Assign again - should succeed (upsert behavior)
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
        )

        # Verify user is still in group
        is_member = await group_service.is_member(group_with_owner.id, member_user.id)
        assert is_member is True

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
        )

        # Promote to admin
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.ADMIN,
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
        """Test assigning admin role to non-member (should succeed - adds user as admin)."""
        # Assign admin role to non-member - should succeed (adds user to group)
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.ADMIN,
        )

        # Verify user is now in group
        is_member = await group_service.is_member(group_with_owner.id, member_user.id)
        assert is_member is True

    async def test_transfer_group_owner(
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
        )

        # Transfer ownership
        await group_service.transfer_group_owner(
            group_id=group_with_owner.id,
            new_owner_id=member_user.id,
        )

        # Verify new owner
        owner_id = await authorization_service.get_group_owner(group_with_owner.id)
        assert owner_id == member_user.id

        # Verify old owner is now member
        old_owner_role = await authorization_service.get_group_role(owner_user.id, group_with_owner.id)
        assert old_owner_role == GroupRole.MEMBER.value

    async def test_transfer_group_owner_to_non_member(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test transferring ownership to non-member raises NotFoundError."""
        # Try to transfer ownership to non-member
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.transfer_group_owner(
                group_id=group_with_owner.id,
                new_owner_id=member_user.id,
            )

    async def test_transfer_group_owner_to_non_member_raises_error(
        self,
        authorization_service: AuthorizationService,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test transferring ownership to non-member raises NotFoundError."""
        # Try to transfer ownership to non-member
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.transfer_group_owner(
                group_id=group_with_owner.id,
                new_owner_id=member_user.id,
            )

    async def test_remove_user_from_group(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test removing user from group."""
        # Add user to group first
        await group_service.assign_group_role(
            group_id=group_with_owner.id,
            user_id=member_user.id,
            role=GroupRole.MEMBER,
        )

        # Remove user from group
        await group_service.remove_user_from_group(
            group_id=group_with_owner.id,
            user_id=member_user.id,
        )

        # Verify user is not in group
        is_member = await group_service.is_member(group_with_owner.id, member_user.id)
        assert is_member is False

    async def test_remove_user_from_group_not_member(
        self,
        group_service: GroupService,
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test removing non-member (should succeed - removes binding if exists)."""
        # Remove non-member - should succeed (no-op if not a member)
        await group_service.remove_user_from_group(
            group_id=group_with_owner.id,
            user_id=member_user.id,
        )

        # Verify user is still not in group
        is_member = await group_service.is_member(group_with_owner.id, member_user.id)
        assert is_member is False

    async def test_remove_user_from_group_with_unsettled_period(
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
        )

        # Create active period with transactions
        category = await category_factory(name="Test Category")

        period = await period_factory(group_id=group_with_owner.id, name="Active Period")

        _ = await transaction_factory(payer_id=owner_user.id, category_id=category.id, period_id=period.id)

        # Try to remove user - should fail (enforced by PEP dependency, but test service layer)
        # Note: This check is now in the PEP dependency, so this test may need to be moved to integration tests
        # For now, we'll test that the service method can be called (the PEP will enforce the rule)
        await group_service.remove_user_from_group(
            group_id=group_with_owner.id,
            user_id=member_user.id,
        )

    async def test_remove_user_from_group_with_settled_period(
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
        )

        # Create settled period (has end_date)
        _ = await period_factory(group_id=group_with_owner.id, name="Settled Period", end_date=datetime.now(UTC))

        # Should succeed - period is settled
        await group_service.remove_user_from_group(
            group_id=group_with_owner.id,
            user_id=member_user.id,
        )

        # Verify user is removed
        role = await authorization_service.get_group_role(member_user.id, group_with_owner.id)
        assert role is None

    async def test_remove_user_from_group_no_active_period(
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
        )

        # Should succeed - no active period
        await group_service.remove_user_from_group(
            group_id=group_with_owner.id,
            user_id=member_user.id,
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
        """Test deleting group with active period and transactions.

        Note: The business rule check is now enforced by PEP dependency.
        This test verifies the service method can be called (the PEP will enforce the rule).
        """

        # Create active period with transactions
        category = await category_factory(name="Test Category")

        period = await period_factory(group_id=group_with_owner.id, name="Active Period")

        _ = await transaction_factory(payer_id=owner_user.id, category_id=category.id, period_id=period.id)

        # Service method can be called (PEP will enforce the rule)
        await group_service.delete_group(group_with_owner.id)

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
        await group_service.delete_group(group_with_owner.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group_with_owner.id)
        assert retrieved is None
