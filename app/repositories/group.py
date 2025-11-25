from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, GroupRole, GroupRoleBinding, User


class GroupRepository:
    """Repository for managing group entities and their relationships with users and periods."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_groups(self) -> Sequence[Group]:
        """Retrieve all groups from the database."""
        stmt = select(Group)
        return (await self.session.scalars(stmt)).all()

    async def get_group_by_id(self, id: int) -> Group | None:
        """Retrieve a specific group by its ID."""
        return await self.session.get(Group, id)

    async def create_group(self, group: Group) -> Group:
        """Create a new group and persist it to the database."""
        self.session.add(group)
        await self.session.flush()
        return group

    async def update_group(self, group: Group) -> Group:
        """Update an existing group and commit changes to the database."""
        await self.session.flush()
        return group

    async def delete_group(self, id: int) -> None:
        """Delete a group by its ID if it exists."""
        stmt = delete(Group).where(Group.id == id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_users_by_group_id(self, group_id: int) -> Sequence[User]:
        """Retrieve all users associated with a specific group (via GroupRoleBinding)."""
        stmt = (
            select(User)
            .join(GroupRoleBinding, User.id == GroupRoleBinding.user_id)
            .where(GroupRoleBinding.group_id == group_id)
        )
        return (await self.session.scalars(stmt)).all()

    async def check_if_user_is_in_group(self, group_id: int, user_id: int) -> bool:
        """Check if a user is in a specific group (has any GroupRoleBinding)."""
        stmt = select(GroupRoleBinding).where(
            GroupRoleBinding.group_id == group_id,
            GroupRoleBinding.user_id == user_id,
        )
        return (await self.session.scalars(stmt)).one_or_none() is not None

    async def get_group_owner(self, group_id: int) -> int | None:
        """Get the owner user_id for a group."""
        stmt = (
            select(GroupRoleBinding.user_id)
            .where(
                GroupRoleBinding.group_id == group_id,
                GroupRoleBinding.role == GroupRole.OWNER.value,
            )
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def get_groups_by_user_id(self, user_id: int) -> Sequence[Group]:
        """Retrieve all groups that a specific user is a member of (via GroupRoleBinding)."""
        stmt = (
            select(Group)
            .join(GroupRoleBinding, Group.id == GroupRoleBinding.group_id)
            .where(GroupRoleBinding.user_id == user_id)
        )
        return (await self.session.scalars(stmt)).all()
