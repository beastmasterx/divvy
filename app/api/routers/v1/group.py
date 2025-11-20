"""
API v1 router for Group endpoints.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_group_service
from app.api.schemas import GroupRequest, GroupResponse
from app.services import GroupService

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[GroupResponse])
def list_groups(
    group_service: GroupService = Depends(get_group_service),
):
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
):
    """
    Get a specific group by its ID.
    """
    group = group_service.get_group_by_id(group_id)
    return GroupResponse.model_validate(group)


@router.post("/", response_model=GroupResponse)
def create_group(
    group: GroupRequest,
    group_service: GroupService = Depends(get_group_service),
):
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
):
    """
    Update a specific group by its ID.
    """
    updated_group = group_service.update_group(group_id, group)
    return GroupResponse.model_validate(updated_group)


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
):
    """
    Delete a specific group by its ID.
    """
    group_service.delete_group(group_id)
