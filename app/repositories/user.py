from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, GroupUser, User


class UserRepository:
    """Repository for managing user entities and their group memberships."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_users(self) -> Sequence[User]:
        """Retrieve all users from the database."""
        stmt = select(User)
        return self.session.execute(stmt).scalars().all()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a specific user by their ID."""
        stmt = select(User).where(User.id == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_user_by_email(self, email: str) -> User | None:
        """Retrieve a specific user by their email address."""
        stmt = select(User).where(User.email == email)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_user(self, user: User) -> User:
        """Create a new user and persist them to the database."""
        self.session.add(user)
        self.session.commit()
        return user

    def update_user(self, user: User) -> User:
        """Update an existing user and commit changes to the database."""
        self.session.commit()
        return user

    def delete_user(self, user_id: int) -> None:
        """Delete a user by their ID if they exist."""
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()

    def get_groups_by_user_id(self, user_id: int) -> Sequence[Group]:
        """Retrieve all groups that a specific user is a member of."""
        stmt = select(Group).join(GroupUser, Group.id == GroupUser.group_id).where(GroupUser.user_id == user_id)
        return self.session.execute(stmt).scalars().all()
