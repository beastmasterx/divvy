"""
Unit tests for AuthorizationService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import ValidationError
from app.models import Group, GroupRole, Period, SystemRole, Transaction, User
from app.services import AuthorizationService


@pytest.mark.unit
class TestAuthorizationService:
    """Test suite for AuthorizationService."""

    # ============================================================================
    # System Role Management
    # ============================================================================

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

    async def test_assign_system_role_all_roles(
        self, authorization_service: AuthorizationService, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test assigning all valid system roles."""
        user = await user_factory(email="user@example.com", name="User")

        # Test all system roles
        for system_role in SystemRole:
            await authorization_service.assign_system_role(user.id, system_role)
            role = await authorization_service.get_system_role(user.id)
            assert role == system_role.value

    # ============================================================================
    # Group Role Management - Direct Group Access
    # ============================================================================

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

        role = await authorization_service.get_group_role_by_group_id(user.id, group.id)

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

        role = await authorization_service.get_group_role_by_group_id(user.id, group.id)

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

        role = await authorization_service.get_group_role_by_group_id(user.id, group.id)

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

        assert await authorization_service.get_group_role_by_group_id(user.id, group.id) == GroupRole.MEMBER.value

        # Update to admin
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)

        assert await authorization_service.get_group_role_by_group_id(user.id, group.id) == GroupRole.ADMIN.value

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

        assert await authorization_service.get_group_role_by_group_id(user.id, group.id) == GroupRole.MEMBER.value

        # Remove role
        await authorization_service.assign_group_role(user.id, group.id, None)

        # Verify it's removed
        role = await authorization_service.get_group_role_by_group_id(user.id, group.id)

        assert role is None

    async def test_assign_group_role_all_roles(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test assigning all valid group roles."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        # Test all group roles
        for group_role in GroupRole:
            await authorization_service.assign_group_role(user.id, group.id, group_role)
            role = await authorization_service.get_group_role_by_group_id(user.id, group.id)
            assert role == group_role.value

    async def test_assign_group_role_multiple_groups(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test user can have different roles in different groups."""
        user = await user_factory(email="user@example.com", name="User")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")

        # Assign different roles in different groups
        await authorization_service.assign_group_role(user.id, group1.id, GroupRole.MEMBER)
        await authorization_service.assign_group_role(user.id, group2.id, GroupRole.ADMIN)

        role1 = await authorization_service.get_group_role_by_group_id(user.id, group1.id)
        role2 = await authorization_service.get_group_role_by_group_id(user.id, group2.id)

        assert role1 == GroupRole.MEMBER.value
        assert role2 == GroupRole.ADMIN.value

    # ============================================================================
    # Group Role Management - Period-based Access
    # ============================================================================

    async def test_get_group_role_by_period_id_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving group role by period ID when user has role in period's group."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Assign group role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.ADMIN)

        role = await authorization_service.get_group_role_by_period_id(user.id, period.id)

        assert role == GroupRole.ADMIN.value

    async def test_get_group_role_by_period_id_not_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving group role by period ID when user has no role in period's group."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        role = await authorization_service.get_group_role_by_period_id(user.id, period.id)

        assert role is None

    async def test_get_group_role_by_period_id_different_group(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test retrieving group role by period ID when user has role in different group."""
        user = await user_factory(email="user@example.com", name="User")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")
        period = await period_factory(group_id=group1.id, name="Test Period")

        # Assign role in group2, but period is in group1
        await authorization_service.assign_group_role(user.id, group2.id, GroupRole.ADMIN)

        role = await authorization_service.get_group_role_by_period_id(user.id, period.id)

        assert role is None

    # ============================================================================
    # Group Role Management - Transaction-based Access
    # ============================================================================

    async def test_get_group_role_by_transaction_id_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving group role by transaction ID when user has role."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")
        transaction = await transaction_factory(period_id=period.id, payer_id=user.id)

        # Assign group role
        await authorization_service.assign_group_role(user.id, group.id, GroupRole.MEMBER)

        role = await authorization_service.get_group_role_by_transaction_id(user.id, transaction.id)

        assert role == GroupRole.MEMBER.value

    async def test_get_group_role_by_transaction_id_not_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving group role by transaction ID when user has no role."""
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")
        transaction = await transaction_factory(period_id=period.id, payer_id=user.id)

        role = await authorization_service.get_group_role_by_transaction_id(user.id, transaction.id)

        assert role is None

    async def test_get_group_role_by_transaction_id_different_group(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving group role by transaction ID when user has role in different group."""
        user = await user_factory(email="user@example.com", name="User")
        group1 = await group_factory(name="Group 1")
        group2 = await group_factory(name="Group 2")
        period = await period_factory(group_id=group1.id, name="Test Period")
        transaction = await transaction_factory(period_id=period.id, payer_id=user.id)

        # Assign role in group2, but transaction's period is in group1
        await authorization_service.assign_group_role(user.id, group2.id, GroupRole.ADMIN)

        role = await authorization_service.get_group_role_by_transaction_id(user.id, transaction.id)

        assert role is None

    # ============================================================================
    # Group Owner Management
    # ============================================================================

    async def test_get_group_owner_exists(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group owner when owner exists."""
        owner = await user_factory(email="owner@example.com", name="Owner")
        group = await group_factory(name="Test Group")

        # Assign owner role
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        owner_id = await authorization_service.get_group_owner(group.id)

        assert owner_id == owner.id

    async def test_get_group_owner_not_exists(
        self,
        authorization_service: AuthorizationService,
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group owner when no owner exists."""
        group = await group_factory(name="Test Group")

        owner_id = await authorization_service.get_group_owner(group.id)

        assert owner_id is None

    async def test_get_group_owner_multiple_members(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group owner when group has multiple members."""
        owner = await user_factory(email="owner@example.com", name="Owner")
        member1 = await user_factory(email="member1@example.com", name="Member 1")
        member2 = await user_factory(email="member2@example.com", name="Member 2")
        group = await group_factory(name="Test Group")

        # Assign roles
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)
        await authorization_service.assign_group_role(member1.id, group.id, GroupRole.MEMBER)
        await authorization_service.assign_group_role(member2.id, group.id, GroupRole.ADMIN)

        owner_id = await authorization_service.get_group_owner(group.id)

        assert owner_id == owner.id

    async def test_get_group_owner_after_ownership_transfer(
        self,
        authorization_service: AuthorizationService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test retrieving group owner after ownership transfer."""
        original_owner = await user_factory(email="owner1@example.com", name="Owner 1")
        new_owner = await user_factory(email="owner2@example.com", name="Owner 2")
        group = await group_factory(name="Test Group")

        # Assign original owner
        await authorization_service.assign_group_role(original_owner.id, group.id, GroupRole.OWNER)
        assert await authorization_service.get_group_owner(group.id) == original_owner.id

        # Transfer ownership
        await authorization_service.assign_group_role(new_owner.id, group.id, GroupRole.OWNER)
        await authorization_service.assign_group_role(original_owner.id, group.id, GroupRole.MEMBER)

        owner_id = await authorization_service.get_group_owner(group.id)

        assert owner_id == new_owner.id
        assert owner_id != original_owner.id
