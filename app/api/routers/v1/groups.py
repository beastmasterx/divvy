"""
API v1 router for Group endpoints.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user, get_group_service
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import User
from app.schemas import GroupRequest, GroupResponse, PeriodResponse
from app.services import GroupService

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=list[GroupResponse])
async def list_groups(
    group_service: GroupService = Depends(get_group_service),
) -> Sequence[GroupResponse]:
    """
    List all periods.

    Returns:
        List of all periods, ordered by start_date descending
    """
    return await group_service.get_all_groups()


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Get a specific group by its ID.
    """
    group = await group_service.get_group_by_id(group_id)
    if not group:
        raise NotFoundError(_("Group %s not found") % group_id)
    return group


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group: GroupRequest,
    current_user: User = Depends(get_current_user),
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Create a new group.
    """
    return await group_service.create_group(group, owner_id=current_user.id)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group: GroupRequest,
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Update a specific group by its ID.
    """
    return await group_service.update_group(group_id, group)


@router.put("/{group_id}/owner/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_group_owner(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Update the owner of a specific group by its ID.
    """
    await group_service.update_group_owner(group_id, user_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Delete a specific group by its ID.
    """
    await group_service.delete_group(group_id)


@router.post("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_group(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Add a user to a specific group.
    """
    await group_service.add_user_to_group(group_id, user_id)


@router.delete("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_group(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Remove a user from a specific group.
    """
    await group_service.remove_user_from_group(group_id, user_id)


@router.get("/{group_id}/periods", response_model=list[PeriodResponse])
async def get_periods(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> list[PeriodResponse]:
    """
    Get all periods for a specific group.
    """
    periods = await group_service.get_periods_by_group_id(group_id)
    return [PeriodResponse.model_validate(period) for period in periods]


@router.get("/{group_id}/periods/current", response_model=PeriodResponse)
async def get_current_period(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> PeriodResponse:
    """
    Get the current active period for a specific group.
    """
    period = await group_service.get_current_period_by_group_id(group_id)
    if not period:
        raise NotFoundError(_("No current active period found for group %s") % group_id)
    return PeriodResponse.model_validate(period)
