from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import Group, GroupRole
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

    async def is_member(self, group_id: int, user_id: int) -> bool:
        """Check if a user is a member of a specific group."""
        return await self._group_repository.is_member(group_id, user_id)

    async def is_owner(self, group_id: int, user_id: int) -> bool:
        """Check if a user is the owner of a specific group."""
        return await self._group_repository.is_owner(group_id, user_id)

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

    async def transfer_group_owner(self, group_id: int, new_owner_id: int) -> GroupResponse:
        """Transfer the ownership of a specific group by its ID to a new owner.

        Args:
            group_id: ID of the group to update
            new_owner_id: ID of the user to set as new owner

        Returns:
            Updated Group response DTO
        """
        # Fetch from repository
        group = await self.get_group_by_id(group_id)
        if not group:
            raise NotFoundError(_("Group %s not found") % group_id)

        # Check if user is a member
        if not await self.is_member(group_id, new_owner_id):
            raise NotFoundError(_("User %s is not a member of group %s") % (new_owner_id, group.name))

        # Get current owner and demote to member if different from new owner
        current_owner_id = await self._authorization_service.get_group_owner(group_id)
        if current_owner_id and current_owner_id != new_owner_id:
            await self._authorization_service.assign_group_role(
                user_id=current_owner_id,
                group_id=group_id,
                role=GroupRole.MEMBER,
            )

        # Assign owner role to new user
        await self._authorization_service.assign_group_role(
            user_id=new_owner_id,
            group_id=group_id,
            role=GroupRole.OWNER,
        )

        return group

    async def remove_user_from_group(self, group_id: int, user_id: int) -> None:
        """Remove a user from a group.

        Args:
            group_id: ID of the group
            user_id: ID of the user to remove from the group
        """
        await self._authorization_service.assign_group_role(user_id, group_id, None)

    async def assign_group_role(self, group_id: int, user_id: int, role: GroupRole) -> None:
        """Assign a role to a member in a group.

        Args:
            group_id: ID of the group
            user_id: ID of the user to assign role to
            role: Role to assign
        """
        # Assign the role
        await self._authorization_service.assign_group_role(
            user_id=user_id,
            group_id=group_id,
            role=role,
        )

    async def delete_group(self, id: int) -> None:
        """Delete a group by its ID.

        Group can only be deleted if the active period (if any) with transactions
        is already settled. This ensures data integrity for active settlements.

        Args:
            id: ID of the group to delete

        Raises:
            NotFoundError: If group not found
            BusinessRuleError: If active period with transactions is not settled
        """
        group = await self.get_group_by_id(id)
        if not group:
            raise NotFoundError(_("Group %s not found") % id)

        await self._group_repository.delete_group(id)

    async def has_active_period_with_transactions(self, group_id: int) -> bool:
        """Check if a group has an active period with transactions."""
        active_period = await self._period_service.get_active_period_by_group_id(group_id)
        if not active_period or active_period.is_closed:
            return False
        return len(active_period.transactions) > 0
