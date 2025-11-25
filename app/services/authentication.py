"""
Authentication service for password hashing, JWT token management, and user authentication.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    get_jwt_refresh_token_expire_days,
)
from app.core.security import (
    check_password,
    generate_access_token,
    generate_refresh_token,
    get_access_token_expires_in,
    hash_password,
    hash_refresh_token,
    verify_access_token,
)
from app.exceptions import NotFoundError, UnauthorizedError
from app.models import RefreshToken
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import PasswordResetRequest, TokenResponse, UserRequest, UserResponse
from app.services.user import UserService


class AuthenticationService:
    """Service layer for authentication-related operations."""

    def __init__(self, session: AsyncSession, user_service: UserService):
        """
        Initialize AuthService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for cross-domain user operations
        """
        self._user_service = user_service
        self._refresh_token_repository = RefreshTokenRepository(session)
        self._user_repository = UserRepository(session)

    async def register(
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
        existing_user = await self._user_service.get_user_by_email(email)
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
        user = await self._user_service.create_user(user_request)

        # Generate tokens
        access_token = generate_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = await self._generate_refresh_token(user_id=user.id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=get_access_token_expires_in(access_token),
            refresh_token=refresh_token,
        )

    async def authenticate(self, email: str, password: str, device_info: str | None = None) -> TokenResponse:
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
        user = await self._user_repository.get_user_by_email(email)

        if not user or not user.password or not check_password(password, user.password) or not user.is_active:
            raise UnauthorizedError("Invalid email or password or user is inactive")

        return await self.generate_tokens(user.id, device_info)

    async def change_password(
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
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Verify old password
        if not user.password:
            raise UnauthorizedError("User has no password set")

        if not check_password(old_password, user.password):
            raise UnauthorizedError("Current password is incorrect")

        return await self._user_service.reset_password(user_id, hash_password(new_password))

    async def reset_password(self, user_id: int, request: PasswordResetRequest) -> UserResponse:
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
        user = await self._user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        return await self._user_service.reset_password(user_id, hash_password(request.new_password))

    async def verify_token(self, token: str) -> dict[str, Any]:
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

    async def _generate_refresh_token(self, user_id: int, device_info: str | None = None) -> str:
        """
        Generate a new refresh token for a user.

        Args:
            user_id: ID of the user to generate token for
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            Plain text refresh token (only returned once, immediately after generation)
        """
        token, hash = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=get_jwt_refresh_token_expire_days())

        await self._refresh_token_repository.create(
            hashed_token=hash,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
        )

        return token

    async def revoke_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token: Plain text refresh token to revoke

        Returns:
            Revoked RefreshToken object if successful, None otherwise
        """
        hashed_refresh_token = hash_refresh_token(token)
        return await self._refresh_token_repository.revoke(hashed_refresh_token)

    async def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        """
        Revoke all refresh tokens for a user (logout all devices).

        Args:
            user_id: ID of the user whose tokens should be revoked
        """
        await self._refresh_token_repository.revoke_all(user_id)

    async def rotate_refresh_token(self, token: str) -> TokenResponse:
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
        old_refresh_token = await self._verify_refresh_token(token)
        if not old_refresh_token:
            raise UnauthorizedError("Invalid or expired refresh token")

        user = await self._user_service.get_user_by_id(old_refresh_token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        await self._refresh_token_repository.revoke_by_id(old_refresh_token.id)
        return await self.generate_tokens(old_refresh_token.user_id, old_refresh_token.device_info)

    async def generate_tokens(self, user_id: int, device_info: str | None = None) -> TokenResponse:
        """
        Generate access and refresh tokens for an existing user.

        This is useful for OAuth flows where a user is already authenticated
        via an external provider and we need to issue tokens.

        Args:
            user_id: ID of the user to generate tokens for
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            TokenResponse containing access token and refresh token

        Raises:
            NotFoundError: If user not found or inactive
        """
        user = await self._user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise NotFoundError("User not found or inactive")

        access_token = generate_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = await self._generate_refresh_token(user_id=user_id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=get_access_token_expires_in(access_token),
            refresh_token=refresh_token,
        )

    async def _verify_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Verify a refresh token is valid, not revoked, and not expired.

        Args:
            token: Plain text refresh token to verify

        Returns:
            Valid RefreshToken object if successful, None otherwise
        """
        hashed_refresh_token = hash_refresh_token(token)
        refresh_token = await self._refresh_token_repository.lookup(hashed_refresh_token)
        if not refresh_token or refresh_token.is_revoked:
            return None

        expires_at = refresh_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None

        return refresh_token
