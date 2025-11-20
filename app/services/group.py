from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.i18n import _
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.models import Group, Period, User
from app.repositories import GroupRepository
from app.services.user import UserService


class GroupService:
    """Service layer for group-related business logic and operations."""

    def __init__(self, session: Session):
        self.group_repository = GroupRepository(session)
        self.user_service = UserService(session)

    def get_all_groups(self) -> Sequence[Group]:
        """Retrieve all groups."""
        return self.group_repository.get_all_groups()

    def get_group_by_id(self, group_id: int) -> Group | None:
        """Retrieve a specific group by its ID."""
        return self.group_repository.get_group_by_id(group_id)

    def create_group(self, group: Group) -> Group:
        """Create a new group."""
        return self.group_repository.create_group(group)

    def update_group(self, group: Group) -> Group:
        """Update an existing group."""
        return self.group_repository.update_group(group)

    def delete_group(self, group_id: int) -> None:
        """Delete a group by its ID.

        Group can only be deleted if the active period (if any) with transactions
        is already settled. This ensures data integrity for active settlements.

        Args:
            group_id: ID of the group to delete

        Raises:
            NotFoundError: If group not found
            BusinessRuleError: If active period with transactions is not settled
        """
        group = self.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        # Check for active period with transactions
        active_period = self.get_current_period_by_group_id(group_id)

        # Active period exists with transactions - must be settled first
        if active_period and active_period.transactions and not active_period.is_settled:
            raise BusinessRuleError(
                _(
                    "Cannot delete group '%(group_name)s': the active period '%(period_name)s' "
                    "has transactions and is not settled. Please settle the period first."
                )
                % {
                    "group_name": group.name,
                    "period_name": active_period.name,
                }
            )

        # All checks passed - safe to delete group
        return self.group_repository.delete_group(group_id)

    def get_users_by_group_id(self, group_id: int) -> Sequence[User]:
        """Retrieve all users associated with a specific group."""
        return self.group_repository.get_users_by_group_id(group_id)

    def get_active_users_by_group_id(self, group_id: int) -> Sequence[User]:
        """Retrieve only active users associated with a specific group."""
        return self.group_repository.get_active_users_by_group_id(group_id)

    def add_user_to_group(self, group_id: int, user_id: int) -> None:
        """Add a user to a group.

        Users can join a group at any time. They will participate in future
        transactions but not in past transactions.

        Args:
            group_id: ID of the group
            user_id: ID of the user to add

        Raises:
            NotFoundError: If group/user not found
            ConflictError: If user already in group
        """
        self._validate_group_and_user(group_id, user_id)

        # Get group and user for better error messages (already validated, so not None)
        group = self.get_group_by_id(group_id)
        user = self.user_service.get_user_by_id(user_id)
        assert group is not None and user is not None  # Type narrowing after validation

        # Check for duplicate membership
        if self.group_repository.check_if_user_is_in_group(group_id, user_id):
            raise ConflictError(
                _("User '%(user_name)s' is already a member of group '%(group_name)s'")
                % {"user_name": user.name, "group_name": group.name}
            )

        # User can join anytime - no period validation needed
        self.group_repository.add_user_to_group(group_id, user_id)

    def remove_user_from_group(self, group_id: int, user_id: int) -> None:
        """Remove a user from a group.

        User can only leave if the active period (if any) with transactions
        is already settled. This ensures data integrity for active settlements.

        Args:
            group_id: ID of the group
            user_id: ID of the user to remove

        Raises:
            NotFoundError: If group/user not found, or user not in group
            BusinessRuleError: If active period with transactions is not settled
        """
        self._validate_group_and_user(group_id, user_id)

        # Get group and user for better error messages (already validated, so not None)
        group = self.get_group_by_id(group_id)
        user = self.user_service.get_user_by_id(user_id)
        assert group is not None and user is not None  # Type narrowing after validation

        # Check if user is actually in the group
        if not self.group_repository.check_if_user_is_in_group(group_id, user_id):
            raise NotFoundError(
                _("User '%(user_name)s' is not a member of group '%(group_name)s'")
                % {"user_name": user.name, "group_name": group.name}
            )

        # Check for active period with transactions
        active_period = self.get_current_period_by_group_id(group_id)

        # Active period exists with transactions - must be settled first
        if active_period and active_period.transactions and not active_period.is_settled:
            raise BusinessRuleError(
                _(
                    "Cannot remove user '%(user_name)s' from group '%(group_name)s': "
                    "the active period '%(period_name)s' has transactions and is not settled. "
                    "Please settle the period first."
                )
                % {
                    "user_name": user.name,
                    "group_name": group.name,
                    "period_name": active_period.name,
                }
            )

        # All checks passed - safe to remove user
        return self.group_repository.remove_user_from_group(group_id, user_id)

    def get_periods_by_group_id(self, group_id: int) -> Sequence[Period]:
        """Retrieve all periods associated with a specific group."""
        return self.group_repository.get_periods_by_group_id(group_id)

    def get_current_period_by_group_id(self, group_id: int) -> Period | None:
        """Retrieve the current unsettled period for a specific group."""
        return self.group_repository.get_current_period_by_group_id(group_id)

    def _validate_group_and_user(self, group_id: int, user_id: int) -> None:
        """Validate that a group and user exist.

        Args:
            group_id: ID of the group
            user_id: ID of the user

        Raises:
            NotFoundError: If group or user not found
        """
        group = self.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)
