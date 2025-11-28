"""
Authentication dependencies.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies.services import get_user_service
from app.core.i18n import _
from app.core.security import verify_access_token
from app.db.audit import set_current_user_id
from app.exceptions import ForbiddenError, UnauthorizedError
from app.schemas import UserResponse
from app.services import UserService

_oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_schema)],
) -> UserResponse:
    """
    Get current authenticated user from JWT token.

    Verifies the JWT token from the Authorization header and returns the user information.
    Sets the user ID in the audit context for automatic tracking of created_by/updated_by fields.

    Args:
        token: JWT token extracted from Authorization header

    Returns:
        Authenticated user information

    Raises:
        UnauthorizedError: If token is invalid, expired, or missing required claims
    """
    try:
        payload = verify_access_token(token)
        user_id_str = payload.get("sub")
        name = payload.get("name")
        email = payload.get("email")

        if not user_id_str or not name or not email:
            raise UnauthorizedError("Invalid authentication token")

        avatar = payload.get("avatar")

        user_id = int(user_id_str)
    except (UnauthorizedError, ValueError, KeyError) as e:
        raise UnauthorizedError("Invalid authentication token") from e

    set_current_user_id(user_id)

    return UserResponse(id=user_id, email=email, name=name, avatar=avatar)


async def get_active_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get active user from current authenticated user.

    Returns:
        Active user information

    Raises:
        ForbiddenError: If the user account is inactive
    """

    user = await user_service.get_user_by_id(current_user.id)

    if not user or not user.is_active:
        raise ForbiddenError(_("User account is inactive"))

    return user
