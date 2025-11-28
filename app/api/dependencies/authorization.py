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


def requires_system_role(*roles: str | SystemRole) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific system role.
    """

    async def _check_system_role(
        current_user: Annotated[UserResponse, Depends(get_active_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        role_values = [role.value if isinstance(role, SystemRole) else role for role in roles]
        user_role = await authorization_service.get_system_role(current_user.id)
        if user_role is None or user_role not in role_values:
            raise ForbiddenError(_("Permission denied: requires role %(role)s") % {"role": ", ".join(role_values)})
        return current_user

    return _check_system_role


def requires_group_role(*roles: str | GroupRole) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific group role.
    """

    async def _check_group_role(
        group_id: Annotated[int, Path(...)],
        current_user: Annotated[UserResponse, Depends(get_active_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        role_values = [role.value if isinstance(role, GroupRole) else role for role in roles]
        user_role = await authorization_service.get_group_role(current_user.id, group_id)
        if user_role is None or user_role not in role_values:
            raise ForbiddenError(_("Permission denied: requires role %(role)s") % {"role": ", ".join(role_values)})
        return current_user

    return _check_group_role
