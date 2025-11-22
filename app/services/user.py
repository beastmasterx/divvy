from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.api.schemas import ProfileRequest, UserRequest, UserResponse
from app.core.i18n import _
from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Group, User
from app.repositories import UserRepository


class UserService:
    """Service layer for user-related business logic and operations."""

    def __init__(self, session: Session):
        self._user_repository = UserRepository(session)

    def get_all_users(self) -> Sequence[UserResponse]:
        """Retrieve all users."""
        users = self._user_repository.get_all_users()
        return [UserResponse.model_validate(user) for user in users]

    def get_user_by_id(self, user_id: int) -> UserResponse | None:
        """Retrieve a specific user by their ID."""
        user = self._user_repository.get_user_by_id(user_id)
        return UserResponse.model_validate(user) if user else None

    def get_user_by_email(self, email: str) -> UserResponse | None:
        """Retrieve a specific user by their email address."""
        user = self._user_repository.get_user_by_email(email)
        return UserResponse.model_validate(user) if user else None

    def get_groups_by_user_id(self, user_id: int) -> Sequence[Group]:
        """Retrieve all groups that a specific user is a member of."""
        return self._user_repository.get_groups_by_user_id(user_id)

    def create_user(self, request: UserRequest) -> UserResponse:
        """
        Create a new user.

        Args:
            request: User request schema containing user data

        Returns:
            Created User response DTO
        """
        user = User(
            email=request.email,
            name=request.name,
            password=request.password,  # Note: password should be hashed before calling this
            is_active=request.is_active,
        )
        user = self._user_repository.create_user(user)
        return UserResponse.model_validate(user)

    def reset_password(self, user_id: int, new_hashed_password: str) -> UserResponse:
        """
        Reset a user's password.

        Args:
            user_id: ID of the user to reset the password
            new_password: New password (should be hashed before calling this)

        Returns:
            Updated User response DTO
        """
        user = self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)

        user.password = new_hashed_password
        updated_user = self._user_repository.update_user(user)
        return UserResponse.model_validate(updated_user)

    def update_profile(self, user_id: int, request: ProfileRequest) -> UserResponse:
        """
        Update an existing user's profile (non-password fields).

        Args:
            user_id: ID of the user to update
            request: Profile request schema containing updated user data

        Returns:
            Updated User response DTO

        Raises:
            NotFoundError: If user not found
        """
        user = self._user_repository.get_user_by_id(user_id)
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

        updated_user = self._user_repository.update_user(user)
        return UserResponse.model_validate(updated_user)

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
        user = self._user_repository.get_user_by_id(user_id)
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
