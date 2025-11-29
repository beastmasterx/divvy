"""
Authorization service for role management.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import ValidationError
from app.models import GroupRole, SystemRole
from app.repositories import AuthorizationRepository


class AuthorizationService:
    """Service layer for authorization-related business logic and role management."""

    def __init__(self, session: AsyncSession):
        self._auth_repository = AuthorizationRepository(session)

    # ========== System Role Management ==========

    async def get_system_role(self, user_id: int) -> str | None:
        """Get user's system role (single role per user)."""
        return await self._auth_repository.get_system_role(user_id)

    async def assign_system_role(
        self,
        user_id: int,
        role: str | SystemRole,
    ) -> None:
        """Assign a system role to a user (switches role if one already exists).

        Users must always have a system role. This method switches between roles.
        To switch from admin to user, call: assign_system_role(user_id, SystemRole.USER)

        Args:
            user_id: ID of the user
            role: System role to assign (required, cannot be None)

        Raises:
            ValidationError: If role is invalid
        """
        role_str = role.value if isinstance(role, SystemRole) else role
        if role_str not in [r.value for r in SystemRole]:
            raise ValidationError(_("Invalid system role: %s") % role_str)

        # Upsert: creates or updates the role
        await self._auth_repository.assign_system_role(user_id, role_str)

    # ========== Group Role Management ==========

    async def get_group_role(self, user_id: int, group_id: int) -> str | None:
        """Get user's role in a specific group."""
        return await self._auth_repository.get_group_role(user_id, group_id)

    async def get_group_owner(self, group_id: int) -> int | None:
        """Get the owner user_id for a group."""
        return await self._auth_repository.get_group_owner(group_id)

    async def assign_group_role(self, user_id: int, group_id: int, role: GroupRole | None) -> None:
        """Assign a group role to a user, or remove them from the group if role is None.

        Creates a new binding if it doesn't exist, updates the existing one,
        or deletes it if role is None (removes user from group).

        Args:
            user_id: ID of the user
            group_id: ID of the group
            role: Group role to assign, or None to remove user from group
        """
        # Upsert or delete
        role_str = role.value if role else None
        await self._auth_repository.assign_group_role(user_id, group_id, role_str)
