"""
Data fixtures for testing (users, groups, transactions, etc.).
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Group, GroupRole, Period, Transaction, User
from app.services import AuthorizationService
from tests.fixtures.factories import (
    create_test_category,
    create_test_group,
    create_test_period,
    create_test_transaction,
    create_test_user,
)


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
async def owner_user(user_factory: Callable[..., Awaitable[User]]) -> User:
    """Create an owner user for testing."""
    return await user_factory(email="owner@example.com", name="Owner")


@pytest.fixture
async def member_user(user_factory: Callable[..., Awaitable[User]]) -> User:
    """Create a member user for testing."""
    return await user_factory(email="user@example.com", name="User")


@pytest.fixture
def group_factory(db_session: AsyncSession) -> Callable[..., Awaitable[Group]]:
    """Factory fixture for creating multiple groups (transient-like)."""

    async def _create_group(name: str, **kwargs: Any) -> Group:
        group = create_test_group(name=name, **kwargs)
        db_session.add(group)
        await db_session.commit()

        return group

    return _create_group


@pytest.fixture
async def group_with_owner(
    group_factory: Callable[..., Awaitable[Group]], owner_user: User, authorization_service: AuthorizationService
) -> Group:
    """Create a group with owner for testing."""
    group = await group_factory(name="Test Group")
    await authorization_service.assign_group_role(owner_user.id, group.id, GroupRole.OWNER)
    return group


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

    async def _create_transaction(payer_id: int, category_id: int, period_id: int, **kwargs: Any) -> Transaction:
        transaction = create_test_transaction(payer_id=payer_id, category_id=category_id, period_id=period_id, **kwargs)
        db_session.add(transaction)
        await db_session.commit()
        return transaction

    return _create_transaction
