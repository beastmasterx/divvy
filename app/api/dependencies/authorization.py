"""
Authorization dependencies for permission checking in routes.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Path

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.services import get_authorization_service
from app.core.i18n import _
from app.exceptions import ForbiddenError
from app.models import Permission
from app.schemas import UserResponse
from app.services import AuthorizationService


def require_permission(
    permission: str | Permission,
    group_id: int | None = None,
) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires a specific permission.

    Checks if the current user has the required permission. If group_id is provided,
    checks group-level permissions; otherwise checks system-level permissions.

    Usage:
        @router.get("/groups")
        async def list_groups(
            user: UserResponse = Depends(require_permission(Permission.GROUPS_READ)),
        ):
            ...

        @router.get("/groups/{group_id}/transactions")
        async def list_transactions(
            group_id: int = Path(...),
            user: UserResponse = Depends(require_permission(Permission.TRANSACTIONS_READ, group_id=group_id)),
        ):
            ...

    Args:
        permission: Permission to check (e.g., "groups:read" or Permission.GROUPS_READ)
        group_id: Optional group ID for group-scoped permissions

    Returns:
        Dependency function that checks the permission
    """

    async def _check_permission(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        has_permission = await authorization_service.has_permission(
            user_id=current_user.id,
            permission=permission,
            group_id=group_id,
        )

        if not has_permission:
            permission_str = permission.value if isinstance(permission, Permission) else permission
            raise ForbiddenError(_("Permission denied: %(permission)s") % {"permission": permission_str})

        return current_user

    return _check_permission


def require_any_permission(
    permissions: list[str | Permission],
    group_id: int | None = None,
) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires any of the specified permissions.

    Checks if the current user has at least one of the required permissions.

    Usage:
        @router.get("/groups")
        async def list_groups(
            user: UserResponse = Depends(require_any_permission([
                Permission.GROUPS_READ,
                Permission.GROUPS_WRITE,
            ])),
        ):
            ...

    Args:
        permissions: List of permissions to check
        group_id: Optional group ID for group-scoped permissions

    Returns:
        Dependency function that checks if user has any of the permissions
    """

    async def _check_any_permission(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        has_permission = await authorization_service.has_any_permission(
            user_id=current_user.id,
            permissions=permissions,
            group_id=group_id,
        )

        if not has_permission:
            permission_strs = [p.value if isinstance(p, Permission) else p for p in permissions]
            raise ForbiddenError(
                _("Permission denied: requires any of %(permissions)s") % {"permissions": ", ".join(permission_strs)}
            )

        return current_user

    return _check_any_permission


def require_all_permissions(
    permissions: list[str | Permission],
    group_id: int | None = None,
) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires all of the specified permissions.

    Checks if the current user has all of the required permissions.

    Usage:
        @router.post("/groups")
        async def create_group(
            user: UserResponse = Depends(require_all_permissions([
                Permission.GROUPS_WRITE,
                Permission.GROUPS_MANAGE_MEMBERS,
            ])),
        ):
            ...

    Args:
        permissions: List of permissions to check
        group_id: Optional group ID for group-scoped permissions

    Returns:
        Dependency function that checks if user has all permissions
    """

    async def _check_all_permissions(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        has_permission = await authorization_service.has_all_permissions(
            user_id=current_user.id,
            permissions=permissions,
            group_id=group_id,
        )

        if not has_permission:
            permission_strs = [p.value if isinstance(p, Permission) else p for p in permissions]
            raise ForbiddenError(
                _("Permission denied: requires all of %(permissions)s") % {"permissions": ", ".join(permission_strs)}
            )

        return current_user

    return _check_all_permissions


def require_permission_in_group(
    permission: str | Permission,
) -> Callable[..., Awaitable[UserResponse]]:
    """
    Factory function to create a dependency that requires permission in a specific group.

    The group_id is extracted from the route path parameter.

    Usage:
        @router.get("/groups/{group_id}/transactions")
        async def list_transactions(
            group_id: int = Path(...),
            user: UserResponse = Depends(require_permission_in_group(Permission.TRANSACTIONS_READ)),
        ):
            ...

    Args:
        permission: Permission to check

    Returns:
        Dependency function that checks permission in the group from path parameter
    """

    async def _check_permission_in_group(
        current_user: Annotated[UserResponse, Depends(get_current_user)],
        group_id: int = Path(...),
        authorization_service: AuthorizationService = Depends(get_authorization_service),
    ) -> UserResponse:
        has_permission = await authorization_service.has_permission(
            user_id=current_user.id,
            permission=permission,
            group_id=group_id,
        )

        if not has_permission:
            permission_str = permission.value if isinstance(permission, Permission) else permission
            raise ForbiddenError(
                _("Permission denied: %(permission)s in group %(group_id)s")
                % {"permission": permission_str, "group_id": group_id}
            )

        return current_user

    return _check_permission_in_group
