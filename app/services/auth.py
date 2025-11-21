"""
Authentication service for password hashing, JWT token management, and user authentication.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.api.schemas import PasswordResetRequest, TokenResponse, UserRequest
from app.core.config import (
    JWT_ALGORITHM,
    get_jwt_access_token_expire_seconds,
    get_jwt_refresh_token_expire_days,
    get_jwt_secret_key,
)
from app.core.i18n import _
from app.exceptions import NotFoundError, UnauthorizedError
from app.models import RefreshToken, User
from app.repositories import RefreshTokenRepository
from app.services.user import UserService


class AuthService:
    """Service layer for authentication-related operations."""

    _hashing_context: CryptContext | None = None

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

        # Hash password
        hashed_pwd = self._hash(password)

        # Create user using schema
        user_request = UserRequest(
            email=email,
            name=name,
            password=hashed_pwd,
            is_active=True,
            avatar=None,
        )
        user = self._user_service.create_user(user_request)

        # Generate tokens
        access_token = self._create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = self._generate_refresh_token(user_id=user.id, device_info=device_info)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._get_token_expires_in(access_token),
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
        user = self._user_service.get_user_by_email(email)

        if not user or not user.password or not self._verify(password, user.password) or not user.is_active:
            raise UnauthorizedError("Invalid email or password or user is inactive")

        access_token = self._create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = self._generate_refresh_token(user_id=user.id, device_info=device_info)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._get_token_expires_in(access_token),
        )

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> User:
        """
        Change a user's password with old password verification.

        Args:
            user_id: ID of the user whose password to change
            old_password: Current password for verification
            new_password: New password

        Returns:
            Updated User model

        Raises:
            NotFoundError: If user not found
            UnauthorizedError: If old password is incorrect
        """

        user = self._user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Verify old password
        if not user.password:
            raise UnauthorizedError("User has no password set")

        if not self._verify(old_password, user.password):
            raise UnauthorizedError("Current password is incorrect")

        new_password_hash = self._hash(new_password)
        return self._user_service.reset_password(user_id, new_password_hash)

    def reset_password(self, user_id: int, request: PasswordResetRequest) -> User:
        """
        Reset a user's password (admin operation, no old password required).

        Args:
            user_id: ID of the user whose password to reset
            new_password: New password

        Returns:
            Updated User model

        Raises:
            NotFoundError: If user not found
        """
        user = self._user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        new_password_hash = self._hash(request.new_password)
        return self._user_service.reset_password(user_id, new_password_hash)

    def _create_access_token(self, data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """
        Create a JWT access token.

        Args:
            data: Dictionary containing token payload (typically user_id and email)
            expires_delta: Optional custom expiration time. If None, uses default from config.

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(seconds=get_jwt_access_token_expire_seconds())

        to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
        encoded_jwt = jwt.encode(to_encode, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
        return encoded_jwt

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
            payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            raise UnauthorizedError(f"Invalid authentication token: {str(e)}") from e

    def _get_token_expires_in(self, token: str) -> int:
        """
        Extract expiration time in seconds from a JWT token.

        Decodes the token without verification to extract the 'exp' claim,
        then calculates the remaining seconds until expiration.

        Args:
            token: JWT token string to extract expiration from

        Returns:
            Number of seconds until token expiration
            Falls back to config default if extraction fails
        """
        try:
            # Decode without verification to extract exp claim
            payload = jwt.decode(
                token,
                get_jwt_secret_key(),
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},  # Don't verify expiration, just extract
            )
            exp = payload.get("exp")
            if exp:
                now = datetime.now(UTC).timestamp()
                expires_in = int(exp - now)
                # Ensure non-negative value
                return max(0, expires_in)
        except Exception:
            # If extraction fails, fall back to config default
            pass
        return get_jwt_access_token_expire_seconds()

    def _generate_refresh_token(self, user_id: int, device_info: str | None = None) -> str:
        """
        Generate a new refresh token for a user.

        Creates a cryptographically random token, generates both a fast lookup key (SHA256)
        and a secure hash (bcrypt), then stores it in the database.

        Args:
            user_id: ID of the user to generate token for
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            Plain text refresh token (only returned once, immediately after generation)
        """
        # Generate a secure random token
        plain_token = secrets.token_urlsafe(32)

        # Create fast lookup key (SHA256 - deterministic, for O(1) database lookup)
        token_lookup = hashlib.sha256(plain_token.encode()).hexdigest()

        # Create secure hash (bcrypt - salted, for security verification)
        token_hash = self._hash(plain_token)

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(days=get_jwt_refresh_token_expire_days())

        # Store in database
        self._refresh_token_repository.create_refresh_token(
            token_lookup=token_lookup,
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
        )

        # Return plain token (only time it's returned)
        return plain_token

    def _verify_refresh_token(self, token: str) -> RefreshToken | None:
        """
        Verify a refresh token and return the token object if valid.

        Uses a two-step verification process:
        1. Fast O(1) lookup using SHA256 hash (token_lookup)
        2. Secure verification using bcrypt hash (token_hash) for security

        Args:
            token: Plain text refresh token to verify

        Returns:
            RefreshToken object if valid, None otherwise
        """
        # Step 1: Fast O(1) lookup using SHA256 hash
        token_lookup = hashlib.sha256(token.encode()).hexdigest()
        refresh_token = self._refresh_token_repository.get_refresh_token_by_lookup(token_lookup)

        if not refresh_token:
            return None

        # Step 2: Check expiration and revocation status
        now = datetime.now(UTC)
        if refresh_token.is_revoked or refresh_token.expires_at <= now:
            return None

        # Step 3: Secure verification using bcrypt (defense in depth)
        try:
            if not self._verify(token, refresh_token.token_hash):
                # Token lookup matched but bcrypt verification failed (shouldn't happen)
                return None
        except Exception:
            return None

        # Step 4: Update last_used_at
        self._refresh_token_repository.update_last_used(refresh_token.id, datetime.now(UTC))

        return refresh_token

    def revoke_refresh_token(self, token: str) -> None:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token: Plain text refresh token to revoke
        """
        refresh_token = self._verify_refresh_token(token)
        if refresh_token:
            self._refresh_token_repository.revoke_refresh_token(refresh_token.id)

    def revoke_all_user_refresh_tokens(self, user_id: int) -> None:
        """
        Revoke all refresh tokens for a user (logout all devices).

        Args:
            user_id: ID of the user whose tokens should be revoked
        """
        self._refresh_token_repository.revoke_all_user_tokens(user_id)

    def rotate_refresh_token(self, old_token: str) -> TokenResponse:
        """
        Rotate a refresh token: invalidate the old one and create a new one.

        This implements token rotation for security. When a refresh token is used,
        it's invalidated and a new one is issued.

        Args:
            old_token: The refresh token to rotate

        Returns:
            TokenResponse containing new access token and refresh token

        Raises:
            UnauthorizedError: If old token is invalid, expired, revoked, or user is not active
        """
        # Verify the old token
        old_refresh_token: RefreshToken | None = self._verify_refresh_token(old_token)
        if not old_refresh_token:
            raise UnauthorizedError(_("Invalid or expired refresh token"))

        # Check if token was already revoked (possible theft detection)
        if old_refresh_token.is_revoked:
            # Token was already used - possible security issue
            # Optionally: revoke all tokens for this user
            raise UnauthorizedError(_("Invalid or expired refresh token"))

        # Save user_id and device_info before revoking
        user_id: int = old_refresh_token.user_id
        device_info: str | None = old_refresh_token.device_info

        user: User | None = self._user_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError(_("User not found or inactive"))

        # Revoke the old token via repository
        self._refresh_token_repository.revoke_refresh_token(old_refresh_token.id)

        # Generate new token with same device info
        new_refresh_token: str = self._generate_refresh_token(
            user_id=user_id,
            device_info=device_info,
        )

        access_token = self._create_access_token(data={"sub": str(user_id), "email": user.email})
        expires_in = self._get_token_expires_in(access_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )

    @classmethod
    def _get_context(cls) -> CryptContext:
        """Get or create the singleton CryptContext instance."""
        if cls._hashing_context is None:
            cls._hashing_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return cls._hashing_context

    @classmethod
    def _hash(cls, value: str) -> str:
        """
        Hash a value using bcrypt.

        Args:
            value: Plain text value to hash

        Returns:
            Hashed value string (includes salt automatically)
        """
        return cls._get_context().hash(value)

    @classmethod
    def _verify(cls, plain: str, hashed: str) -> bool:
        """
        Verify a plain value against a hashed value.

        Args:
            plain: Plain text value to verify
            hashed: Hashed value to compare against

        Returns:
            True if values match, False otherwise
        """
        return cls._get_context().verify(plain, hashed)
