"""
Authentication: Token Handlers (Phase 1: Token Verification) 🔐

This module contains the factory for the synchronous FastAPI dependency that
decodes and verifies the JWT access token. It is the first stage of the
authentication process.

---
KEY ARCHITECTURE:
- The module uses a **synchronous factory function** (`def get_claims_payload`)
  which returns a **synchronous dependency function** (`def _get_claims_payload`).
  This structure allows passing dynamic configuration (`options`) while keeping the
  CPU-bound verification logic off the main event loop via a threadpool.
- It relies on the `app.core.security.verify_access_token` function for the
  cryptographic checks (signature, expiration, etc.).

FAILURE:
- Token verification failures (invalid signature, expired, or malformed)
  result in a **401 Unauthorized** error.

PUBLIC API:
- get_claims_payload: Factory for the core claims provider dependency.
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.i18n import _
from app.core.security import validate_access_token
from app.exceptions import UnauthorizedError

# The OAuth2PasswordBearer instance
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_claims_payload(
    options: dict[str, Any] | None = None,
) -> Callable[[Annotated[str, Depends]], dict[str, Any]]:
    """
    🔑 AUTHENTICATION PROVIDER FACTORY: Creates a SYNCHRONOUS dependency that decodes
    and verifies the JWT, allowing optional override of verification settings.

    Args:
        options: Optional dictionary of verification options (e.g., {"verify_exp": False}).

    Returns:
        A callable dependency function that returns the token claims payload.

    Raises:
        UnauthorizedError (401): If the token is invalid, expired, or malformed.
    """

    def _get_claims_payload(token: Annotated[str, Depends(_oauth2_scheme)]):
        """
        Synchronous dependency for token claims. Runs in FastAPI's internal threadpool.
        """
        try:
            return validate_access_token(token, options)
        except (JWTError, ValueError) as e:
            raise UnauthorizedError(_("Invalid authentication token")) from e

    return _get_claims_payload
