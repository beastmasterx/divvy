from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_user_service
from app.api.schemas.user import ProfileRequest, UserResponse
from app.models import User
from app.services import UserService

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user's information.

    Returns the user information for the currently authenticated user
    based on the JWT token in the Authorization header.

    Args:
        user: Current authenticated user from dependency

    Returns:
        UserResponse containing user information
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar=user.avatar,
    )


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    request: ProfileRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Update current authenticated user's profile.
    """
    updated_user: User = user_service.update_profile(user.id, request)
    return UserResponse.model_validate(updated_user)
