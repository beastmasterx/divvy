"""
Data fixtures for testing (users, groups, transactions, etc.).

This module provides factory fixtures organized into logical sections:
- Core entity factories: Basic entities (users, groups)
- Authentication factories: Auth-related entities (identities, tokens, account links)
- Business entity factories: Domain entities (categories, periods, transactions, settlements)
- Low-level binding factories: Direct model creation (for repository unit tests)
- High-level service factories: Service-based creation (for API/integration tests)
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AccountLinkRequest,
    Category,
    Group,
    GroupRole,
    GroupRoleBinding,
    IdentityProviderName,
    Period,
    RefreshToken,
    Settlement,
    SystemRole,
    SystemRoleBinding,
    Transaction,
    User,
    UserIdentity,
)
from app.services import AuthorizationService
from tests.fixtures.factories import (
    create_test_account_link_request,
    create_test_category,
    create_test_group,
    create_test_period,
    create_test_refresh_token,
    create_test_settlement,
    create_test_transaction,
    create_test_user,
    create_test_user_identity,
)

# ============================================================================
# Core Entity Factories
# ============================================================================


@pytest.fixture
def user_factory(db_session: AsyncSession) -> Callable[..., Awaitable[User]]:
    """Factory fixture for creating multiple users (transient-like)."""

    async def _create_user(email: str, name: str, **kwargs: Any) -> User:
        user = create_test_user(email=email, name=name, **kwargs)
        db_session.add(user)
        await db_session.commit()
        return user

    return _create_user


@pytest.fixture
def group_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Group]]:
    """Factory fixture for creating multiple groups (transient-like)."""

    async def _create_group(name: str, **kwargs: Any) -> Group:
        group = create_test_group(name=name, **kwargs)
        db_session.add(group)
        await db_session.commit()

        return group

    return _create_group


# ============================================================================
# Authentication Factories
# ============================================================================


@pytest.fixture
async def user_identity_factory(db_session: AsyncSession) -> Callable[..., Awaitable[UserIdentity]]:
    """Factory fixture for creating user identities."""

    async def _create_user_identity(
        user_id: int = 1,
        identity_provider: IdentityProviderName = IdentityProviderName.MICROSOFT,
        external_id: str = "external_123",
        external_email: str | None = "external@example.com",
        external_username: str | None = "external_user",
        **kwargs: Any,
    ) -> UserIdentity:
        user_identity = create_test_user_identity(
            user_id=user_id,
            identity_provider=identity_provider,
            external_id=external_id,
            external_email=external_email,
            external_username=external_username,
            **kwargs,
        )
        db_session.add(user_identity)
        await db_session.commit()
        return user_identity

    return _create_user_identity


@pytest.fixture
async def account_link_request_factory(db_session: AsyncSession) -> Callable[..., Awaitable[AccountLinkRequest]]:
    """Factory fixture for creating account link requests."""

    async def _create_account_link_request(
        user_id: int = 1,
        identity_provider: IdentityProviderName = IdentityProviderName.MICROSOFT,
        external_id: str = "external_123",
        **kwargs: Any,
    ) -> AccountLinkRequest:
        account_link_request = create_test_account_link_request(
            user_id=user_id, identity_provider=identity_provider, external_id=external_id, **kwargs
        )
        db_session.add(account_link_request)
        await db_session.commit()
        return account_link_request

    return _create_account_link_request


@pytest.fixture
async def refresh_token_factory(db_session: AsyncSession) -> Callable[..., Awaitable[RefreshToken]]:
    """Factory fixture for creating refresh tokens."""

    async def _create_refresh_token(
        id: str = "test_token_123",
        user_id: int = 1,
        device_info: str | None = "Test Device",
        is_revoked: bool = False,
        **kwargs: Any,
    ) -> RefreshToken:
        refresh_token = create_test_refresh_token(
            id=id, user_id=user_id, device_info=device_info, is_revoked=is_revoked, **kwargs
        )
        db_session.add(refresh_token)
        await db_session.commit()
        return refresh_token

    return _create_refresh_token


# ============================================================================
# Business Entity Factories
# ============================================================================


@pytest.fixture
def category_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Category]]:
    """Factory fixture for creating categories."""

    async def _create_category(name: str, **kwargs: Any) -> Category:
        category = create_test_category(name=name, **kwargs)
        db_session.add(category)
        await db_session.commit()
        return category

    return _create_category


@pytest.fixture
def period_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Period]]:
    """Factory fixture for creating periods."""

    async def _create_period(group_id: int, name: str, **kwargs: Any) -> Period:
        period = create_test_period(group_id=group_id, name=name, **kwargs)
        db_session.add(period)
        await db_session.commit()
        return period

    return _create_period


@pytest.fixture
def transaction_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Transaction]]:
    """Factory fixture for creating transactions."""

    async def _create_transaction(
        payer_id: int = 1, category_id: int = 1, period_id: int = 1, **kwargs: Any
    ) -> Transaction:
        transaction = create_test_transaction(payer_id=payer_id, category_id=category_id, period_id=period_id, **kwargs)
        db_session.add(transaction)
        await db_session.commit()
        return transaction

    return _create_transaction


@pytest.fixture
def settlement_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Settlement]]:
    """Factory fixture for creating settlements."""

    async def _create_settlement(
        period_id: int = 1, payer_id: int = 1, payee_id: int = 2, amount: int = 5000, **kwargs: Any
    ) -> Settlement:
        settlement = create_test_settlement(
            period_id=period_id, payer_id=payer_id, payee_id=payee_id, amount=amount, **kwargs
        )
        db_session.add(settlement)
        await db_session.commit()
        return settlement

    return _create_settlement


# ============================================================================
# Low-Level Binding Factories (for Repository Unit Tests)
# ============================================================================
# These factories create role bindings directly, bypassing the service layer.
# Use these in repository unit tests to test repository methods in isolation.


@pytest.fixture
def system_role_binding_factory(db_session: AsyncSession) -> Callable[..., Awaitable[SystemRoleBinding]]:
    """Factory for creating system role bindings directly (bypasses service layer).

    Use in repository unit tests when testing repository methods in isolation.
    """

    async def _create_system_role_binding(user_id: int, role: str, **kwargs: Any) -> SystemRoleBinding:
        binding = SystemRoleBinding(user_id=user_id, role=role, **kwargs)
        db_session.add(binding)
        await db_session.commit()
        return binding

    return _create_system_role_binding


@pytest.fixture
def group_role_binding_factory(db_session: AsyncSession) -> Callable[..., Awaitable[GroupRoleBinding]]:
    """Factory for creating group role bindings directly (bypasses service layer).

    Use in repository unit tests when testing repository methods in isolation.
    """

    async def _create_group_role_binding(user_id: int, group_id: int, role: str, **kwargs: Any) -> GroupRoleBinding:
        binding = GroupRoleBinding(user_id=user_id, group_id=group_id, role=role, **kwargs)
        db_session.add(binding)
        await db_session.commit()
        return binding

    return _create_group_role_binding


# ============================================================================
# High-Level Service-Based Factories (for API/Integration Tests)
# ============================================================================
# These factories use the service layer to create entities with role assignments.
# Use these in API and integration tests to test through the service layer.


@pytest.fixture
def group_with_role_factory(
    group_factory: Callable[..., Awaitable[Group]],
    authorization_service: AuthorizationService,
    db_session: AsyncSession,
) -> Callable[..., Awaitable[Group]]:
    """Factory for creating groups with role assignments (uses service layer).

    This factory uses AuthorizationService to assign roles, ensuring proper
    business logic and validation. Use in API and integration tests.

    Usage:
        # Create a new group with a role
        group = await group_with_role_factory(
            user_id=owner_user.id,
            role=GroupRole.OWNER,
            name="My Group"
        )

        # Add another role to existing group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group.id
        )
    """

    async def _create_group_with_role(
        user_id: int, role: GroupRole, name: str | None = None, group_id: int | None = None, **kwargs: Any
    ) -> Group:
        """
        Create a group and assign a role, or assign a role to an existing group.

        Args:
            user_id: The user ID to assign the role to
            role: The role to assign
            name: Group name (only used if group_id is None)
            group_id: Existing group ID (if None, creates a new group)
            **kwargs: Additional arguments passed to group_factory
        """
        if group_id is None:
            # Create new group
            group = await group_factory(name=name or "Test Group", **kwargs)
            group_id = group.id
        else:
            # Use existing group - fetch it to return
            from app.repositories.group import GroupRepository

            group_repo = GroupRepository(db_session)
            group = await group_repo.get_group_by_id(group_id)
            if not group:
                raise ValueError(f"Group {group_id} not found")

        await authorization_service.assign_group_role(user_id, group_id, role)
        await db_session.commit()
        return group

    return _create_group_with_role


@pytest.fixture
def user_with_system_role_factory(
    user_factory: Callable[..., Awaitable[User]],
    authorization_service: AuthorizationService,
    db_session: AsyncSession,
) -> Callable[..., Awaitable[User]]:
    """Factory for creating users with system role assignments (uses service layer).

    This factory uses AuthorizationService to assign roles, ensuring proper
    business logic and validation. Use in API and integration tests.

    Usage:
        admin_user = await user_with_system_role_factory(
            role=SystemRole.ADMIN,
            email="admin@example.com",
            name="Admin User"
        )
    """

    async def _create_user_with_role(
        role: SystemRole, email: str = "test@example.com", name: str = "Test User", **kwargs: Any
    ) -> User:
        """
        Create a user and assign a system role.

        Args:
            role: The system role to assign
            email: User email address
            name: User name
            **kwargs: Additional arguments passed to user_factory
        """
        user = await user_factory(email=email, name=name, **kwargs)
        await authorization_service.assign_system_role(user.id, role)
        await db_session.commit()
        return user

    return _create_user_with_role
