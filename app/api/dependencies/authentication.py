"""
Authentication dependencies.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies.services import get_authentication_service, get_user_service
from app.db.audit import set_current_user_id
from app.exceptions import UnauthorizedError
from app.schemas import UserResponse
from app.services import AuthenticationService, UserService

_oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_schema)],
    authentication_service: AuthenticationService = Depends(get_authentication_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get current authenticated user from JWT token.

    Extracts JWT token from Authorization header, verifies it, and returns the User object.

    Args:
        token: JWT token
        authentication_service: Authentication service instance
        user_service: User service instance

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid, expired, or user not found/inactive
    """
    try:
        payload = await authentication_service.verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedError("Invalid authentication token")
        user_id = int(user_id_str)
    except (UnauthorizedError, ValueError, KeyError) as e:
        raise UnauthorizedError("Invalid authentication token") from e

    user = await user_service.get_user_by_id(user_id)

    if not user or not user.is_active:
        raise UnauthorizedError("User account not found or inactive")

    # Set user ID in audit context for SQLAlchemy events
    # This allows automatic setting of created_by and updated_by fields
    set_current_user_id(user.id)

    return user
