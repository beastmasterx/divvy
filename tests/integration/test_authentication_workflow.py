"""
Integration tests for authentication and authorization workflows.

These tests verify that authentication, authorization, and user management
work correctly together.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password
from app.exceptions import ConflictError, UnauthorizedError
from app.models import User
from app.schemas import GroupRequest
from app.services import AuthenticationService, AuthorizationService, GroupService, PeriodService, UserService


@pytest.mark.integration
class TestAuthenticationWorkflow:
    """Integration tests for authentication and user management workflows."""

    async def test_user_registration_and_login_workflow(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        authentication_service: AuthenticationService,
    ):
        """Test complete user registration and authentication flow."""
        # Register new user
        email = "newuser@example.com"
        name = "New User"
        password = "securepass123"

        token_response = await authentication_service.register(
            email=email,
            name=name,
            password=password,
            device_info="test-device",
        )

        # Verify tokens were issued
        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0

        # Verify user was created
        user = await user_service.get_user_by_email(email)
        assert user is not None
        assert user.email == email
        assert user.name == name
        # Password verification is tested via successful login below

        # Login with credentials
        login_response = await authentication_service.authenticate(
            email=email,
            password=password,
            device_info="test-device",
        )

        assert login_response.access_token is not None
        assert login_response.refresh_token is not None
        assert login_response.access_token != token_response.access_token  # New token

    async def test_duplicate_registration_fails(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        authentication_service: AuthenticationService,
    ):
        """Test that registering with duplicate email fails."""
        # Create existing user
        email = "existing@example.com"
        await user_factory(email=email, name="Existing User", password=hash_password("password123"))

        # Try to register with same email
        with pytest.raises(ConflictError):
            await authentication_service.register(
                email=email,
                name="New User",
                password="newpassword123",
                device_info="test-device",
            )

    async def test_invalid_login_fails(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        authentication_service: AuthenticationService,
    ):
        """Test that invalid credentials fail authentication."""
        # Create user
        email = "user@example.com"
        password = "correctpass123"
        await user_factory(email=email, name="User", password=hash_password(password), is_active=True)

        # Try wrong password
        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email=email,
                password="wrongpassword",
                device_info="test-device",
            )

        # Try wrong email
        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email="wrong@example.com",
                password=password,
                device_info="test-device",
            )

    async def test_token_refresh_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        authentication_service: AuthenticationService,
    ):
        """Test refreshing access tokens."""
        # Create user and get initial tokens
        email = "user@example.com"
        password = "securepass123"
        await user_factory(email=email, name="User", password=hash_password(password), is_active=True)

        initial_response = await authentication_service.authenticate(
            email=email,
            password=password,
            device_info="test-device",
        )

        # Refresh token
        refresh_response = await authentication_service.rotate_token(initial_response.refresh_token)

        assert refresh_response.access_token is not None
        assert refresh_response.refresh_token is not None
        assert refresh_response.access_token != initial_response.access_token  # New access token
        assert refresh_response.refresh_token != initial_response.refresh_token  # New refresh token

    async def test_user_profile_update_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        user_service: UserService,
    ):
        """Test updating user profile."""
        # Create user
        user = await user_factory(email="user@example.com", name="Original Name", avatar="old-avatar.jpg")

        # Update profile
        from app.schemas import ProfileRequest

        profile_request = ProfileRequest(
            name="Updated Name",
            email="updated@example.com",
            avatar="new-avatar.jpg",
        )

        updated_user = await user_service.update_profile(user.id, profile_request)

        assert updated_user.name == "Updated Name"
        assert updated_user.email == "updated@example.com"
        assert updated_user.avatar == "new-avatar.jpg"

    async def test_authenticated_user_group_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        authentication_service: AuthenticationService,
    ):
        """Test that authenticated users can create and manage groups."""
        # Register and authenticate user
        email = "user@example.com"
        password = "securepass123"

        await authentication_service.register(
            email=email,
            name="Test User",
            password=password,
            device_info="test-device",
        )

        # Get user
        user_service = UserService(db_session)
        user = await user_service.get_user_by_email(email)
        assert user is not None

        # Create group (simulating authenticated user)
        authorization_service = AuthorizationService(db_session)
        group_service = GroupService(db_session, authorization_service, PeriodService(db_session))

        group_request = GroupRequest(name="My Group")
        group = await group_service.create_group(group_request, user.id)

        # Verify user is owner
        assert await group_service.is_owner(group.id, user.id)
        assert await group_service.is_member(group.id, user.id)

        # Get user's groups
        user_groups = await group_service.get_groups_by_user_id(user.id)
        assert len(user_groups) > 0
        assert any(g.id == group.id for g in user_groups)
