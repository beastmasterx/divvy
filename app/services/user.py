from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.api.schemas import ProfileRequest, UserRequest
from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Group, User
from app.repositories import UserRepository


class UserService:
    """Service layer for user-related business logic and operations."""

    def __init__(self, session: Session):
        self._user_repository = UserRepository(session)

    def get_all_users(self) -> Sequence[User]:
        """Retrieve all users."""
        return self._user_repository.get_all_users()

    def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a specific user by their ID."""
        return self._user_repository.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        """Retrieve a specific user by their email address."""
        return self._user_repository.get_user_by_email(email)

    def get_groups_by_user_id(self, user_id: int) -> Sequence[Group]:
        """Retrieve all groups that a specific user is a member of."""
        return self._user_repository.get_groups_by_user_id(user_id)

    def create_user(self, request: UserRequest) -> User:
        """
        Create a new user.

        Args:
            request: User request schema containing user data

        Returns:
            Created User model
        """
        user = User(
            email=request.email,
            name=request.name,
            password=request.password,  # Note: password should be hashed before calling this
            is_active=request.is_active,
            avatar=request.avatar,
        )
        return self._user_repository.create_user(user)

    def reset_password(self, user_id: int, new_password: str) -> User:
        """
        Reset a user's password.

        Args:
            user_id: ID of the user to reset the password
            new_password: New password (should be hashed before calling this)

        Returns:
            Updated User model
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)

        user.password = new_password
        return self._user_repository.update_user(user)

    def update_profile(self, user_id: int, request: ProfileRequest) -> User:
        """
        Update an existing user's profile (non-password fields).

        Args:
            user_id: ID of the user to update
            request: Profile request schema containing updated user data

        Returns:
            Updated User model

        Raises:
            NotFoundError: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)

        # Only update fields that are provided (None means no change)
        if request.email is not None:
            user.email = request.email
        if request.name is not None:
            user.name = request.name
        if request.is_active is not None:
            user.is_active = request.is_active
        if request.avatar is not None:
            user.avatar = request.avatar

        return self._user_repository.update_user(user)

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

        return self._user_repository.delete_user(user_id)
