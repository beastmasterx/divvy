from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.core.security import check_password, hash_password
from app.exceptions import BusinessRuleError, NotFoundError, UnauthorizedError
from app.models import User
from app.repositories import GroupRepository, UserRepository
from app.schemas import ProfileRequest, UserRequest, UserResponse


class UserService:
    """Service layer for user-related business logic and operations."""

    def __init__(self, session: AsyncSession):
        self._user_repository = UserRepository(session)
        self._group_repository = GroupRepository(session)

    async def get_all_users(self) -> Sequence[UserResponse]:
        """Retrieve all users."""
        users = await self._user_repository.get_all_users()
        return [UserResponse.model_validate(user) for user in users]

    async def get_user_by_id(self, user_id: int) -> UserResponse | None:
        """Retrieve a specific user by their ID."""
        user = await self._user_repository.get_user_by_id(user_id)
        return UserResponse.model_validate(user) if user else None

    async def get_user_by_email(self, email: str) -> UserResponse | None:
        """Retrieve a specific user by their email address."""
        user = await self._user_repository.get_user_by_email(email)
        return UserResponse.model_validate(user) if user else None

    async def get_users_by_group_id(self, group_id: int) -> Sequence[User]:
        """Retrieve all users associated with a specific group."""
        return await self._group_repository.get_users_by_group_id(group_id)

    async def create_user(self, request: UserRequest) -> UserResponse:
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
        user = await self._user_repository.create_user(user)
        return UserResponse.model_validate(user)

    async def check_password(self, email: str, password: str) -> bool:
        """Check if a user's password is correct."""
        user = await self._user_repository.get_user_by_email(email)
        if not user or user.password is None:
            return False
        return check_password(password, user.password)

    async def change_password(self, email: str, old_password: str, new_password: str) -> UserResponse:
        """
        Change a user's password.

        Args:
            email: Email of the user to change the password
            old_password: Current password for verification
            new_password: New password

        Returns:
            Updated User response DTO

        Raises:
            UnauthorizedError: If user not found or password is invalid or current password is incorrect
        """
        user = await self._user_repository.get_user_by_email(email)
        if not user or not user.password:
            raise UnauthorizedError("User not found or password is invalid")

        if not check_password(old_password, user.password):
            raise UnauthorizedError("Current password is incorrect")

        user.password = hash_password(new_password)
        updated_user = await self._user_repository.update_user(user)
        return UserResponse.model_validate(updated_user)

    async def reset_password(self, email: str, new_hashed_password: str) -> UserResponse:
        """
        Reset a user's password.

        Args:
            email: Email of the user to reset the password
            new_password: New password (should be hashed before calling this)

        Returns:
            Updated User response DTO

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repository.get_user_by_email(email)
        if not user:
            raise NotFoundError(_("User not found"))

        user.password = new_hashed_password
        updated_user = await self._user_repository.update_user(user)
        return UserResponse.model_validate(updated_user)

    async def update_profile(self, user_id: int, request: ProfileRequest) -> UserResponse:
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
        user = await self._user_repository.get_user_by_id(user_id)
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

        updated_user = await self._user_repository.update_user(user)
        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: int) -> None:
        """Delete a user by their ID.

        User must leave all groups before deletion. This ensures all periods
        are settled and there are no active transactions involving the user.

        Args:
            user_id: ID of the user to delete

        Raises:
            NotFoundError: If user not found
            BusinessRuleError: If user is still a member of groups
        """
        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)

        groups = await self._group_repository.get_groups_by_user_id(user_id)

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

        return await self._user_repository.delete_user(user_id)
