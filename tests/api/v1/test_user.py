"""
API tests for User endpoints.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models import User
from app.schemas.user import ProfileRequest, UserResponse


@pytest.mark.api
class TestUserAPI:
    """Test suite for User API endpoints."""

    # ============================================================================
    # GET /user/me - Get current user info
    # ============================================================================

    async def test_get_current_user_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test endpoint requires authentication."""
        response = await unauthenticated_async_client.get("/api/v1/user/me", follow_redirects=True)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful current user retrieval."""
        user = await user_factory(
            email="user@example.com",
            name="Test User",
            avatar="https://example.com/avatar.jpg",
        )

        async for client in async_client_factory(user):
            response = await client.get("/api/v1/user/me", follow_redirects=True)

            assert response.status_code == status.HTTP_200_OK
            user_response = UserResponse.model_validate(response.json())
            assert user_response.id == user.id
            assert user_response.email == user.email
            assert user_response.name == user.name
            assert user_response.avatar == user.avatar

    # ============================================================================
    # PUT /user/me - Update user profile
    # ============================================================================

    async def test_update_profile_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test endpoint requires authentication."""
        request = ProfileRequest(name="Updated Name")
        response = await unauthenticated_async_client.put(
            "/api/v1/user/me",
            json=request.model_dump(exclude_none=True),
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_profile_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test successful profile update."""
        user = await user_factory(
            email="user@example.com",
            name="Original Name",
            avatar="https://example.com/old-avatar.jpg",
        )

        request = ProfileRequest(
            name="Updated Name",
            email="updated@example.com",
            avatar="https://example.com/new-avatar.jpg",
        )
        async for client in async_client_factory(user):
            response = await client.put(
                "/api/v1/user/me",
                json=request.model_dump(exclude_none=True),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            user_response = UserResponse.model_validate(response.json())
            assert user_response.name == "Updated Name"
            assert user_response.email == "updated@example.com"
            assert user_response.avatar == "https://example.com/new-avatar.jpg"

    async def test_update_profile_partial(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test partial profile update (only some fields)."""
        user = await user_factory(
            email="user@example.com",
            name="Original Name",
            avatar="https://example.com/avatar.jpg",
        )

        request = ProfileRequest(name="Updated Name Only")
        async for client in async_client_factory(user):
            response = await client.put(
                "/api/v1/user/me",
                json=request.model_dump(exclude_none=True),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            user_response = UserResponse.model_validate(response.json())
            assert user_response.name == "Updated Name Only"
            # Other fields should remain unchanged or be None

    async def test_update_profile_validation_error(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test profile update with invalid data fails."""
        user = await user_factory(email="user@example.com", name="Test User")

        async for client in async_client_factory(user):
            # Note: This will fail Pydantic validation before reaching the endpoint
            # We'll use raw dict to test endpoint validation, or catch ValidationError
            # Using raw dict to test endpoint-level validation
            response = await client.put(
                "/api/v1/user/me",
                json={
                    "email": "invalid-email",
                    "name": "",  # Empty name should fail validation
                },
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
