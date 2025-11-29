"""
Authentication service for password hashing, JWT token management, and user authentication.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    AccessTokenResult,
    RefreshTokenResult,
    check_password,
    generate_access_token,
    generate_refresh_token,
    hash_password,
    verify_refresh_token,
)
from app.exceptions import InvalidRefreshTokenError, NotFoundError, UnauthorizedError
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
        access_token, expires_in = await self._generate_access_token(user_id=user.id, email=user.email)
        refresh_token, _ = await self._generate_refresh_token(user_id=user.id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
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
        user = await self.verify_password(email, password)
        if not user:
            raise UnauthorizedError("Invalid email or password or user is inactive")

        return await self.generate_tokens(user.id, device_info)

    async def verify_password(self, email: str, password: str) -> UserResponse | None:
        """
        Verify user credentials and return user if authentication succeeds.

        Performs the following checks in order:
        1. User exists with the given email
        2. User has a password set
        3. User account is active
        4. Provided password matches the stored password hash

        Args:
            email: User's email address
            password: Plain text password to verify

        Returns:
            UserResponse if all checks pass, None otherwise
        """
        user = await self._user_repository.get_user_by_email(email)
        if user is None:
            return None

        if user.password is None:
            return None

        if not user.is_active:
            return None

        if not check_password(password, user.password):
            return None

        return UserResponse.model_validate(user)

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

        access_token, expires_in = generate_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token, _ = await self._generate_refresh_token(user_id=user_id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            refresh_token=refresh_token,
        )

    async def revoke_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token: Plain text refresh token to revoke

        Returns:
            Revoked RefreshToken object if successful, None otherwise
        """
        claims = verify_refresh_token(token)
        jti, _ = self._get_refresh_token_jti_and_user_id(claims)
        return await self._refresh_token_repository.revoke_by_id(jti)

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
        old_refresh_token_claims = verify_refresh_token(token)
        jti, user_id = self._get_refresh_token_jti_and_user_id(old_refresh_token_claims)

        user = await self._user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        old_refresh_token = await self._refresh_token_repository.get_by_id(jti)
        if not old_refresh_token:
            raise UnauthorizedError("Refresh token not found")
        if old_refresh_token.is_revoked:
            raise UnauthorizedError("Refresh token is revoked")

        await self._refresh_token_repository.revoke_by_id(jti)
        return await self.generate_tokens(old_refresh_token.user_id, old_refresh_token.device_info)

    def _get_refresh_token_jti_and_user_id(self, claims: dict[str, Any]) -> tuple[str, int]:
        """
        Get the JWT ID and user ID from a refresh token claims.

        Args:
            token: JWT token string to get JWT ID from
        """
        jti = claims.get("jti")
        if jti is None:
            raise InvalidRefreshTokenError("Refresh token is missing the required 'jti' claim.")

        user_id = claims.get("sub")
        if user_id is None:
            raise InvalidRefreshTokenError("Refresh token is missing the required 'sub' claim.")

        return jti, int(user_id)

    async def _generate_access_token(self, user_id: int, email: str) -> AccessTokenResult:
        """
        Generate an access token for an existing user.

        Args:
            user_id: ID of the user to generate an access token for
            email: User's email address

        Returns:
            AccessTokenResult: Contains the access token and the expiration time in seconds
        """
        result = generate_access_token(data={"sub": str(user_id), "email": email})
        return AccessTokenResult(token=result.token, expires_in=result.expires_in)

    async def _generate_refresh_token(self, user_id: int, device_info: str | None = None) -> RefreshTokenResult:
        """
        Generate a refresh token for an existing user.

        Args:
            user_id: ID of the user to generate a refresh token for
            device_info: Optional device information (e.g., User-Agent string)
        """
        result = generate_refresh_token(data={"sub": str(user_id)})
        await self._refresh_token_repository.create(id=result.jti, user_id=user_id, device_info=device_info)
        return result
