"""
Authorization dependencies for permission checking in routes.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Path

from app.api.dependencies.authentication import get_active_user
from app.api.dependencies.services import get_authorization_service
from app.core.i18n import _
from app.exceptions import ForbiddenError
from app.models import GroupRole, SystemRole
from app.schemas import UserResponse
from app.services import AuthorizationService


def require_system_role(role: str | SystemRole) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific system role.
    """

    async def _check_system_role(
        current_user: Annotated[UserResponse, Depends(get_active_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        role_str = role.value if isinstance(role, SystemRole) else role
        user_role = await authorization_service.get_system_role(current_user.id)
        if user_role is None or user_role != role_str:
            raise ForbiddenError(_("Permission denied: requires role %(role)s") % {"role": role_str})
        return current_user

    return _check_system_role


def require_group_role(role: str | GroupRole) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific group role.
    """

    async def _check_group_role(
        group_id: Annotated[int, Path(...)],
        current_user: Annotated[UserResponse, Depends(get_active_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        role_str = role.value if isinstance(role, GroupRole) else role
        user_role = await authorization_service.get_group_role(current_user.id, group_id)
        if user_role is None or user_role != role_str:
            raise ForbiddenError(_("Permission denied: requires role %(role)s") % {"role": role_str})
        return current_user

    return _check_group_role
