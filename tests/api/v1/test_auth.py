"""
API tests for Authentication endpoints.
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.identity_providers.registry import IdentityProviderRegistry
from app.core.security.password import hash_password
from app.models import IdentityProviderName, User


@pytest.mark.api
class TestAuthAPI:
    """Test suite for Authentication API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_identity_providers(self) -> Iterator[None]:
        """Register mock identity providers for API tests and ensure cleanup."""
        # Clear registry first for test isolation
        IdentityProviderRegistry.clear()

        # Register mock Microsoft provider for OAuth tests
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value

        def _get_authorization_url(state: str | None = None) -> str:
            """Mock get_authorization_url that includes state if provided."""
            url = "https://login.microsoftonline.com/test/oauth2/v2.0/authorize?client_id=test"
            if state:
                url += f"&state={state}"
            return url

        mock_provider.get_authorization_url = MagicMock(side_effect=_get_authorization_url)
        IdentityProviderRegistry.register(mock_provider)

        yield

        # Cleanup: clear registry after test
        IdentityProviderRegistry.clear()

    # ============================================================================
    # POST /auth/register - Register new user
    # ============================================================================

    async def test_register_success(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test successful user registration."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "name": "New User",
                "password": "securepass123",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    async def test_register_duplicate_email(
        self,
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test registration with duplicate email fails."""
        # Create existing user
        await user_factory(email="existing@example.com", name="Existing User")

        response = await unauthenticated_async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "existing@example.com",
                "name": "New User",
                "password": "securepass123",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_register_validation_error(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test registration with invalid data fails."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "name": "",
                "password": "short",
            },
            follow_redirects=True,
        )

        # FastAPI returns 422 for Pydantic validation errors
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # ============================================================================
    # POST /auth/token - Get access token (password grant)
    # ============================================================================

    async def test_token_password_grant_success(
        self,
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful password grant authentication."""
        password = "securepass123"
        await user_factory(
            email="user@example.com",
            name="Test User",
            password=hash_password(password),
            is_active=True,
        )

        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": "user@example.com",
                "password": password,
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    async def test_token_password_grant_invalid_credentials(
        self,
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test password grant with invalid credentials fails."""
        password = "securepass123"
        await user_factory(
            email="user@example.com",
            name="Test User",
            password=hash_password(password),
            is_active=True,
        )

        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": "user@example.com",
                "password": "wrongpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_password_grant_missing_credentials(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test password grant with missing credentials fails."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_token_refresh_grant_success(
        self,
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful refresh token grant."""
        email = "user@example.com"
        password = "securepass123"
        await user_factory(
            email=email,
            name="Test User",
            password=hash_password(password),
            is_active=True,
        )

        # First get tokens via HTTP endpoint (ensures proper session management)
        initial_response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": email,
                "password": password,
            },
            follow_redirects=True,
        )

        assert initial_response.status_code == status.HTTP_200_OK
        initial_data = initial_response.json()
        refresh_token = initial_data["refresh_token"]
        initial_access_token = initial_data["access_token"]

        # Then refresh using the refresh token
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != initial_access_token  # New token

    async def test_token_refresh_grant_invalid_token(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test refresh grant with invalid token fails."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": "invalid-token",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_invalid_grant_type(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test token endpoint with invalid grant type fails."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "invalid_grant",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ============================================================================
    # POST /auth/revoke - Revoke refresh token
    # ============================================================================

    async def test_revoke_token_success(
        self,
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful token revocation."""
        password = "securepass123"
        await user_factory(
            email="user@example.com",
            name="Test User",
            password=hash_password(password),
            is_active=True,
        )

        # Get tokens via HTTP endpoint (ensures proper session management)
        token_response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": "user@example.com",
                "password": password,
            },
            follow_redirects=True,
        )

        assert token_response.status_code == status.HTTP_200_OK
        token_data = token_response.json()
        refresh_token = token_data["refresh_token"]

        # Revoke refresh token
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/revoke",
            data={
                "token": refresh_token,
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify token is revoked (refresh should fail)
        refresh_response = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            follow_redirects=True,
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_revoke_token_invalid(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test revoking invalid token."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/revoke",
            data={
                "token": "invalid-token",
            },
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ============================================================================
    # POST /auth/logout-all - Logout from all devices
    # ============================================================================

    async def test_logout_all_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test logout-all requires authentication."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/logout-all",
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_logout_all_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        unauthenticated_async_client: AsyncClient,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful logout from all devices."""
        password = "securepass123"
        user = await user_factory(
            email="user@example.com",
            name="Test User",
            password=hash_password(password),
            is_active=True,
        )

        # Create multiple refresh tokens via HTTP endpoints (simulating different devices)
        token_response1 = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": "user@example.com",
                "password": password,
            },
            headers={"User-Agent": "device1"},
            follow_redirects=True,
        )

        token_response2 = await unauthenticated_async_client.post(
            "/api/v1/auth/token",
            data={
                "grant_type": "password",
                "username": "user@example.com",
                "password": password,
            },
            headers={"User-Agent": "device2"},
            follow_redirects=True,
        )

        assert token_response1.status_code == status.HTTP_200_OK
        assert token_response2.status_code == status.HTTP_200_OK

        token_data2 = token_response2.json()
        refresh_token2 = token_data2["refresh_token"]

        async for client in async_client_factory(user):
            response = await client.post(
                "/api/v1/auth/logout-all",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify tokens are revoked
            refresh_response = await unauthenticated_async_client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token2,
                },
                follow_redirects=True,
            )

            assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    # ============================================================================
    # GET /auth/oauth/{provider}/authorize - OAuth authorization
    # ============================================================================

    async def test_oauth_authorize_redirects(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test OAuth authorize redirects to provider."""
        response = await unauthenticated_async_client.get(
            "/api/v1/auth/oauth/microsoft/authorize",
            follow_redirects=False,
        )

        # Should redirect (307) to the provider's authorization URL
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert "Location" in response.headers
        assert response.headers["Location"].startswith("https://")

    # ============================================================================
    # POST /auth/link/{provider}/initiate - Initiate account linking
    # ============================================================================

    async def test_initiate_account_link_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test initiate account link requires authentication."""
        response = await unauthenticated_async_client.post(
            "/api/v1/auth/link/microsoft/initiate",
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_initiate_account_link_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful account link initiation."""
        user = await user_factory(email="user@example.com", name="Test User")

        async for client in async_client_factory(user):
            response = await client.post(
                "/api/v1/auth/link/microsoft/initiate",
                follow_redirects=True,
            )

            # Should return authorization URL
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "authorization_url" in data
            assert data["authorization_url"].startswith("https://")
