"""
Unit tests for AuthenticationService.
"""

from collections.abc import Awaitable, Callable
from datetime import timedelta

import pytest

from app.core.security import generate_access_token, hash_password
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models import User
from app.schemas.user import PasswordResetRequest
from app.services import AuthenticationService, UserService


@pytest.mark.unit
class TestAuthenticationService:
    """Test suite for AuthenticationService."""

    async def test_register_new_user(
        self, authentication_service: AuthenticationService, user_service: UserService
    ) -> None:
        """Test registering a new user."""
        token_response = await authentication_service.register(
            email="newuser@example.com",
            name="New User",
            password="securepass123",
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0

        # Verify user was created
        user = await user_service.get_user_by_email("newuser@example.com")

        assert user is not None
        assert user.name == "New User"
        assert user.is_active is True

    async def test_register_duplicate_email_raises_error(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test that registering with duplicate email raises ConflictError."""
        # Create existing user
        user = await user_factory(email="existing@example.com", name="Existing User")

        with pytest.raises(ConflictError):
            await authentication_service.register(
                email=user.email,
                name="New User",
                password="pass12345",
            )

    async def test_authenticate_valid_credentials(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test authenticating with valid credentials."""
        # Create user with hashed password
        password = "securepass123"
        await user_factory(email="user@example.com", name="Test User", password=hash_password(password), is_active=True)

        token_response = await authentication_service.authenticate(
            email="user@example.com",
            password=password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0

    async def test_authenticate_invalid_email(self, authentication_service: AuthenticationService) -> None:
        """Test authenticating with invalid email raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email="nonexistent@example.com",
                password="pass12345",
            )

    async def test_authenticate_invalid_password(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test authenticating with invalid password raises UnauthorizedError."""
        password = "securepass123"

        user = await user_factory(
            email="user@example.com", name="Test User", password=hash_password(password), is_active=True
        )

        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email=user.email,
                password="wrongpassword",
            )

    async def test_authenticate_inactive_user(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test authenticating inactive user raises UnauthorizedError."""
        password = "securepass123"

        user = await user_factory(
            email="user@example.com",
            name="Test User",
            password=hash_password(password),
            is_active=False,  # Inactive user
        )

        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email=user.email,
                password=password,
            )

    async def test_change_password_valid(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test changing password with valid old password."""
        old_password = "oldpass123"
        new_password = "newpass456"

        user = await user_factory(
            email="user@example.com", name="Test User", password=hash_password(old_password), is_active=True
        )

        updated_user = await authentication_service.change_password(
            user_id=user.id,
            old_password=old_password,
            new_password=new_password,
        )

        assert updated_user.id == user.id
        with pytest.raises(UnauthorizedError):
            await authentication_service.authenticate(
                email=user.email,
                password=old_password,
            )

        token_response = await authentication_service.authenticate(
            email=user.email,
            password=new_password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

    async def test_change_password_invalid_old_password(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test changing password with invalid old password raises UnauthorizedError."""
        old_password = "oldpass123"

        user = await user_factory(
            email="user@example.com", name="Test User", password=hash_password(old_password), is_active=True
        )

        with pytest.raises(UnauthorizedError):
            await authentication_service.change_password(
                user_id=user.id,
                old_password="wrongpassword",
                new_password="newpass456",
            )

    async def test_change_password_user_not_found(self, authentication_service: AuthenticationService) -> None:
        """Test changing password for non-existent user raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await authentication_service.change_password(
                user_id=99999,
                old_password="oldpass12",
                new_password="newpass12",
            )

    async def test_reset_password(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test resetting password (admin operation)."""
        old_password = "oldpass123"
        new_password = "newpass456"

        user = await user_factory(
            email="user@example.com", name="Test User", password=hash_password(old_password), is_active=True
        )

        request = PasswordResetRequest(new_password=new_password)
        updated_user = await authentication_service.reset_password(user_id=user.id, request=request)

        assert updated_user.id == user.id

        token_response = await authentication_service.authenticate(
            email=user.email,
            password=new_password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

    async def test_reset_password_user_not_found(self, authentication_service: AuthenticationService) -> None:
        """Test resetting password for non-existent user raises NotFoundError."""
        request = PasswordResetRequest(new_password="newpassword")
        with pytest.raises(NotFoundError):
            await authentication_service.reset_password(user_id=99999, request=request)

    async def test_verify_token_valid(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test verifying a valid JWT token."""
        password = "password"
        user = await user_factory(email="user@example.com", name="Test User", password=hash_password(password))

        # Create a token
        token = (await authentication_service.authenticate(email=user.email, password=password)).access_token

        # Verify it
        payload = await authentication_service.verify_token(token)

        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert "exp" in payload
        assert "iat" in payload

    async def test_verify_token_invalid(self, authentication_service: AuthenticationService) -> None:
        """Test verifying an invalid JWT token raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await authentication_service.verify_token("invalid.token.here")

    async def test_verify_token_expired(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test verifying an expired token raises UnauthorizedError."""
        password = "password"
        user = await user_factory(email="user@example.com", name="Test User", password=hash_password(password))

        token = generate_access_token(
            data={"sub": str(user.id), "email": user.email}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(UnauthorizedError):
            await authentication_service.verify_token(token)

    async def test_generate_refresh_token(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test generating a refresh token."""
        password = "password"
        user = await user_factory(email="user@example.com", name="Test User", password=hash_password(password))

        refresh_token = (await authentication_service.authenticate(email=user.email, password=password)).refresh_token

        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

    async def test_revoke_refresh_token(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test revoking a refresh token."""
        password = "password"
        user = await user_factory(email="user@example.com", name="Test User", password=hash_password(password))

        # Generate a token
        refresh_token = (await authentication_service.authenticate(email=user.email, password=password)).refresh_token

        # Revoke it
        revoked_token = await authentication_service.revoke_refresh_token(refresh_token)

        assert revoked_token is not None
        assert revoked_token.is_revoked is True
        with pytest.raises(UnauthorizedError):
            await authentication_service.rotate_refresh_token(refresh_token)

    async def test_rotate_refresh_token(
        self, authentication_service: AuthenticationService, user_factory: Callable[..., Awaitable[User]]
    ) -> None:
        """Test rotating a refresh token."""
        password = "password"
        user = await user_factory(
            email="user@example.com", name="Test User", password=hash_password(password), is_active=True
        )

        # Generate initial token
        old_token: str = (await authentication_service.authenticate(email=user.email, password=password)).refresh_token

        # Rotate it
        token_response = await authentication_service.rotate_refresh_token(old_token)

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.refresh_token != old_token  # New token should be different

        # Verify old token is revoked
        with pytest.raises(UnauthorizedError):
            await authentication_service.rotate_refresh_token(old_token)

    async def test_rotate_refresh_token_invalid_token(self, authentication_service: AuthenticationService) -> None:
        """Test rotating an invalid refresh token raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await authentication_service.rotate_refresh_token("invalid_token")
