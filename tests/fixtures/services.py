"""
Service instance fixtures for testing.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import AuthorizationService, PeriodService, UserService


@pytest.fixture
def user_service(db_session: AsyncSession) -> UserService:
    """Create a UserService instance for testing."""
    return UserService(db_session)


@pytest.fixture
def authorization_service(db_session: AsyncSession) -> AuthorizationService:
    """Create an AuthorizationService instance for testing."""
    return AuthorizationService(db_session)


@pytest.fixture
def period_service(db_session: AsyncSession) -> PeriodService:
    """Create a PeriodService instance for testing."""
    return PeriodService(db_session)
