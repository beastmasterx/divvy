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
    """
    Create a FastAPI app instance configured for testing.

    Sets up a test application with the API router included at the `/api` prefix.
    This fixture provides the base application that test clients will use.

    **Note:** This fixture does not include any authentication overrides.
    Use `async_client` or `unauthenticated_async_client` fixtures for ready-to-use
    test clients, or manually configure dependency overrides as needed.
    """
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
    """
    Create a default authenticated user for testing.

    Provides a standard test user with the following attributes:
    - Email: "test@example.com"
    - Name: "Test User"
    - Active status: True

    This fixture is used by `authenticated_user_override` to provide
    authentication for test clients. For tests requiring specific user
    attributes or roles, create a custom user using `user_factory` directly.

    **Dependencies:**
    - `user_factory`: Factory fixture for creating user instances

    **Returns:**
        A User instance configured for testing.
    """
    return await user_factory(
        email="test@example.com",
        name="Test User",
        is_active=True,
    )


@pytest.fixture
def authenticated_user_override(authenticated_user: User) -> Callable[[], Awaitable[UserResponse]]:
    """
    Create a dependency override function for `get_current_user`.

    Returns an async function that can be used to override the `get_current_user`
    dependency in FastAPI's dependency injection system. This allows tests to
    bypass actual authentication and use the `authenticated_user` fixture instead.

    **Usage:**
        ```python
        async def test_custom_override(app: FastAPI, authenticated_user_override):
            app.dependency_overrides[get_current_user] = authenticated_user_override
            # Test code here
            app.dependency_overrides.clear()  # Clean up
        ```

    **Note:** The `async_client` fixture automatically uses this override,
    so manual setup is typically not needed unless testing custom scenarios.

    **Dependencies:**
    - `authenticated_user`: The user instance to use for authentication

    **Returns:**
        An async callable that returns a `UserResponse` for the authenticated user.
    """

    async def _get_current_user_override() -> UserResponse:
        return UserResponse.model_validate(authenticated_user)

    return _get_current_user_override


# ============================================================================
# Test Client Fixtures
# ============================================================================


@pytest.fixture
def async_client_factory(
    app: FastAPI,
) -> Callable[[User], AsyncIterator[AsyncClient]]:
    """
    Factory fixture for creating authenticated async test clients with custom users.

    Returns a factory function that creates an async test client authenticated as
    the specified user. Automatically handles dependency override setup and cleanup.

    **Usage:**
        ```python
        async def test_get_transaction_success(
            async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
            owner_user: User,
            draft_transaction: Transaction,
        ):
            async for client in async_client_factory(owner_user):
                response = await client.get(
                    f"/api/v1/transactions/{draft_transaction.id}",
                    follow_redirects=True,
                )
                assert response.status_code == status.HTTP_200_OK
        ```

    **Note:** This is a fixture factory pattern. The returned function should be
    used with `async for` to properly handle the async context manager lifecycle.

    **Parameters:**
        - `user`: The User instance to authenticate as

    **Returns:**
        An async iterator that yields an AsyncClient authenticated as the specified user.
    """

    async def _create_client(user: User) -> AsyncIterator[AsyncClient]:
        async def _get_user_override() -> UserResponse:
            return UserResponse.model_validate(user)

        app.dependency_overrides[get_current_user] = _get_user_override
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
        finally:
            app.dependency_overrides.clear()

    return _create_client


@pytest.fixture
async def async_client(
    async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
    authenticated_user: User,
) -> AsyncIterator[AsyncClient]:
    """
    Create an async test client with automatic authentication.

    Automatically sets up authentication using the default `authenticated_user` fixture
    and cleans up dependency overrides after the test.

    **Usage:**
        ```python
        async def test_get_groups_success(async_client: AsyncClient):
            response = await async_client.get("/api/v0/groups/")
            assert response.status_code == status.HTTP_199_OK
        ```

    **Note:** For tests requiring specific users or roles, use `async_client_factory`
    fixture factory directly instead of this fixture.

    **Implementation:** This fixture uses `async_client_factory` internally with the
    default `authenticated_user` fixture.
    """
    async for client in async_client_factory(authenticated_user):
        yield client


@pytest.fixture
async def unauthenticated_async_client(
    app: FastAPI,
) -> AsyncIterator[AsyncClient]:
    """
    Create an async test client without authentication.

    Use this to test authentication requirements and public endpoints.

    **Usage:**
        ```python
        async def test_get_groups_requires_authentication(
            unauthenticated_async_client: AsyncClient
        ):
            response = await unauthenticated_async_client.get("/api/v1/groups/")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        ```
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    # Ensure no overrides remain
    app.dependency_overrides.clear()
