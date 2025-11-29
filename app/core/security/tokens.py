"""
Core Security Utilities and Token Management 🛡️

This module provides cryptographically secure functions for handling user authentication
tokens (JWT access and JWT refresh tokens). It serves as the single source
of truth for all cryptographic operations within the application.

---
DESIGN PRINCIPLES:
1.  JWT-Centric: All internal tokens (Access, Refresh) are signed JWTs for stateless verification.
2.  Error Encapsulation: All third-party JWT errors are caught and re-raised as
    application-specific exceptions (e.g., InvalidAccessTokenError).
3.  Testability: All JWT functions accept security parameters (secret_key, algorithm)
    as explicit arguments, allowing easy overriding in unit tests.
4.  Security: JWT verification uses a 5-second `leeway` to mitigate clock drift issues.

Key functionalities include:
- Generation and verification of JWT access tokens.
- Generation and verification of JWT refresh tokens.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.config import (
    get_access_token_expire_delta,
    get_core_jwt_secret_key,
    get_jwt_algorithm,
    get_refresh_token_expire_delta,
)
from app.exceptions import InvalidAccessTokenError, InvalidRefreshTokenError

# Define the NamedTuple for the return type


class AccessTokenResult(NamedTuple):
    """
    A container for the results of access token generation.
    token: The fully encoded JWT string.
    expires_in: The lifetime of the token in seconds, required by OAuth 2.0.
    """

    token: str
    expires_in: int


class RefreshTokenResult(NamedTuple):
    """
    A container for the results of refresh token generation.
    jti: The unique JWT ID claim, required for database storage and revocation checks.
    token: The fully encoded JWT string to be sent to the user.
    """

    jti: str
    token: str


# --- ACCESS TOKEN (JWT) UTILITIES ---


def generate_access_token(
    data: dict[str, Any],
    secret_key: str = get_core_jwt_secret_key(),
    algorithm: str = get_jwt_algorithm(),
    expires_delta: timedelta = get_access_token_expire_delta(),
) -> AccessTokenResult:
    """
    Generate a JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire.timestamp(), "iat": datetime.now(UTC).timestamp()})

    # NOTE: No try/except needed here as encoding failures are rare and should crash
    token = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return AccessTokenResult(token=token, expires_in=int(expires_delta.total_seconds()))


def verify_access_token(
    token: str,
    options: dict[str, Any] | None = None,
    secret_key: str = get_core_jwt_secret_key(),
    algorithm: str = get_jwt_algorithm(),
) -> dict[str, Any]:
    """
    Verify and decode a JWT access token.

    Raises:
        InvalidAccessTokenError: If the token is invalid (expired, bad signature, etc.).
    """
    default_options = {"leeway": 5}
    if options:
        default_options.update(options)

    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm], options=default_options)
    except (JWTError, ExpiredSignatureError, JWTClaimsError) as e:
        raise InvalidAccessTokenError(f"Access token verification failed: {e.__class__.__name__}") from e


# --- REFRESH TOKEN (JWT) UTILITIES ---


def generate_refresh_token(
    data: dict[str, Any],
    secret_key: str = get_core_jwt_secret_key(),
    algorithm: str = get_jwt_algorithm(),
    expires_delta: timedelta = get_refresh_token_expire_delta(),
) -> RefreshTokenResult:
    """
    Generate a JWT refresh token, including a unique 'jti' (JWT ID) claim
    for database-based revocation.

    Returns:
        RefreshTokenResult: Contains the JTI (jti) which MUST be saved in the
        database and the encoded token (token) for the user.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta

    # 1. Generate the unique ID (JTI) first
    jti = secrets.token_urlsafe(16)

    # 2. Add expiration, issued-at, and the pre-generated JTI to the payload
    to_encode.update(
        {
            "exp": expire.timestamp(),
            "iat": datetime.now(UTC).timestamp(),
            "jti": jti,
        }
    )

    # 3. Encode the token
    token = jwt.encode(to_encode, secret_key, algorithm=algorithm)

    # 4. Return both the JTI and the token using the NamedTuple
    return RefreshTokenResult(jti=jti, token=token)


def verify_refresh_token(
    token: str,
    options: dict[str, Any] | None = None,
    secret_key: str = get_core_jwt_secret_key(),
    algorithm: str = get_jwt_algorithm(),
) -> dict[str, Any]:
    """
    Verify and decode a JWT refresh token.

    Raises:
        InvalidRefreshTokenError: If the token is invalid (expired, wrong signature, bad claim).
    """
    default_options = {"leeway": 5}
    if options:
        default_options.update(options)

    try:
        claims = jwt.decode(token, secret_key, algorithms=[algorithm], options=default_options)
    except (JWTError, ExpiredSignatureError, JWTClaimsError) as e:
        # Catch various JWT errors and raise our specific application exception
        raise InvalidRefreshTokenError(f"Refresh token verification failed: {e.__class__.__name__}") from e

    return claims
