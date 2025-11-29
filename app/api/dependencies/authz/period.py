"""
Policy Enforcement Points (PEPs) for Period resources 🛡️

This module defines FastAPI dependencies that enforce authorization policies
for period-related endpoints by checking group membership through the period's group_id.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Path

from app.api.dependencies.authn import get_current_user
from app.api.dependencies.services import get_authorization_service, get_period_service
from app.core.i18n import _
from app.exceptions import ForbiddenError, NotFoundError
from app.schemas import PeriodCreateRequest, UserResponse
from app.services import AuthorizationService, PeriodService

from .utils import RoleType, get_display_role_name, normalize_roles


def requires_group_role_for_period(*roles: RoleType) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific group role
    for the group associated with the period identified by 'period_id' in the path.

    This function first retrieves the period to extract its group_id, then checks
    if the user has the required role in that group.

    Args:
        *roles: A variable number of required GroupRole objects or string values.
                Access is granted if the user possesses ANY of the provided roles
                within the context of the period's group.

    Returns:
        A callable FastAPI dependency that raises ForbiddenError on failure.
    """
    required_role_values = normalize_roles(roles)
    display_names = [get_display_role_name(r) for r in required_role_values]
    role_list_display = ", ".join(display_names)

    async def _check_user_group_role(
        period_id: Annotated[int, Path(description=_("The unique ID of the target period."))],
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        period_service: PeriodService = Depends(get_period_service),
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        """
        Internal PEP check: Retrieves period details and verifies the user's role within that context.
        """
        period = await period_service.get_period_by_id(period_id)

        if not period:
            raise NotFoundError(_("Period %s not found") % period_id)

        user_role = await authorization_service.get_group_role(current_user.id, period.group_id)

        if user_role is None or user_role not in required_role_values:
            raise ForbiddenError(
                _(
                    "Access denied. You do not have the required role (%(roles)s) for the group associated with this period."
                )
                % {"roles": role_list_display}
            )

        return current_user

    return _check_user_group_role


def requires_group_role_for_period_creation(*roles: RoleType) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific group role
    for a group_id extracted from the request body (PeriodCreateRequest).

    This is useful for POST endpoints where group_id is in the request body
    rather than the path.

    Args:
        *roles: A variable number of required GroupRole objects or string values.
                Access is granted if the user possesses ANY of the provided roles
                within the context of the requested group.

    Returns:
        A callable FastAPI dependency that raises ForbiddenError on failure.
    """
    required_role_values = normalize_roles(roles)
    display_names = [get_display_role_name(r) for r in required_role_values]
    role_list_display = ", ".join(display_names)

    async def _check_user_group_role_for_creation(
        period_request: PeriodCreateRequest,
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        """
        Internal PEP check: Verifies the user's role in the group specified in the period creation request.
        """
        user_role = await authorization_service.get_group_role(current_user.id, period_request.group_id)

        if user_role is None or user_role not in required_role_values:
            raise ForbiddenError(
                _("Access denied. You do not have the required role (%(roles)s) for this group.")
                % {"roles": role_list_display}
            )

        return current_user

    return _check_user_group_role_for_creation
