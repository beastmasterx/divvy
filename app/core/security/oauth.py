"""
OAuth-specific security utilities.

This module provides security utilities for OAuth2 authorization flows, including
state token management, CSRF protection, and other OAuth-related security functions.

Currently implements:
    - State token creation and verification: Signed JWT tokens for OAuth state
      parameter management, supporting operation context (login/link), user
      identification, and one-time use tracking via nonce.

The module is designed to be extended with additional OAuth security utilities
as needed (e.g., PKCE helpers, token exchange utilities, etc.).

Functions:
    create_state_token: Create a signed JWT state token with operation
        context, user identification, and security features.
    verify_state_token: Verify and decode a state token, validating
        signature and expiration. Returns StateTokenPayload.
    is_signed_state_token: Check if a string is a JWT token format.

Types:
    StateTokenPayload: NamedTuple representing decoded state token payload.

Example:
    >>> from app.core.security.oauth import create_state_token
    >>> token = create_state_token(operation="link", user_id=123)
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, NamedTuple

from jose import JWTError, jwt

from app.config import get_jwt_algorithm, get_jwt_secret_key

from ..datetime import utc_now

_JWT_ALGORITHM = get_jwt_algorithm()


class StateTokenPayload(NamedTuple):
    """Decoded OAuth state token payload.

    Contains operation context, user identification, and security metadata
    extracted from a verified JWT state token.

    Attributes:
        operation: Operation type ("link" for account linking, "login" for authentication)
        nonce: Cryptographically secure nonce for one-time use tracking
        exp: Token expiration timestamp (Unix timestamp as float)
        iat: Token issued at timestamp (Unix timestamp as float)
        user_id: User ID (only present for "link" operation, None for "login")
    """

    operation: Literal["link", "login"]
    nonce: str
    exp: datetime  # Timezone-aware UTC datetime
    iat: datetime  # Timezone-aware UTC datetime
    user_id: int | None = None  # Only present for "link" operation


def create_state_token(
    operation: str,
    user_id: int | None = None,
    expires_in_minutes: int = 10,
) -> str:
    """
    Create a signed JWT state token for OAuth flow.

    The state token encodes operation context (link/login) and user identification
    for authenticated account linking operations. It includes a nonce for
    one-time use tracking and CSRF protection.

    Args:
        operation: Operation type ("link" or "login")
        user_id: User ID (required for "link" operation)
        expires_in_minutes: Token expiration time in minutes (default: 10)

    Returns:
        Signed JWT token string (URL-safe)

    Raises:
        ValueError: If user_id is required but not provided

    Example:
        >>> token = create_state_token(operation="link", user_id=123)
        >>> payload = verify_state_token(token)
        >>> payload.operation
        'link'
        >>> payload.user_id
        123
    """
    if operation == "link" and user_id is None:
        raise ValueError("user_id is required for 'link' operation")

    # Generate cryptographically secure nonce for one-time use tracking
    nonce = secrets.token_urlsafe(16)  # 16 bytes = 128 bits of entropy

    payload: dict[str, Any] = {
        "operation": operation,
        "nonce": nonce,
        "iat": utc_now(),
        "exp": utc_now() + timedelta(minutes=expires_in_minutes),
    }

    if user_id is not None:
        payload["user_id"] = user_id

    return jwt.encode(payload, get_jwt_secret_key(), algorithm=_JWT_ALGORITHM)


def verify_state_token(token: str) -> StateTokenPayload:
    """
    Verify and decode an OAuth state token.

    Verifies the token's signature and expiration, then returns the decoded payload
    as a structured StateTokenPayload object.

    Args:
        token: JWT state token string

    Returns:
        StateTokenPayload containing:
        - operation: "link" or "login"
        - user_id: User ID (if link operation, None for login)
        - nonce: Unique nonce for one-time use tracking
        - exp: Expiration timestamp (Unix timestamp as float)
        - iat: Issued at timestamp (Unix timestamp as float)

    Raises:
        ValueError: If token is invalid, expired, has invalid signature, or
            cannot be decoded/parsed

    Example:
        >>> token = create_state_token(operation="link", user_id=123)
        >>> payload = verify_state_token(token)
        >>> payload.operation
        'link'
        >>> payload.user_id
        123
        >>> payload.nonce
        '...'
    """
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret_key(),
            algorithms=[_JWT_ALGORITHM],
        )
        # Extract fields from JWT payload
        # JWT timestamps (exp, iat) are already floats
        operation = payload.get("operation")
        if operation not in ("link", "login"):
            raise ValueError(f"Invalid operation in state token: {operation}")

        return StateTokenPayload(
            operation=operation,
            nonce=payload.get("nonce", ""),
            exp=datetime.fromtimestamp(payload.get("exp", 0), UTC),
            iat=datetime.fromtimestamp(payload.get("iat", 0), UTC),
            user_id=payload.get("user_id"),
        )
    except JWTError as e:
        raise ValueError(f"Invalid state token: {e}") from e
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Invalid state token payload: {e}") from e


def is_signed_state_token(state: str) -> bool:
    """
    Check if a state string is a signed JWT token.

    JWT tokens have 3 parts separated by dots: header.payload.signature
    This function checks if the state string matches that pattern.

    Args:
        state: State string to check

    Returns:
        True if state appears to be a JWT token, False otherwise

    Example:
        >>> is_signed_state_token("eyJhbGciOiJIUzI1NiJ9.eyJvcGVyYXRpb24iOiJsaW5rIn0.signature")
        True
        >>> is_signed_state_token("550e8400-e29b-41d4-a716-446655440000")
        False
    """
    # JWT tokens have 3 parts separated by dots: header.payload.signature
    parts = state.split(".")
    return len(parts) == 3
