"""
Authentication service for password hashing, JWT token management, and user authentication.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError
from sqlalchemy.orm import Session

from app.api.schemas import PasswordResetRequest, TokenResponse, UserRequest, UserResponse
from app.core.config import (
    get_jwt_refresh_token_expire_days,
)
from app.core.security import (
    check_password,
    create_access_token,
    create_refresh_token,
    get_access_token_expires_in,
    hash_password,
    hash_refresh_token,
    verify_access_token,
)
from app.exceptions import NotFoundError, UnauthorizedError
from app.models import RefreshToken
from app.repositories import RefreshTokenRepository, UserRepository
from app.services.user import UserService


class AuthService:
    """Service layer for authentication-related operations."""

    def __init__(
        self,
        session: Session,
        user_service: UserService,
    ):
        """
        Initialize AuthService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for cross-domain user operations
        """
        self._user_service = user_service
        self._refresh_token_repository = RefreshTokenRepository(session)
        self._user_repository = UserRepository(session)

    def register(
        self,
        email: str,
        name: str,
        password: str,
        device_info: str | None = None,
    ) -> TokenResponse:
        """
        Register a new user and return access token and refresh token.

        Args:
            email: User email address
            name: User name
            password: Password
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            TokenResponse containing access token and refresh token

        Raises:
            ConflictError: If email already exists
        """
        from app.exceptions import ConflictError

        # Check if user exists
        existing_user = self._user_service.get_user_by_email(email)
        if existing_user:
            raise ConflictError("Email already registered")

        # Create user using schema
        user_request = UserRequest(
            email=email,
            name=name,
            password=hash_password(password),
            is_active=True,
            avatar=None,
        )
        user = self._user_service.create_user(user_request)

        # Generate tokens
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = self._generate_refresh_token(user_id=user.id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=get_access_token_expires_in(access_token),
        )

    def authenticate(self, email: str, password: str, device_info: str | None = None) -> TokenResponse:
        """
        Authenticate a user by email and password.

        Args:
            email: User's email address
            password: Plain text password
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            TokenResponse containing access token and refresh token

        Raises:
            UnauthorizedError: If email or password is incorrect or user is inactive
        """
        # Need ORM model for password verification (password not in DTO)
        user_orm = self._user_repository.get_user_by_email(email)

        if (
            not user_orm
            or not user_orm.password
            or not check_password(password, user_orm.password)
            or not user_orm.is_active
        ):
            raise UnauthorizedError("Invalid email or password or user is inactive")

        access_token = create_access_token(data={"sub": str(user_orm.id), "email": user_orm.email})
        refresh_token = self._generate_refresh_token(user_id=user_orm.id, device_info=device_info)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=get_access_token_expires_in(access_token),
        )

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> UserResponse:
        """
        Change a user's password with old password verification.

        Args:
            user_id: ID of the user whose password to change
            old_password: Current password for verification
            new_password: New password

        Returns:
            Updated User response DTO

        Raises:
            NotFoundError: If user not found
            UnauthorizedError: If old password is incorrect
        """
        # Need ORM model for password verification (password not in DTO)
        user_orm = self._user_repository.get_user_by_id(user_id)
        if not user_orm:
            raise NotFoundError(f"User {user_id} not found")

        # Verify old password
        if not user_orm.password:
            raise UnauthorizedError("User has no password set")

        if not check_password(old_password, user_orm.password):
            raise UnauthorizedError("Current password is incorrect")

        return self._user_service.reset_password(user_id, hash_password(new_password))

    def reset_password(self, user_id: int, request: PasswordResetRequest) -> UserResponse:
        """
        Reset a user's password (admin operation, no old password required).

        Args:
            user_id: ID of the user whose password to reset
            request: Password reset request containing new password

        Returns:
            Updated User response DTO

        Raises:
            NotFoundError: If user not found
        """
        user = self._user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        return self._user_service.reset_password(user_id, hash_password(request.new_password))

    def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload as dictionary

        Raises:
            UnauthorizedError: If token is invalid, expired, or malformed
        """
        try:
            return verify_access_token(token)
        except JWTError as e:
            raise UnauthorizedError(f"Invalid authentication token: {str(e)}") from e

    def _generate_refresh_token(self, user_id: int, device_info: str | None = None) -> str:
        """
        Generate a new refresh token for a user.

        Args:
            user_id: ID of the user to generate token for
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            Plain text refresh token (only returned once, immediately after generation)
        """
        token, hash = create_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=get_jwt_refresh_token_expire_days())

        self._refresh_token_repository.create(
            hashed_token=hash,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
        )

        return token

    def revoke_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token: Plain text refresh token to revoke

        Returns:
            Revoked RefreshToken object if successful, None otherwise
        """
        hashed_refresh_token = hash_refresh_token(token)
        return self._refresh_token_repository.revoke(hashed_refresh_token)

    def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        """
        Revoke all refresh tokens for a user (logout all devices).

        Args:
            user_id: ID of the user whose tokens should be revoked
        """
        self._refresh_token_repository.revoke_all(user_id)

    def rotate_refresh_token(self, token: str) -> TokenResponse:
        """
        Rotate a refresh token: invalidate the old one and create a new one.

        This implements token rotation for security. When a refresh token is used,
        it's invalidated and a new one is issued.

        Args:
            token: The refresh token to rotate

        Returns:
            TokenResponse containing new access token and refresh token

        Raises:
            UnauthorizedError: If old token is invalid, expired, revoked, or user is not active
        """
        old_refresh_token = self._verify_refresh_token(token)
        if not old_refresh_token:
            raise UnauthorizedError("Invalid or expired refresh token")

        user = self._user_service.get_user_by_id(old_refresh_token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        self._refresh_token_repository.revoke_by_id(old_refresh_token.id)
        new_refresh_token: str = self._generate_refresh_token(
            user_id=old_refresh_token.user_id,
            device_info=old_refresh_token.device_info,
        )

        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        expires_in = get_access_token_expires_in(access_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    def _verify_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Verify a refresh token is valid, not revoked, and not expired.

        Args:
            token: Plain text refresh token to verify

        Returns:
            Valid RefreshToken object if successful, None otherwise
        """
        hashed_refresh_token = hash_refresh_token(token)
        refresh_token = self._refresh_token_repository.lookup(hashed_refresh_token)
        if not refresh_token or refresh_token.is_revoked:
            return None

        expires_at = refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None

        return refresh_token
