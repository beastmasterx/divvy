"""
Authorization service for RBAC permission checking and role management.
"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import ValidationError
from app.models import GroupRole, Permission, SystemRole
from app.repositories import AuthorizationRepository


class AuthorizationService:
    """Service layer for authorization-related business logic and permission checking."""

    def __init__(self, session: AsyncSession):
        self._auth_repository = AuthorizationRepository(session)

    # ========== Permission Checking ==========

    async def has_permission(
        self,
        user_id: int,
        permission: str | Permission,
        group_id: int | None = None,
    ) -> bool:
        """Check if a user has a specific permission.

        Checks both system-level and group-level roles:
        - System roles: ADMIN has all permissions
        - Group roles: Checks group role bindings if group_id is provided
        - Role permissions: Checks RolePermission mappings

        Args:
            user_id: ID of the user to check
            permission: Permission to check (e.g., "groups:read")
            group_id: Optional group ID for group-scoped permissions

        Returns:
            True if user has the permission, False otherwise
        """
        permission_str = permission.value if isinstance(permission, Permission) else permission

        # Get user's system roles
        system_roles = await self._auth_repository.get_system_roles(user_id)

        # System ADMIN has all permissions
        if SystemRole.ADMIN.value in system_roles:
            return True

        # Check system role permissions
        for role in system_roles:
            role_permissions = await self._auth_repository.get_role_permissions(role)
            if permission_str in role_permissions:
                return True

        # If group_id is provided, check group-level permissions
        if group_id is not None:
            group_role = await self._auth_repository.get_user_group_role(user_id, group_id)
            if group_role:
                # Group OWNER has all group permissions
                if group_role == GroupRole.OWNER.value:
                    return True

                # Check group role permissions
                group_role_permissions = await self._auth_repository.get_role_permissions(group_role)
                if permission_str in group_role_permissions:
                    return True

        return False

    async def has_any_permission(
        self,
        user_id: int,
        permissions: Sequence[str | Permission],
        group_id: int | None = None,
    ) -> bool:
        """Check if a user has any of the specified permissions.

        Args:
            user_id: ID of the user to check
            permissions: List of permissions to check
            group_id: Optional group ID for group-scoped permissions

        Returns:
            True if user has at least one permission, False otherwise
        """
        for permission in permissions:
            if await self.has_permission(user_id, permission, group_id):
                return True
        return False

    async def has_all_permissions(
        self,
        user_id: int,
        permissions: Sequence[str | Permission],
        group_id: int | None = None,
    ) -> bool:
        """Check if a user has all of the specified permissions.

        Args:
            user_id: ID of the user to check
            permissions: List of permissions to check
            group_id: Optional group ID for group-scoped permissions

        Returns:
            True if user has all permissions, False otherwise
        """
        for permission in permissions:
            if not await self.has_permission(user_id, permission, group_id):
                return False
        return True

    # ========== System Role Management ==========

    async def get_system_roles(self, user_id: int) -> Sequence[str]:
        """Get all system roles for a user."""
        return await self._auth_repository.get_system_roles(user_id)

    async def assign_system_role(self, user_id: int, role: str | SystemRole) -> None:
        """Assign a system role to a user.

        Args:
            user_id: ID of the user
            role: System role to assign

        Raises:
            ValidationError: If role is invalid
        """
        role_str = role.value if isinstance(role, SystemRole) else role
        if role_str not in [r.value for r in SystemRole]:
            raise ValidationError(_("Invalid system role: %s") % role_str)

        # Check if already assigned
        existing_roles = await self._auth_repository.get_system_roles(user_id)
        if role_str in existing_roles:
            return  # Already assigned, no-op

        await self._auth_repository.create_system_role_binding(user_id, role_str)

    async def unassign_system_role(self, user_id: int, role: str | SystemRole) -> None:
        """Unassign a system role from a user.

        Args:
            user_id: ID of the user
            role: System role to unassign

        Raises:
            ValidationError: If role is invalid
        """
        role_str = role.value if isinstance(role, SystemRole) else role
        if role_str not in [r.value for r in SystemRole]:
            raise ValidationError(_("Invalid system role: %s") % role_str)

        await self._auth_repository.delete_system_role_binding(user_id, role_str)

    # ========== Group Role Management ==========

    async def get_group_role(self, user_id: int, group_id: int) -> str | None:
        """Get user's role in a specific group."""
        return await self._auth_repository.get_user_group_role(user_id, group_id)

    async def assign_group_role(
        self,
        user_id: int,
        group_id: int,
        role: str | GroupRole,
    ) -> None:
        """Assign a group role to a user.

        Creates a new binding if it doesn't exist, or updates the existing one.

        Args:
            user_id: ID of the user
            group_id: ID of the group
            role: Group role to assign

        Raises:
            ValidationError: If role is invalid
        """
        role_str = role.value if isinstance(role, GroupRole) else role
        if role_str not in [r.value for r in GroupRole]:
            raise ValidationError(_("Invalid group role: %s") % role_str)

        # Check if binding exists
        existing_role = await self._auth_repository.get_user_group_role(user_id, group_id)
        if existing_role:
            await self._auth_repository.update_group_role_binding(user_id, group_id, role_str)
        else:
            await self._auth_repository.create_group_role_binding(user_id, group_id, role_str)

    async def unassign_group_role(self, user_id: int, group_id: int) -> None:
        """Unassign a group role from a user.

        Args:
            user_id: ID of the user
            group_id: ID of the group
        """
        await self._auth_repository.delete_group_role_binding(user_id, group_id)

    # ========== Role Permission Management ==========

    async def get_role_permissions(self, role: str) -> Sequence[str]:
        """Get all permissions for a role."""
        return await self._auth_repository.get_role_permissions(role)

    async def assign_permission_to_role(self, role: str, permission: str | Permission) -> None:
        """Assign a permission to a role.

        Args:
            role: Role name (system or group role)
            permission: Permission to assign

        Raises:
            ValidationError: If permission is invalid
        """
        permission_str = permission.value if isinstance(permission, Permission) else permission
        if permission_str not in [p.value for p in Permission]:
            raise ValidationError(_("Invalid permission: %s") % permission_str)

        # Check if already assigned
        existing_permissions = await self._auth_repository.get_role_permissions(role)
        if permission_str in existing_permissions:
            return  # Already assigned, no-op

        await self._auth_repository.create_role_permission(role, permission_str)

    async def unassign_permission_from_role(self, role: str, permission: str | Permission) -> None:
        """Unassign a permission from a role.

        Args:
            role: Role name (system or group role)
            permission: Permission to unassign

        Raises:
            ValidationError: If permission is invalid
        """
        permission_str = permission.value if isinstance(permission, Permission) else permission
        if permission_str not in [p.value for p in Permission]:
            raise ValidationError(_("Invalid permission: %s") % permission_str)

        await self._auth_repository.delete_role_permission(role, permission_str)
