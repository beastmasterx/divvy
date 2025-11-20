from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Group, User
from app.repositories import UserRepository


class UserService:
    """Service layer for user-related business logic and operations."""

    def __init__(self, session: Session):
        self.user_repository = UserRepository(session)

    def get_all_users(self) -> Sequence[User]:
        """Retrieve all users."""
        return self.user_repository.get_all_users()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a specific user by their ID."""
        return self.user_repository.get_user_by_id(user_id)

    def create_user(self, user: User) -> User:
        """Create a new user."""
        return self.user_repository.create_user(user)

    def update_user(self, user: User) -> User:
        """Update an existing user."""
        return self.user_repository.update_user(user)

    def delete_user(self, user_id: int) -> None:
        """Delete a user by their ID.

        User must leave all groups before deletion. This ensures all periods
        are settled and there are no active transactions involving the user.

        Args:
            user_id: ID of the user to delete

        Raises:
            NotFoundError: If user not found
            BusinessRuleError: If user is still a member of groups
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)

        groups = self.get_groups_by_user_id(user_id)

        if groups:
            group_names = [g.name for g in groups]
            raise BusinessRuleError(
                _(
                    "Cannot delete user '%(user_name)s': they are still a member of group(s) "
                    "%(group_names)s. Please remove them from all groups first."
                )
                % {
                    "user_name": user.name,
                    "group_names": ", ".join(f"'{g}'" for g in group_names),
                }
            )

        return self.user_repository.delete_user(user_id)

    def get_groups_by_user_id(self, user_id: int) -> Sequence[Group]:
        """Retrieve all groups that a specific user is a member of."""
        return self.user_repository.get_groups_by_user_id(user_id)
