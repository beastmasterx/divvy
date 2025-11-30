"""
API v1 router for Group endpoints.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.api.dependencies.authz import requires_group_role
from app.api.dependencies.authz.group import (
    requires_non_owner_role_assignment,
    requires_settled_active_period,
    verifies_target_user_membership,
)
from app.api.dependencies.services import get_group_service, get_period_service
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import GroupRole
from app.schemas import (
    GroupRequest,
    GroupResponse,
    PeriodRequest,
    PeriodResponse,
    UserResponse,
)
from app.services import GroupService, PeriodService

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[GroupResponse])
async def get_groups_by_user_id(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    group_service: GroupService = Depends(get_group_service),
) -> Sequence[GroupResponse]:
    """
    List all groups that the current user is a member of.
    """
    return await group_service.get_groups_by_user_id(current_user.id)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group_by_id(
    group_id: int,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.MEMBER))],
) -> GroupResponse:
    """
    Get a specific group by its ID.
    Requires group membership.
    """
    group = await group_service.get_group_by_id(group_id)
    if not group:
        raise NotFoundError(_("Group %s not found") % group_id)
    return group


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group: GroupRequest,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> GroupResponse:
    """
    Create a new group.
    Any authenticated user can create a group (becomes owner automatically).
    """
    return await group_service.create_group(group, owner_id=current_user.id)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    request: GroupRequest,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER, GroupRole.ADMIN))],
) -> GroupResponse:
    """
    Update a specific group by its ID.
    Requires group owner or admin role.
    """
    return await group_service.update_group(group_id, request)


@router.put("/{group_id}/users/{user_id}", response_model=GroupResponse)
async def transfer_group_owner(
    group_id: int,
    user_id: int,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER))],
    _verifies_target_user_membership: Annotated[None, Depends(verifies_target_user_membership)],
) -> GroupResponse:
    """Transfer the ownership of a specific group by its ID to a new owner."""
    return await group_service.transfer_group_owner(group_id, user_id)


@router.delete("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER))],
    _verifies_target_user_membership: Annotated[None, Depends(verifies_target_user_membership)],
    _requires_settled_active_period: Annotated[None, Depends(requires_settled_active_period)],
) -> None:
    """Remove a user from a group."""
    await group_service.remove_user_from_group(group_id, user_id)


@router.put("/{group_id}/users/{user_id}/{role}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_group_role(
    group_id: int,
    user_id: int,
    role: GroupRole,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER, GroupRole.ADMIN))],
    _requires_non_owner_role_assignment: Annotated[None, Depends(requires_non_owner_role_assignment)],
) -> None:
    """Assign a role to a user in a group."""
    await group_service.assign_group_role(group_id=group_id, user_id=user_id, role=role)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    group_service: Annotated[GroupService, Depends(get_group_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER))],
    _requires_settled_active_period: Annotated[None, Depends(requires_settled_active_period)],
) -> None:
    """
    Delete a specific group by its ID.
    Requires group owner role.
    """
    await group_service.delete_group(group_id)


@router.get("/{group_id}/periods", response_model=list[PeriodResponse])
async def get_periods(
    group_id: int,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.MEMBER))],
) -> list[PeriodResponse]:
    """
    Get all periods for a specific group.
    """
    periods = await period_service.get_periods_by_group_id(group_id)
    return [PeriodResponse.model_validate(period) for period in periods]


@router.get("/{group_id}/periods/current", response_model=PeriodResponse)
async def get_current_period(
    group_id: int,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.MEMBER))],
) -> PeriodResponse:
    """
    Get the current active period for a specific group.
    """
    period = await period_service.get_active_period_by_group_id(group_id)
    if not period:
        raise NotFoundError(_("No current active period found for group %s") % group_id)
    return PeriodResponse.model_validate(period)


@router.post("/{group_id}/periods", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    group_id: int,
    period: PeriodRequest,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER, GroupRole.ADMIN))],
) -> PeriodResponse:
    """
    Create a new period.
    Requires owner or admin role in the group specified in the request.
    """
    return await period_service.create_period(group_id, period)
