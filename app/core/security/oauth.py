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


def create_state_token(
    operation: str,
    user_id: int | None = None,
    expires_delta: timedelta = get_state_token_expire_delta(),
    secret_key: str = get_state_token_secret_key(),
    algorithm: str = get_state_token_algorithm(),
) -> str:
    """
    Create a signed JWT state token for OAuth flow.
    """
    if operation == "link" and user_id is None:
        raise ValueError("user_id is required for 'link' operation")

    nonce = secrets.token_urlsafe(16)

    payload: dict[str, Any] = {
        "operation": operation,
        "nonce": nonce,
        "iat": utc_now().timestamp(),  # 💡 Use timestamp for IAT/EXP claims
        "exp": (utc_now() + expires_delta).timestamp(),  # 💡 Use timestamp for IAT/EXP claims
    }

    if user_id is not None:
        payload["user_id"] = user_id

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_state_token(
    token: str,
    secret_key: str = get_state_token_secret_key(),
    algorithm: str = get_state_token_algorithm(),
) -> StateTokenPayload:
    """
    Verify and decode an OAuth state token.

    Raises:
        InvalidStateTokenError: If the token is invalid (expired, bad signature, malformed).
    """
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
    """
    # JWT tokens have 3 parts separated by dots: header.payload.signature
    parts = state.split(".")
    return len(parts) == 3
