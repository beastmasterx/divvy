"""
Unit tests for GroupService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.models import Group, GroupRole, User
from app.schemas import GroupRequest
from app.services import AuthorizationService, GroupService, PeriodService
from tests.fixtures.factories import create_test_group, create_test_user


@pytest.mark.unit
class TestGroupService:
    """Test suite for GroupService."""

    @pytest.fixture
    async def group_service(self, db_session: AsyncSession) -> GroupService:
        """Create a GroupService instance for testing."""
        auth_service = AuthorizationService(db_session)
        period_service = PeriodService(db_session)
        return GroupService(db_session, auth_service, period_service)

    @pytest.fixture
    async def test_owner(self, db_session: AsyncSession) -> User:
        """Create a test owner user."""
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession) -> User:
        """Create a test user."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def test_group_with_owner(self, db_session: AsyncSession, test_owner: User) -> Group:
        """Create a test group with owner role binding."""
        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(test_owner.id, group.id, GroupRole.OWNER)

        return group

    # ========== Get Operations ==========

    async def test_get_all_groups(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving all groups."""
        # Create some groups
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group1 = create_test_group(name="Group 1")
        group2 = create_test_group(name="Group 2")
        db_session.add(group1)
        db_session.add(group2)
        await db_session.commit()

        groups = await group_service.get_all_groups()
        assert len(groups) >= 2

        group_names = {g.name for g in groups}
        assert "Group 1" in group_names
        assert "Group 2" in group_names

    async def test_get_group_by_id_exists(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving a group by ID when it exists."""
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        retrieved = await group_service.get_group_by_id(group.id)
        assert retrieved is not None
        assert retrieved.id == group.id
        assert retrieved.name == "Test Group"

    async def test_get_group_by_id_not_exists(self, group_service: GroupService):
        """Test retrieving a group by ID when it doesn't exist."""
        result = await group_service.get_group_by_id(99999)
        assert result is None

    async def test_get_groups_by_user_id(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving groups that a user is a member of."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        # Create groups
        group1 = create_test_group(name="Group 1")
        group2 = create_test_group(name="Group 2")
        group3 = create_test_group(name="Group 3")
        db_session.add_all([group1, group2, group3])
        await db_session.commit()

        # Add user to group1 and group2
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(user.id, group1.id, GroupRole.MEMBER)
        await auth_service.assign_group_role(user.id, group2.id, GroupRole.MEMBER)

        # Get user's groups
        groups = await group_service.get_groups_by_user_id(user.id)
        group_ids = {g.id for g in groups}
        assert group1.id in group_ids
        assert group2.id in group_ids
        assert group3.id not in group_ids

    async def test_get_groups_by_user_id_no_groups(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving groups for a user with no groups."""
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        groups = await group_service.get_groups_by_user_id(user.id)
        assert len(groups) == 0

    async def test_get_group_owner(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving group owner."""
        owner = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(owner)
        await db_session.commit()

        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        # Assign owner role
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        owner_id = await group_service.get_group_owner(group.id)
        assert owner_id == owner.id

    async def test_get_group_owner_no_owner(self, db_session: AsyncSession, group_service: GroupService):
        """Test retrieving owner for group with no owner."""
        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        owner_id = await group_service.get_group_owner(group.id)
        assert owner_id is None

    # ========== Create Operations ==========

    async def test_create_group(self, db_session: AsyncSession, group_service: GroupService):
        """Test creating a new group."""
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        request = GroupRequest(name="New Group")
        created = await group_service.create_group(request, owner_id=user.id)

        assert created.id is not None
        assert created.name == "New Group"

        # Verify it's in the database
        retrieved = await group_service.get_group_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Group"

        # Verify owner role binding exists
        owner_id = await group_service.get_group_owner(created.id)
        assert owner_id == user.id

    # ========== Update Operations ==========

    async def test_update_group_exists(self, db_session: AsyncSession, group_service: GroupService):
        """Test updating an existing group."""
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Original Name")
        db_session.add(group)
        await db_session.commit()

        # Create owner role binding
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(user.id, group.id, GroupRole.OWNER)

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

    async def test_delete_group_exists(self, db_session: AsyncSession, group_service: GroupService):
        """Test deleting a group by owner."""
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="To Delete")
        db_session.add(group)
        await db_session.commit()
        group_id = group.id

        # Create owner role binding
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(user.id, group_id, GroupRole.OWNER)

        # Should succeed if no active period with transactions
        await group_service.delete_group(group_id, current_user_id=user.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group_id)
        assert retrieved is None

    async def test_delete_group_not_exists(self, group_service: GroupService):
        """Test deleting a non-existent group raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.delete_group(99999, current_user_id=1)

    async def test_delete_group_not_owner(self, db_session: AsyncSession, group_service: GroupService):
        """Test deleting a group by non-owner raises ForbiddenError."""
        owner = create_test_user(email="owner@example.com", name="Owner")
        other_user = create_test_user(email="other@example.com", name="Other")
        db_session.add_all([owner, other_user])
        await db_session.commit()

        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        # Create owner role binding
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        # Try to delete as non-owner
        with pytest.raises(ForbiddenError, match="Only the group owner can delete"):
            await group_service.delete_group(group.id, current_user_id=other_user.id)

    # ========== Role Assignment Operations ==========

    async def test_assign_group_role_add_member(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test assigning member role adds user to group."""
        from app.services import UserService

        user_service = UserService(db_session)

        # Assign member role (adds user to group)
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Verify user is in group
        users = await user_service.get_users_by_group_id(test_group_with_owner.id)
        user_ids = {u.id for u in users}
        assert test_user.id in user_ids

        # Verify role is member
        auth_service = AuthorizationService(db_session)
        role = await auth_service.get_group_role(test_user.id, test_group_with_owner.id)
        assert role == GroupRole.MEMBER.value

    async def test_assign_group_role_add_member_already_member(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test assigning member role to existing member raises ConflictError."""
        # Add user to group first
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Try to add again
        with pytest.raises(ConflictError, match="already a member"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=test_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_assign_admin(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test assigning admin role to existing member."""
        # Add user as member first
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Promote to admin
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.ADMIN,
            assigned_by_user_id=test_owner.id,
        )

        # Verify role is admin
        auth_service = AuthorizationService(db_session)
        role = await auth_service.get_group_role(test_user.id, test_group_with_owner.id)
        assert role == GroupRole.ADMIN.value

    async def test_assign_group_role_assign_admin_not_member(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test assigning admin role to non-member raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=test_user.id,
                role=GroupRole.ADMIN,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_transfer_ownership(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test transferring ownership."""
        # Add user as member first
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Transfer ownership
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.OWNER,
            assigned_by_user_id=test_owner.id,
        )

        # Verify new owner
        owner_id = await group_service.get_group_owner(test_group_with_owner.id)
        assert owner_id == test_user.id

        # Verify old owner is now member
        auth_service = AuthorizationService(db_session)
        old_owner_role = await auth_service.get_group_role(test_owner.id, test_group_with_owner.id)
        assert old_owner_role == GroupRole.MEMBER.value

    async def test_assign_group_role_transfer_ownership_not_owner(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test transferring ownership by non-owner raises ForbiddenError."""
        # Add user as member
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Create another user
        other_user = create_test_user(email="other@example.com", name="Other")
        db_session.add(other_user)
        await db_session.commit()

        # Add other user as admin
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=other_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=other_user.id,
            role=GroupRole.ADMIN,
            assigned_by_user_id=test_owner.id,
        )

        # Try to transfer ownership as admin (not owner)
        with pytest.raises(ForbiddenError, match="Only the current owner can transfer"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=test_user.id,
                role=GroupRole.OWNER,
                assigned_by_user_id=other_user.id,
            )

    async def test_assign_group_role_transfer_to_non_member(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test transferring ownership to non-member (auto-adds as member first)."""
        # Transfer ownership to non-member
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.OWNER,
            assigned_by_user_id=test_owner.id,
        )

        # Verify new owner
        owner_id = await group_service.get_group_owner(test_group_with_owner.id)
        assert owner_id == test_user.id

    async def test_assign_group_role_remove_user(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test removing user from group (role=None)."""
        from app.services import UserService

        user_service = UserService(db_session)

        # Add user to group first
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Remove user from group
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=None,
            assigned_by_user_id=test_owner.id,
        )

        # Verify user is not in group
        users = await user_service.get_users_by_group_id(test_group_with_owner.id)
        user_ids = {u.id for u in users}
        assert test_user.id not in user_ids

    async def test_assign_group_role_remove_user_not_member(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test removing non-member raises NotFoundError."""
        with pytest.raises(NotFoundError, match="not a member"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=test_user.id,
                role=None,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_invalid_group(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User
    ):
        """Test assigning role with invalid group raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.assign_group_role(
                group_id=99999,
                user_id=test_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_invalid_user(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_group_with_owner: Group
    ):
        """Test assigning role with invalid user raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=99999,
                role=GroupRole.MEMBER,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_no_permission(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test assigning role without permission raises ForbiddenError."""
        # Add user as member (not admin)
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Create another user
        other_user = create_test_user(email="other@example.com", name="Other")
        db_session.add(other_user)
        await db_session.commit()

        # Try to assign role as member (no permission)
        with pytest.raises(ForbiddenError, match="Permission denied"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=other_user.id,
                role=GroupRole.MEMBER,
                assigned_by_user_id=test_user.id,  # Member trying to assign
            )

    async def test_assign_group_role_remove_user_with_unsettled_period(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test removing user when active period has transactions raises BusinessRuleError."""
        from tests.fixtures.factories import create_test_category, create_test_period, create_test_transaction

        # Add user to group
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Create active period with transactions
        category = create_test_category(name="Test Category")
        db_session.add(category)
        await db_session.commit()

        period = create_test_period(group_id=test_group_with_owner.id, name="Active Period")
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(payer_id=test_owner.id, category_id=category.id, period_id=period.id)
        db_session.add(transaction)
        await db_session.commit()

        # Try to remove user - should fail
        with pytest.raises(BusinessRuleError, match="not settled"):
            await group_service.assign_group_role(
                group_id=test_group_with_owner.id,
                user_id=test_user.id,
                role=None,
                assigned_by_user_id=test_owner.id,
            )

    async def test_assign_group_role_remove_user_with_settled_period(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test removing user when active period is settled succeeds."""
        from datetime import UTC, datetime

        from tests.fixtures.factories import create_test_period

        # Add user to group
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Create settled period (has end_date)
        period = create_test_period(
            group_id=test_group_with_owner.id, name="Settled Period", end_date=datetime.now(UTC)
        )
        db_session.add(period)
        await db_session.commit()

        # Should succeed - period is settled
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=None,
            assigned_by_user_id=test_owner.id,
        )

        # Verify user is removed
        auth_service = AuthorizationService(db_session)
        role = await auth_service.get_group_role(test_user.id, test_group_with_owner.id)
        assert role is None

    async def test_assign_group_role_remove_user_no_active_period(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User, test_user: User, test_group_with_owner: Group
    ):
        """Test removing user when no active period succeeds."""
        # Add user to group
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=GroupRole.MEMBER,
            assigned_by_user_id=test_owner.id,
        )

        # Should succeed - no active period
        await group_service.assign_group_role(
            group_id=test_group_with_owner.id,
            user_id=test_user.id,
            role=None,
            assigned_by_user_id=test_owner.id,
        )

        # Verify user is removed
        auth_service = AuthorizationService(db_session)
        role = await auth_service.get_group_role(test_user.id, test_group_with_owner.id)
        assert role is None

    async def test_delete_group_with_unsettled_period(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User
    ):
        """Test deleting group with active period and transactions raises BusinessRuleError."""
        from tests.fixtures.factories import create_test_category, create_test_period, create_test_transaction

        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        # Create owner role binding
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(test_owner.id, group.id, GroupRole.OWNER)

        # Create active period with transactions
        category = create_test_category(name="Test Category")
        db_session.add(category)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Active Period")
        db_session.add(period)
        await db_session.commit()

        transaction = create_test_transaction(payer_id=test_owner.id, category_id=category.id, period_id=period.id)
        db_session.add(transaction)
        await db_session.commit()

        # Try to delete group - should fail
        with pytest.raises(BusinessRuleError, match="not settled"):
            await group_service.delete_group(group.id, current_user_id=test_owner.id)

    async def test_delete_group_with_settled_period(
        self, db_session: AsyncSession, group_service: GroupService, test_owner: User
    ):
        """Test deleting group with settled period succeeds."""
        from datetime import UTC, datetime

        from tests.fixtures.factories import create_test_period

        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        # Create owner role binding
        auth_service = AuthorizationService(db_session)
        await auth_service.assign_group_role(test_owner.id, group.id, GroupRole.OWNER)

        # Create settled period (has end_date)
        period = create_test_period(group_id=group.id, name="Settled Period", end_date=datetime.now(UTC))
        db_session.add(period)
        await db_session.commit()

        # Should succeed - period is settled
        await group_service.delete_group(group.id, current_user_id=test_owner.id)

        # Verify group is deleted
        retrieved = await group_service.get_group_by_id(group.id)
        assert retrieved is None
