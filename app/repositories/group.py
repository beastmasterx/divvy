from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Group, GroupUser, Period, User


class GroupRepository:
    """Repository for managing group entities and their relationships with users and periods."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_groups(self) -> Sequence[Group]:
        """Retrieve all groups from the database."""
        stmt = select(Group)
        return self.session.execute(stmt).scalars().all()

    def get_group_by_id(self, group_id: int) -> Group | None:
        """Retrieve a specific group by its ID."""
        stmt = select(Group).where(Group.id == group_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_group(self, group: Group) -> Group:
        """Create a new group and persist it to the database."""
        self.session.add(group)
        self.session.commit()
        return group

    def update_group(self, group: Group) -> Group:
        """Update an existing group and commit changes to the database."""
        self.session.commit()
        return group

    def delete_group(self, group_id: int) -> None:
        """Delete a group by its ID if it exists."""
        group = self.get_group_by_id(group_id)
        if group:
            self.session.delete(group)
            self.session.commit()

    def get_users_by_group_id(self, group_id: int) -> Sequence[User]:
        """Retrieve all users associated with a specific group."""
        stmt = select(User).join(GroupUser, User.id == GroupUser.user_id).where(GroupUser.group_id == group_id)
        return self.session.execute(stmt).scalars().all()

    def check_if_user_is_in_group(self, group_id: int, user_id: int) -> bool:
        """Check if a user is in a specific group."""
        stmt = select(GroupUser).where(GroupUser.group_id == group_id).where(GroupUser.user_id == user_id)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def add_user_to_group(self, group_id: int, user_id: int) -> None:
        """Add a user to a group by creating a GroupUser relationship."""
        group_user = GroupUser(group_id=group_id, user_id=user_id)
        self.session.add(group_user)
        self.session.commit()

    def remove_user_from_group(self, group_id: int, user_id: int) -> None:
        """Remove a user from a group by deleting the GroupUser relationship."""
        stmt = delete(GroupUser).where(GroupUser.group_id == group_id).where(GroupUser.user_id == user_id)
        self.session.execute(stmt)
        self.session.commit()

    def get_periods_by_group_id(self, group_id: int) -> Sequence[Period]:
        """Retrieve all periods associated with a specific group."""
        stmt = select(Period).where(Period.group_id == group_id)
        return self.session.execute(stmt).scalars().all()

    def get_current_period_by_group_id(self, group_id: int) -> Period | None:
        """Retrieve the current unsettled period for a specific group."""
        stmt = select(Period).where(Period.group_id == group_id, Period.end_date.is_(None))
        return self.session.execute(stmt).scalar_one_or_none()
