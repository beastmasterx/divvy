"""
API v1 router for Group endpoints.
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_group_service
from app.api.schemas import GroupRequest, GroupResponse, PeriodResponse
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.services import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[GroupResponse])
def list_groups(
    group_service: GroupService = Depends(get_group_service),
) -> list[GroupResponse]:
    """
    List all periods.

    Returns:
        List of all periods, ordered by start_date descending
    """
    groups = group_service.get_all_groups()
    return [GroupResponse.model_validate(group) for group in groups]


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Get a specific group by its ID.
    """
    group = group_service.get_group_by_id(group_id)
    if not group:
        raise NotFoundError(_("Group %s not found") % group_id)
    return GroupResponse.model_validate(group)


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group: GroupRequest,
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Create a new group.
    """
    created_group = group_service.create_group(group)
    return GroupResponse.model_validate(created_group)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group: GroupRequest,
    group_service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    """
    Update a specific group by its ID.
    """
    updated_group = group_service.update_group(group_id, group)
    return GroupResponse.model_validate(updated_group)


@router.put("/{group_id}/owner/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_group_owner(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Update the owner of a specific group by its ID.
    """
    group_service.update_group_owner(group_id, user_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Delete a specific group by its ID.
    """
    group_service.delete_group(group_id)


@router.post("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_user_to_group(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Add a user to a specific group.
    """
    group_service.add_user_to_group(group_id, user_id)


@router.delete("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_group(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Remove a user from a specific group.
    """
    group_service.remove_user_from_group(group_id, user_id)


@router.get("/{group_id}/periods", response_model=list[PeriodResponse])
def get_periods(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> list[PeriodResponse]:
    """
    Get all periods for a specific group.
    """
    periods = group_service.get_periods_by_group_id(group_id)
    return [PeriodResponse.model_validate(period) for period in periods]


@router.get("/{group_id}/periods/current", response_model=PeriodResponse)
def get_current_period(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> PeriodResponse:
    """
    Get the current active period for a specific group.
    """
    period = group_service.get_current_period_by_group_id(group_id)
    if not period:
        raise NotFoundError(_("No current active period found for group %s") % group_id)
    return PeriodResponse.model_validate(period)
