"""
Repository for authorization-related data access.
"""

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import GroupRoleBinding, RolePermission, SystemRoleBinding


class AuthorizationRepository:
    """Repository for authorization-related queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== System Role Bindings ==========

    async def get_system_roles(self, user_id: int) -> Sequence[str]:
        """Get all system roles for a user."""
        stmt = select(SystemRoleBinding.role).where(SystemRoleBinding.user_id == user_id)
        return (await self.session.scalars(stmt)).all()

    async def create_system_role_binding(
        self,
        user_id: int,
        role: str,
    ) -> SystemRoleBinding:
        """Create a system role binding."""
        binding = SystemRoleBinding(user_id=user_id, role=role)
        self.session.add(binding)
        await self.session.flush()
        return binding

    async def delete_system_role_binding(
        self,
        user_id: int,
        role: str,
    ) -> None:
        """Delete a system role binding."""
        stmt = delete(SystemRoleBinding).where(
            SystemRoleBinding.user_id == user_id,
            SystemRoleBinding.role == role,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    # ========== Group Role Bindings ==========

    async def get_user_group_role(self, user_id: int, group_id: int) -> str | None:
        """Get user's role in a specific group."""
        stmt = select(GroupRoleBinding.role).where(
            GroupRoleBinding.user_id == user_id,
            GroupRoleBinding.group_id == group_id,
        )
        return await self.session.scalar(stmt)

    async def create_group_role_binding(
        self,
        user_id: int,
        group_id: int,
        role: str,
    ) -> GroupRoleBinding:
        """Create a group role binding."""
        binding = GroupRoleBinding(user_id=user_id, group_id=group_id, role=role)
        self.session.add(binding)
        await self.session.flush()
        return binding

    async def update_group_role_binding(
        self,
        user_id: int,
        group_id: int,
        role: str,
    ) -> GroupRoleBinding:
        """Update an existing group role binding.

        Raises:
            NotFoundError: If the binding does not exist
        """
        stmt = select(GroupRoleBinding).where(
            GroupRoleBinding.user_id == user_id,
            GroupRoleBinding.group_id == group_id,
        )
        binding = (await self.session.scalars(stmt)).one_or_none()
        if not binding:
            raise NotFoundError(
                _("Group role binding not found for user %(user_id)s in group %(group_id)s")
                % {"user_id": user_id, "group_id": group_id}
            )
        binding.role = role
        await self.session.flush()
        return binding

    async def delete_group_role_binding(
        self,
        user_id: int,
        group_id: int,
    ) -> None:
        """Delete a group role binding."""
        stmt = delete(GroupRoleBinding).where(
            GroupRoleBinding.user_id == user_id,
            GroupRoleBinding.group_id == group_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    # ========== Role Permissions ==========

    async def get_role_permissions(self, role: str) -> Sequence[str]:
        """Get all permissions for a role."""
        stmt = select(RolePermission.permission).where(RolePermission.role == role)
        return (await self.session.scalars(stmt)).all()

    async def create_role_permission(
        self,
        role: str,
        permission: str,
    ) -> RolePermission:
        """Create a role permission mapping."""
        role_permission = RolePermission(role=role, permission=permission)
        self.session.add(role_permission)
        await self.session.flush()
        return role_permission

    async def delete_role_permission(
        self,
        role: str,
        permission: str,
    ) -> None:
        """Delete a role permission mapping."""
        stmt = delete(RolePermission).where(
            RolePermission.role == role,
            RolePermission.permission == permission,
        )
        await self.session.execute(stmt)
        await self.session.flush()
