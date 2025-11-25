"""
Unit tests for AuthService.
"""

from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import PasswordResetRequest
from app.core.security import generate_access_token, hash_password
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.services import AuthService, UserService
from tests.fixtures.factories import create_test_user


@pytest.mark.unit
class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    async def auth_service(self, db_session: AsyncSession) -> AuthService:
        """Create an AuthService instance with dependencies."""
        user_service = UserService(db_session)
        return AuthService(session=db_session, user_service=user_service)

    async def test_register_new_user(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test registering a new user."""
        token_response = await auth_service.register(
            email="newuser@example.com",
            name="New User",
            password="securepass123",
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0

        # Verify user was created
        user_service = UserService(db_session)
        user = await user_service.get_user_by_email("newuser@example.com")
        assert user is not None
        assert user.name == "New User"
        assert user.is_active is True

    async def test_register_duplicate_email_raises_error(
        self, auth_service: AuthService, db_session: AsyncSession
    ) -> None:
        """Test that registering with duplicate email raises ConflictError."""
        # Create existing user
        user = create_test_user(email="existing@example.com", name="Existing User")
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(ConflictError):
            await auth_service.register(
                email="existing@example.com",
                name="New User",
                password="pass12345",
            )

    async def test_authenticate_valid_credentials(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test authenticating with valid credentials."""
        # Create user with hashed password
        password = "securepass123"
        hashed_password = hash_password(password)
        user = create_test_user(email="user@example.com", name="Test User", password=hashed_password, is_active=True)
        db_session.add(user)
        await db_session.commit()

        token_response = await auth_service.authenticate(
            email="user@example.com",
            password=password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in > 0

    async def test_authenticate_invalid_email(self, auth_service: AuthService) -> None:
        """Test authenticating with invalid email raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await auth_service.authenticate(
                email="nonexistent@example.com",
                password="pass12345",
            )

    async def test_authenticate_invalid_password(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test authenticating with invalid password raises UnauthorizedError."""
        password = "securepass123"
        hashed_password = hash_password(password)

        user = create_test_user(email="user@example.com", name="Test User", password=hashed_password, is_active=True)
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(UnauthorizedError):
            await auth_service.authenticate(
                email="user@example.com",
                password="wrongpassword",
            )

    async def test_authenticate_inactive_user(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test authenticating inactive user raises UnauthorizedError."""
        password = "securepass123"
        hashed_password = hash_password(password)

        user = create_test_user(
            email="user@example.com", name="Test User", password=hashed_password, is_active=False  # Inactive user
        )
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(UnauthorizedError):
            await auth_service.authenticate(
                email="user@example.com",
                password=password,
            )

    async def test_change_password_valid(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test changing password with valid old password."""
        old_password = "oldpass123"
        new_password = "newpass456"
        hashed_old_password = hash_password(old_password)

        user = create_test_user(
            email="user@example.com", name="Test User", password=hashed_old_password, is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        updated_user = await auth_service.change_password(
            user_id=user_id,
            old_password=old_password,
            new_password=new_password,
        )

        assert updated_user.id == user_id
        with pytest.raises(UnauthorizedError):
            await auth_service.authenticate(
                email="user@example.com",
                password=old_password,
            )

        token_response = await auth_service.authenticate(
            email="user@example.com",
            password=new_password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

    async def test_change_password_invalid_old_password(
        self, auth_service: AuthService, db_session: AsyncSession
    ) -> None:
        """Test changing password with invalid old password raises UnauthorizedError."""
        old_password = "oldpass123"
        hashed_old_password = hash_password(old_password)

        user = create_test_user(
            email="user@example.com", name="Test User", password=hashed_old_password, is_active=True
        )
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(UnauthorizedError):
            await auth_service.change_password(
                user_id=user.id,
                old_password="wrongpassword",
                new_password="newpass456",
            )

    async def test_change_password_user_not_found(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test changing password for non-existent user raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await auth_service.change_password(
                user_id=99999,
                old_password="oldpass12",
                new_password="newpass12",
            )

    async def test_reset_password(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test resetting password (admin operation)."""
        old_password = "oldpass123"
        new_password = "newpass456"
        hashed_old_password = hash_password(old_password)

        user = create_test_user(
            email="user@example.com", name="Test User", password=hashed_old_password, is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        user_id = user.id

        request = PasswordResetRequest(new_password=new_password)
        updated_user = await auth_service.reset_password(user_id=user_id, request=request)

        assert updated_user.id == user_id

        token_response = await auth_service.authenticate(
            email="user@example.com",
            password=new_password,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

    async def test_reset_password_user_not_found(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test resetting password for non-existent user raises NotFoundError."""
        request = PasswordResetRequest(new_password="newpassword")
        with pytest.raises(NotFoundError):
            await auth_service.reset_password(user_id=99999, request=request)

    async def test_verify_token_valid(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test verifying a valid JWT token."""
        password = "password"
        user = create_test_user(email="user@example.com", name="Test User", password=hash_password(password))
        db_session.add(user)
        await db_session.commit()

        # Create a token
        token = (await auth_service.authenticate(email=user.email, password=password)).access_token

        # Verify it
        payload = await auth_service.verify_token(token)

        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert "exp" in payload
        assert "iat" in payload

    async def test_verify_token_invalid(self, auth_service: AuthService) -> None:
        """Test verifying an invalid JWT token raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await auth_service.verify_token("invalid.token.here")

    async def test_verify_token_expired(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test verifying an expired token raises UnauthorizedError."""
        password = "password"
        user = create_test_user(email="user@example.com", name="Test User", password=hash_password(password))
        db_session.add(user)
        await db_session.commit()

        token = generate_access_token(
            data={"sub": str(user.id), "email": user.email}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(UnauthorizedError):
            await auth_service.verify_token(token)

    async def test_generate_refresh_token(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test generating a refresh token."""
        password = "password"
        user = create_test_user(email="user@example.com", name="Test User", password=hash_password(password))
        db_session.add(user)
        await db_session.commit()

        refresh_token = (await auth_service.authenticate(email=user.email, password=password)).refresh_token

        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

    async def test_revoke_refresh_token(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test revoking a refresh token."""
        password = "password"
        user = create_test_user(email="user@example.com", name="Test User", password=hash_password(password))
        db_session.add(user)
        await db_session.commit()

        # Generate a token
        refresh_token = (await auth_service.authenticate(email=user.email, password=password)).refresh_token

        # Revoke it
        revoked_token = await auth_service.revoke_refresh_token(refresh_token)

        assert revoked_token is not None
        assert revoked_token.is_revoked is True
        with pytest.raises(UnauthorizedError):
            await auth_service.rotate_refresh_token(refresh_token)

    async def test_rotate_refresh_token(self, auth_service: AuthService, db_session: AsyncSession) -> None:
        """Test rotating a refresh token."""
        password = "password"
        user = create_test_user(
            email="user@example.com", name="Test User", password=hash_password(password), is_active=True
        )
        db_session.add(user)
        await db_session.commit()

        # Generate initial token
        old_token: str = (await auth_service.authenticate(email=user.email, password=password)).refresh_token

        # Rotate it
        token_response = await auth_service.rotate_refresh_token(old_token)

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.refresh_token != old_token  # New token should be different

        # Verify old token is revoked
        with pytest.raises(UnauthorizedError):
            await auth_service.rotate_refresh_token(old_token)

    async def test_rotate_refresh_token_invalid_token(self, auth_service: AuthService) -> None:
        """Test rotating an invalid refresh token raises UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            await auth_service.rotate_refresh_token("invalid_token")
