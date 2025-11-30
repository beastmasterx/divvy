"""
Authorization: Role-Based Access Control (RBAC) 🛡️

This module provides dependency factory functions for enforcing Role-Based Access
Control (RBAC) rules on both system-wide and group-specific resources.

---
DESIGN:
The factory pattern (`requires_...`) creates dynamic FastAPI dependencies
that check if the current authenticated user possesses any of the required roles
for the requested resource.

FAILURE:
If the user's role does not satisfy the requirements, a 403 ForbiddenError is raised.
"""

from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated

from fastapi import Depends, Path

from app.api.dependencies.authn import get_current_user
from app.api.dependencies.services import get_authorization_service, get_period_service
from app.core.i18n import _
from app.exceptions import ForbiddenError, NotFoundError
from app.models import GroupRole, SystemRole
from app.schemas import UserResponse
from app.services import AuthorizationService, PeriodService

# Type alias for the acceptable role types (Enum or str)
RoleType = SystemRole | GroupRole | str


def _normalize_roles(roles: Sequence[RoleType]) -> list[str]:
    """
    Converts a sequence of Role Enums (SystemRole/GroupRole) or strings into
    a list of standardized role string values for authorization checks.

    Args:
        roles: Sequence of role enums or strings to normalize

    Returns:
        List of normalized role string values
    """
    normalized: list[str] = []
    for role in roles:
        # Use isinstance() for robust type checking against the Enum types
        if isinstance(role, (SystemRole, GroupRole)):
            # Enums must provide a .value attribute
            normalized.append(role.value)
        else:
            # Assume it's a string, or convert non-Enum/non-string to string
            normalized.append(str(role))
    return normalized


def _get_display_role_name(role_value: str) -> str:
    """
    Returns the translated, display-friendly name for an internal role value.

    This prepares the string (e.g., "system:admin" -> "System Admin") and wraps
    it in the translation marker (`_()`) for i18n tooling.

    Args:
        role_value: The internal role value string

    Returns:
        Translated, display-friendly role name
    """
    # 1. Clean the role value: remove prefix (if exists) and replace underscores
    clean_name = role_value.split(":")[-1].replace("_", " ")

    # 2. Translate the title-cased, cleaned string
    # E.g., translates "System Admin"
    return _(clean_name.title())


def requires_system_role(*roles: RoleType) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific system role.

    This check enforces authorization across the entire application context.

    Args:
        *roles: A variable number of required SystemRole objects or string values.
                Access is granted if the user possesses ANY of the provided roles.

    Returns:
        A callable FastAPI dependency that raises ForbiddenError on failure.
    """
    required_role_values = _normalize_roles(roles)

    # Get the list of translated display names for the error message
    display_names = [_get_display_role_name(r) for r in required_role_values]
    role_list_display = ", ".join(display_names)

    async def _verify_system_role(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:

        user_role = await authorization_service.get_system_role(current_user.id)

        # Check if the user's role is None (no role assigned) OR is not in the required list
        if user_role is None or user_role not in required_role_values:
            raise ForbiddenError(
                _("Access denied. This operation requires one of the following roles: %(roles)s")
                % {"roles": role_list_display}
            )
        return current_user

    return _verify_system_role


def requires_group_role(*roles: RoleType) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific group role
    for the resource identified by 'group_id' in the path.

    Args:
        *roles: A variable number of required GroupRole objects or string values.
                Access is granted if the user possesses ANY of the provided roles
                within the context of the requested group.

    Returns:
        A callable FastAPI dependency that raises ForbiddenError on failure.
    """
    required_role_values = _normalize_roles(roles)

    # Get the list of translated display names for the error message
    display_names = [_get_display_role_name(r) for r in required_role_values]
    role_list_display = ", ".join(display_names)

    async def _verify_group_role(
        # The Path(...) dependency ensures group_id is provided in the route
        group_id: Annotated[int, Path(description=_("The unique ID of the target group."))],
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:

        # Check if the user has a role in the context of the provided group_id
        user_role = await authorization_service.get_group_role(current_user.id, group_id)

        if user_role is None or user_role not in required_role_values:
            # Use the translated display names in the Forbidden error
            raise ForbiddenError(
                _("Access denied. You do not have the required role (%(roles)s) for this resource.")
                % {"roles": role_list_display}
            )
        return current_user

    return _verify_group_role


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
    required_role_values = _normalize_roles(roles)
    display_names = [_get_display_role_name(r) for r in required_role_values]
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
