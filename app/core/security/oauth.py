"""
OAuth-specific security utilities.

This module provides security utilities for OAuth2 authorization flows, including
state token management, CSRF protection, and other OAuth-related security functions.

Currently implements:
    - State token creation and verification: Signed JWT tokens for OAuth state
      parameter management, supporting operation context (login/link), user
      identification, and one-time use tracking via nonce.

Functions:
    create_state_token: Create a signed JWT state token with operation
        context, user identification, and security features.
    verify_state_token: Verify and decode a state token, validating
        signature and expiration. Returns StateTokenPayload.
    is_signed_state_token: Check if a string is a JWT token format.

Types:
    StateTokenPayload: NamedTuple representing decoded state token payload.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, NamedTuple

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.config import (
    get_state_token_algorithm,
    get_state_token_expire_delta,
    get_state_token_secret_key,
)
from app.exceptions import InvalidStateTokenError

from ..datetime import utc_now


class StateTokenPayload(NamedTuple):
    """Decoded OAuth state token payload."""

    operation: Literal["link", "login"]
    nonce: str
    exp: datetime  # Timezone-aware UTC datetime
    iat: datetime  # Timezone-aware UTC datetime
    user_id: int | None = None


def generate_state_token(
    user_id: int,
    operation: Literal["link", "login"] = "link",
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    """
    Generates a cryptographically secure state token containing operation context,
    user identification, and a random nonce for CSRF protection.

    Args:
        operation: Operation type to identify the OAuth flow. Defaults to "link".
        user_id: User ID associated with the operation.
        expires_delta: Token expiration time. If None, uses configured default.
        secret_key: Secret key for signing. If None, uses configured default.
        algorithm: JWT signing algorithm. If None, uses configured default.

    Returns:
        Encoded JWT string containing the state token.
    """

    expires_delta = expires_delta or get_state_token_expire_delta()
    secret_key = secret_key or get_state_token_secret_key()
    algorithm = algorithm or get_state_token_algorithm()

    nonce = secrets.token_urlsafe(16)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "operation": operation,
        "nonce": nonce,
        "iat": utc_now().timestamp(),  # 💡 Use timestamp for IAT/EXP claims
        "exp": (utc_now() + expires_delta).timestamp(),  # 💡 Use timestamp for IAT/EXP claims
    }

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_state_token(
    token: str,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> StateTokenPayload:
    """
    Verify and decode an OAuth state token.

    Args:
        token: JWT state token string to verify.
        secret_key: Secret key for verification. If None, uses configured default.
        algorithm: JWT signing algorithm. If None, uses configured default.

    Returns:
        StateTokenPayload containing decoded token data (operation, nonce, timestamps, user_id).

    Raises:
        InvalidStateTokenError: If the token is invalid, expired, has a bad signature,
            is malformed, or contains an invalid operation type.
    """

    secret_key = secret_key or get_state_token_secret_key()
    algorithm = algorithm or get_state_token_algorithm()

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
        )
    except (JWTError, ExpiredSignatureError, JWTClaimsError) as e:
        raise InvalidStateTokenError(f"State token verification failed: {e.__class__.__name__}") from e
    except Exception as e:
        # Catch non-JWT exceptions (e.g., UnicodeDecodeError) during JOSE decode
        raise InvalidStateTokenError(f"Token decoding failed: {e.__class__.__name__}") from e

    # --- Structural Validation and Conversion ---
    operation = payload.get("operation")
    if operation not in ("link", "login"):
        raise InvalidStateTokenError(f"Invalid operation in state token: {operation}")

    # Use try/except to wrap potential TypeErrors/ValueErrors during payload construction
    try:
        return StateTokenPayload(
            # JWT timestamps (exp, iat) are floats; convert them to datetime objects
            operation=operation,
            nonce=payload.get("nonce", ""),
            exp=datetime.fromtimestamp(payload.get("exp", 0), UTC),
            iat=datetime.fromtimestamp(payload.get("iat", 0), UTC),
            user_id=payload.get("user_id"),
        )
    except (ValueError, TypeError) as e:
        raise InvalidStateTokenError(f"State token payload is structurally invalid: {e.__class__.__name__}") from e


def is_signed_state_token(state: str) -> bool:
    """
    Check if a state string is a signed JWT token.

    Performs a simple format check by verifying the string has the JWT structure
    (three parts separated by dots: header.payload.signature). This is a quick
    heuristic and does not validate the token signature or contents.

    Args:
        state: String to check for JWT token format.

    Returns:
        True if the string appears to be a JWT token (has 3 dot-separated parts),
        False otherwise.
    """
    # JWT tokens have 3 parts separated by dots: header.payload.signature
    parts = state.split(".")
    return len(parts) == 3
