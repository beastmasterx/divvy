"""
Authentication: User Providers (Phase 2: Identity Provisioning & Authorization) 👤

This module contains the core **Identity Provider** dependency that provisions
the final, usable User object for the application. It chains off the claims
verified in `token_handlers` and enforces basic authorization rules.

---
RESPONSIBILITIES:
1. **Chain Authentication:** Depends on `get_claims_payload` to receive a
   verified claims dictionary.
2. **Identity Integrity:** Validates the format of critical claims (e.g., safely
   converting `sub` to an integer, guarding against `ValueError`).
3. **Database Confirmation:** Performs a **database lookup** to confirm the
   user ID still exists and retrieve the user's base status/roles.
4. **Active Status Check (Authorization):** Verifies the retrieved user's
   account is marked as active.

VERB CONVENTION:
- This module uses the **`get_current_`** verb family (e.g., `get_current_user`)
  as its primary role is to **retrieve and provide** the authenticated and authorized subject.

FAILURE:
- Identity provisioning failures (invalid claim format, user not found in DB,
  or inactive account) result in a **401 Unauthorized** error.

PUBLIC API:
- get_current_user: The primary asynchronous dependency that returns the
  validated and active User object.
"""

from typing import Annotated, Any

from fastapi import Depends

from app.api.dependencies.services import get_user_service
from app.core.i18n import _
from app.exceptions import UnauthorizedError
from app.schemas import UserResponse
from app.services import UserService

from .token_handlers import get_claims_payload


async def get_current_user(
    claims: Annotated[dict[str, Any], Depends(get_claims_payload())],
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Retrieves and validates the current active user based on JWT claims.

    This function performs identity integrity checks, database confirmation,
    and verifies the user's active status.

    Args:
        claims: The verified JWT claims payload from the token handler.
        user_service: Dependency for accessing user data.

    Returns:
        The validated and active UserResponse object.

    Raises:
        UnauthorizedError: If the token is invalid (missing claims),
                           the user is not found in the DB,
                           or the user account is inactive.
    """
    user_id_str = claims.get("sub")
    email = claims.get("email")  # Email often used for logging/context but not strictly needed for lookup

    # 1. Identity Integrity: Check for required claims
    if not user_id_str or not email:
        raise UnauthorizedError(_("Invalid authentication token: Missing mandatory claims."))

    # 2. Identity Integrity: Convert subject to required type (guarding against ValueError)
    try:
        # Note: Using str.isnumeric() could check first, but int() conversion is definitive
        user_id = int(user_id_str)
    except (ValueError, TypeError) as e:
        # Catch errors if 'sub' claim isn't convertible to an integer
        raise UnauthorizedError(_("Invalid authentication token: User subject ID is malformed.")) from e

    # 3. Database Confirmation: Check user existence
    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise UnauthorizedError(_("User not found: Account corresponding to token subject does not exist."))

    # 4. Authorization Check: Active status
    if not user.is_active:  # Assuming the User model has an 'is_active' attribute
        raise UnauthorizedError(_("User account is disabled or inactive."))

    # 5. Success: Return the final, validated user object
    return user
