"""
Repository for authorization-related data access.
"""

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GroupRoleBinding, RolePermission, SystemRoleBinding


class AuthorizationRepository:
    """Repository for authorization-related queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== System Role Bindings ==========

    async def get_system_role(self, user_id: int) -> str | None:
        """Get user's system role (single role per user)."""
        stmt = select(SystemRoleBinding.role).where(SystemRoleBinding.user_id == user_id)
        return await self.session.scalar(stmt)

    async def assign_system_role(
        self,
        user_id: int,
        role: str | None,
    ) -> SystemRoleBinding | None:
        """Assign a system role to a user (upsert) or remove it (if role is None).

        Args:
            user_id: ID of the user
            role: Role to assign, or None to remove the role binding

        Returns:
            SystemRoleBinding if role was assigned, None if role was removed
        """
        if role is None:
            # Delete the binding
            stmt = delete(SystemRoleBinding).where(
                SystemRoleBinding.user_id == user_id,
            )
            await self.session.execute(stmt)
            await self.session.flush()
            return None

        # Upsert: Check if binding exists
        stmt = select(SystemRoleBinding).where(
            SystemRoleBinding.user_id == user_id,
        )
        binding = (await self.session.scalars(stmt)).one_or_none()

        if binding:
            # Update existing binding
            binding.role = role
        else:
            # Create new binding
            binding = SystemRoleBinding(user_id=user_id, role=role)
            self.session.add(binding)

        await self.session.flush()
        return binding

    # ========== Group Role Bindings ==========

    async def get_group_role(self, user_id: int, group_id: int) -> str | None:
        """Get user's role in a specific group."""
        stmt = select(GroupRoleBinding.role).where(
            GroupRoleBinding.user_id == user_id,
            GroupRoleBinding.group_id == group_id,
        )
        return await self.session.scalar(stmt)

    async def assign_group_role(
        self,
        user_id: int,
        group_id: int,
        role: str | None,
    ) -> GroupRoleBinding | None:
        """Assign a group role to a user (upsert) or remove it (if role is None).

        Args:
            user_id: ID of the user
            group_id: ID of the group
            role: Role to assign, or None to remove the role binding

        Returns:
            GroupRoleBinding if role was assigned, None if role was removed
        """
        if role is None:
            # Delete the binding
            stmt = delete(GroupRoleBinding).where(
                GroupRoleBinding.user_id == user_id,
                GroupRoleBinding.group_id == group_id,
            )
            await self.session.execute(stmt)
            await self.session.flush()
            return None

        # Upsert: Check if binding exists
        stmt = select(GroupRoleBinding).where(
            GroupRoleBinding.user_id == user_id,
            GroupRoleBinding.group_id == group_id,
        )
        binding = (await self.session.scalars(stmt)).one_or_none()

        if binding:
            # Update existing binding
            binding.role = role
        else:
            # Create new binding
            binding = GroupRoleBinding(user_id=user_id, group_id=group_id, role=role)
            self.session.add(binding)

        await self.session.flush()
        return binding

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
