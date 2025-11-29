"""
API test fixtures for FastAPI dependency overrides and test clients.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user
from app.api.routers.v1 import api_router
from app.models import User
from app.schemas import UserResponse

# ============================================================================
# App Fixtures
# ============================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app instance for testing."""
    test_app = FastAPI()
    test_app.include_router(api_router, prefix="/api")
    return test_app


# ============================================================================
# Authentication Override Fixtures
# ============================================================================


@pytest.fixture
async def authenticated_user(
    user_factory: Callable[..., Awaitable[User]],
) -> User:
    """Create a default authenticated user for testing."""
    return await user_factory(
        email="test@example.com",
        name="Test User",
        is_active=True,
    )


@pytest.fixture
def authenticated_user_override(authenticated_user: User) -> Callable[[], Awaitable[UserResponse]]:
    """
    Create a dependency override for get_current_user.

    Returns a function that can be used to override the get_current_user
    dependency in FastAPI app.
    """

    async def _get_current_user_override() -> UserResponse:
        return UserResponse.model_validate(authenticated_user)

    return _get_current_user_override


# ============================================================================
# Test Client Fixtures
# ============================================================================


@pytest.fixture
async def async_client(
    app: FastAPI,
    authenticated_user_override: Callable[[], Awaitable[UserResponse]],
) -> AsyncIterator[AsyncClient]:
    """
    Create an async test client with authentication override.

    Automatically sets up authentication and cleans up after test.
    """
    app.dependency_overrides[get_current_user] = authenticated_user_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    # Clean up dependency overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
async def unauthenticated_client(
    app: FastAPI,
) -> AsyncIterator[AsyncClient]:
    """
    Create an async test client without authentication.

    Use this to test authentication requirements.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    # Ensure no overrides remain
    app.dependency_overrides.clear()
