from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.models import Group, GroupRole, Permission
from app.repositories import GroupRepository, UserRepository
from app.schemas import GroupRequest, GroupResponse
from app.services.authorization import AuthorizationService
from app.services.period import PeriodService


class GroupService:
    """Service layer for group-related business logic and operations."""

    def __init__(
        self,
        session: AsyncSession,
        authorization_service: AuthorizationService,
        period_service: PeriodService,
    ):
        self._group_repository = GroupRepository(session)
        self._user_repository = UserRepository(session)
        self._authorization_service = authorization_service
        self._period_service = period_service

    async def get_all_groups(self) -> Sequence[GroupResponse]:
        """Retrieve all groups."""
        groups = await self._group_repository.get_all_groups()
        return [GroupResponse.model_validate(group) for group in groups]

    async def get_group_by_id(self, group_id: int) -> GroupResponse | None:
        """Retrieve a specific group by its ID."""
        group = await self._group_repository.get_group_by_id(group_id)
        return GroupResponse.model_validate(group) if group else None

    async def get_groups_by_user_id(self, user_id: int) -> Sequence[GroupResponse]:
        """Retrieve all groups that a specific user is a member of."""
        groups = await self._group_repository.get_groups_by_user_id(user_id)
        return [GroupResponse.model_validate(group) for group in groups]

    async def get_group_owner(self, group_id: int) -> int | None:
        """Get the owner user_id for a group.

        Args:
            group_id: ID of the group

        Returns:
            User ID of the owner, or None if no owner exists
        """
        return await self._group_repository.get_group_owner(group_id)

    async def create_group(self, group_request: GroupRequest, owner_id: int) -> GroupResponse:
        """Create a new group.

        Creates the group and assigns the owner role via GroupRoleBinding.

        Args:
            group_request: Pydantic schema containing group data
            owner_id: ID of the user who will own the group.

        Returns:
            Created Group response DTO

        Raises:
            ValidationError: If owner_id is not provided and group requires it
        """
        # Create group without owner_id (will be removed from model)
        group = Group(name=group_request.name)
        group = await self._group_repository.create_group(group)

        # Assign owner role via GroupRoleBinding
        await self._authorization_service.assign_group_role(
            user_id=owner_id,
            group_id=group.id,
            role=GroupRole.OWNER,
        )

        return GroupResponse.model_validate(group)

    async def update_group(self, group_id: int, group_request: GroupRequest) -> GroupResponse:
        """Update an existing group.

        Args:
            group_id: ID of the group to update
            group_request: Pydantic schema containing updated group data

        Returns:
            Updated Group response DTO

        Raises:
            NotFoundError: If group not found
        """
        # Fetch existing group from repository (need ORM for modification)
        group = await self._group_repository.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        # Update fields from request
        group.name = group_request.name

        updated_group = await self._group_repository.update_group(group)
        return GroupResponse.model_validate(updated_group)

    async def update_group_owner(self, group_id: int, owner_id: int) -> GroupResponse:
        """Update the owner of a specific group by its ID.

        Transfers ownership by updating GroupRoleBinding roles.

        Args:
            group_id: ID of the group to update
            owner_id: ID of the user to set as owner

        Returns:
            Updated Group response DTO
        """
        # Fetch from repository
        group = await self._group_repository.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        # Check if user is a member
        if not await self._group_repository.check_if_user_is_in_group(group_id, owner_id):
            raise NotFoundError(_("User %s is not a member of group %s") % (owner_id, group.name))

        # Get current owner
        current_owner_id = await self._group_repository.get_group_owner(group_id)

        # Transfer ownership: demote old owner to member, promote new user to owner
        if current_owner_id and current_owner_id != owner_id:
            await self._authorization_service.assign_group_role(
                user_id=current_owner_id,
                group_id=group_id,
                role=GroupRole.MEMBER,
            )

        await self._authorization_service.assign_group_role(
            user_id=owner_id,
            group_id=group_id,
            role=GroupRole.OWNER,
        )

        return GroupResponse.model_validate(group)

    async def delete_group(self, id: int, current_user_id: int) -> None:
        """Delete a group by its ID.

        Group can only be deleted if the active period (if any) with transactions
        is already settled. This ensures data integrity for active settlements.

        ABAC Rule: Only owner can delete the group.

        Args:
            id: ID of the group to delete
            current_user_id: ID of the user performing the deletion

        Raises:
            NotFoundError: If group not found
            ForbiddenError: If user is not the owner (ABAC)
            BusinessRuleError: If active period with transactions is not settled
        """
        group = await self._group_repository.get_group_by_id(id)
        if not group:
            raise NotFoundError(_("Group %s not found") % id)

        # ABAC: Only owner can delete
        owner_id = await self._group_repository.get_group_owner(id)
        if owner_id != current_user_id:
            raise ForbiddenError(_("Only the group owner can delete the group"))

        # Check for active period with transactions
        active_period = await self._period_service.get_current_period_by_group_id(id)

        # Active period exists with transactions - must be settled first
        if active_period and active_period.transactions and not active_period.is_closed:
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
        await self._group_repository.delete_group(id)

    async def assign_group_role(
        self,
        group_id: int,
        user_id: int,
        role: GroupRole | None,
        assigned_by_user_id: int,
    ) -> None:
        """Assign a role to a member in a group, or remove them from the group.

        Handles all role assignment and membership operations:
        - Role assignment (owner, admin, member)
        - User addition (assigning member role to non-member)
        - User removal (assigning None role)

        ABAC Rules:
        - If assigning owner role: Only current owner can transfer (ABAC)
        - If assigning owner role: Automatically demotes old owner to member
        - For other roles: Only owner/admin can assign (checked via permission)
        - Removing user (role=None): Validates active period is settled

        Args:
            group_id: ID of the group
            user_id: ID of the user to assign role to
            role: Role to assign, or None to remove user from group
            assigned_by_user_id: ID of the user performing the assignment

        Raises:
            NotFoundError: If group/user not found, or user not in group (when appropriate)
            ForbiddenError: If user doesn't have permission to assign role
            ConflictError: If trying to add user who is already a member
            BusinessRuleError: If trying to remove user when active period is not settled
        """
        # Validate group and user exist
        await self._validate_group_and_user(group_id, user_id)

        # Get group and user for better error messages
        group = await self.get_group_by_id(group_id)
        user = await self._user_repository.get_user_by_id(user_id)
        assert group is not None and user is not None  # Type narrowing after validation

        # Handle role removal (user removal from group)
        if role is None:
            # Check if user is actually in the group
            if not await self._group_repository.check_if_user_is_in_group(group_id, user_id):
                raise NotFoundError(
                    _("User '%(user_name)s' is not a member of group '%(group_name)s'")
                    % {"user_name": user.name, "group_name": group.name}
                )

            # Check for active period with transactions (business rule)
            active_period = await self._period_service.get_current_period_by_group_id(group_id)
            if active_period and active_period.transactions and not active_period.is_closed:
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
            await self._authorization_service.assign_group_role(user_id, group_id, None)
            return

        # Get current owner for ABAC checks
        current_owner_id = await self._group_repository.get_group_owner(group_id)

        # Special handling for owner role assignment (ownership transfer)
        if role == GroupRole.OWNER:
            # ABAC: Only current owner can transfer ownership
            if current_owner_id != assigned_by_user_id:
                raise ForbiddenError(_("Only the current owner can transfer group ownership"))

            # Check if target user is a member (or allow if not, since they'll become owner)
            if not await self._group_repository.check_if_user_is_in_group(group_id, user_id):
                # If not a member, add them first (they'll become owner)
                await self._authorization_service.assign_group_role(
                    user_id=user_id,
                    group_id=group_id,
                    role=GroupRole.MEMBER,
                )

            # Demote old owner to member (if different from new owner)
            if current_owner_id and current_owner_id != user_id:
                await self._authorization_service.assign_group_role(
                    user_id=current_owner_id,
                    group_id=group_id,
                    role=GroupRole.MEMBER,
                )

            # Assign owner role to new user
            await self._authorization_service.assign_group_role(
                user_id=user_id,
                group_id=group_id,
                role=GroupRole.OWNER,
            )
            return

        # For non-owner roles, check permission
        has_permission = await self._authorization_service.has_permission(
            user_id=assigned_by_user_id,
            permission=Permission.GROUPS_WRITE,
            group_id=group_id,
        )
        if not has_permission:
            raise ForbiddenError(_("Permission denied: groups:write required to assign roles"))

        # Special handling for member role (adding user to group)
        if role == GroupRole.MEMBER:
            # Check for duplicate membership
            if await self._group_repository.check_if_user_is_in_group(group_id, user_id):
                raise ConflictError(
                    _("User '%(user_name)s' is already a member of group '%(group_name)s'")
                    % {"user_name": user.name, "group_name": group.name}
                )
            # User can join anytime - no period validation needed
            await self._authorization_service.assign_group_role(
                user_id=user_id,
                group_id=group_id,
                role=GroupRole.MEMBER,
            )
            return

        # For admin role (or any other role), user must already be a member
        if not await self._group_repository.check_if_user_is_in_group(group_id, user_id):
            raise NotFoundError(
                _("User '%(user_name)s' is not a member of group '%(group_name)s'")
                % {"user_name": user.name, "group_name": group.name}
            )

        # Assign the role
        await self._authorization_service.assign_group_role(
            user_id=user_id,
            group_id=group_id,
            role=role,
        )

    async def _validate_group_and_user(self, group_id: int, user_id: int) -> None:
        """Validate that a group and user exist.

        Args:
            group_id: ID of the group
            user_id: ID of the user

        Raises:
            NotFoundError: If group or user not found
        """
        group = await self._group_repository.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        user = await self._user_repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(_("User %s not found") % user_id)
