"""
API v1 router for Group endpoints.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_active_user, get_group_service, get_period_service
from app.api.dependencies.authorization import require_group_role
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import GroupRole
from app.schemas import (
    GroupRequest,
    GroupResponse,
    GroupRoleAssignmentRequest,
    PeriodResponse,
    UserResponse,
)
from app.services import GroupService, PeriodService

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(get_active_user)],
)


@router.get("/", response_model=list[GroupResponse])
async def get_groups_by_user_id(
    current_user: Annotated[UserResponse, Depends(get_active_user)],
    group_service: GroupService = Depends(get_group_service),
) -> Sequence[GroupResponse]:
    """
    List all groups that the current user is a member of.
    Requires groups:read permission.
    """
    return await group_service.get_groups_by_user_id(current_user.id)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group_by_id(
    group_id: int,
    _current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.MEMBER.value))],
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Get a specific group by its ID.
    Requires groups:read permission in the group.
    """
    group = await group_service.get_group_by_id(group_id)
    if not group:
        raise NotFoundError(_("Group %s not found") % group_id)
    return group


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group: GroupRequest,
    current_user: Annotated[UserResponse, Depends(get_active_user)],
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Create a new group.
    Any authenticated user can create a group (becomes owner automatically).
    """
    return await group_service.create_group(group, owner_id=current_user.id)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group: GroupRequest,
    _current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.OWNER.value))],
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Update a specific group by its ID.
    Requires groups:write permission in the group.
    """
    return await group_service.update_group(group_id, group)


@router.put("/{group_id}/users/{user_id}/role", status_code=status.HTTP_204_NO_CONTENT)
async def assign_group_role(
    group_id: int,
    user_id: int,
    request: GroupRoleAssignmentRequest,
    current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.OWNER.value))],
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """Assign a role to a user in a group, add them to the group, or remove them from the group.

    Requires groups:write permission. Special rules:
    - Assigning owner role: Only current owner can transfer (ABAC)
    - Assigning owner role: Automatically demotes old owner to member
    - Assigning member role: Adds user to group (if not already a member)
    - Assigning null role: Removes user from group (validates active period is settled)
    - Other roles: Only owner/admin can assign to existing members
    """
    await group_service.assign_group_role(
        group_id=group_id,
        user_id=user_id,
        role=request.role,
        assigned_by_user_id=current_user.id,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.OWNER.value))],
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Delete a specific group by its ID.
    Requires groups:delete permission. Only owner can delete (ABAC).
    """
    await group_service.delete_group(group_id, current_user_id=current_user.id)


@router.get("/{group_id}/periods", response_model=list[PeriodResponse])
async def get_periods(
    group_id: int,
    _current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.MEMBER.value))],
    period_service: PeriodService = Depends(get_period_service),
) -> list[PeriodResponse]:
    """
    Get all periods for a specific group.
    """
    periods = await period_service.get_periods_by_group_id(group_id)
    return [PeriodResponse.model_validate(period) for period in periods]


@router.get("/{group_id}/periods/current", response_model=PeriodResponse)
async def get_current_period(
    group_id: int,
    _current_user: Annotated[UserResponse, Depends(require_group_role(GroupRole.MEMBER.value))],
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Get the current active period for a specific group.
    """
    period = await period_service.get_current_period_by_group_id(group_id)
    if not period:
        raise NotFoundError(_("No current active period found for group %s") % group_id)
    return PeriodResponse.model_validate(period)
