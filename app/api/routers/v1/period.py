"""
API v1 router for Period endpoints.
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_period_service
from app.api.schemas import PeriodRequest, PeriodResponse
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.services import PeriodService

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("/", response_model=list[PeriodResponse])
def list_periods(
    period_service: PeriodService = Depends(get_period_service),
):
    """
    List all periods.
    """
    periods = period_service.get_all_periods()
    return [PeriodResponse.model_validate(period) for period in periods]


@router.get("/{period_id}", response_model=PeriodResponse)
def get_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
):
    """
    Get a specific period by its ID.
    """
    period = period_service.get_period_by_id(period_id)
    if not period:
        raise NotFoundError(_("Period %s not found") % period_id)
    return PeriodResponse.model_validate(period)


@router.post("/", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
def create_period(
    period: PeriodRequest,
    period_service: PeriodService = Depends(get_period_service),
):
    """
    Create a new period.
    """
    created_period = period_service.create_period(period)
    return PeriodResponse.model_validate(created_period)


@router.put("/{period_id}", response_model=PeriodResponse)
def update_period(
    period_id: int,
    period: PeriodRequest,
    period_service: PeriodService = Depends(get_period_service),
):
    """
    Update a specific period by its ID.
    """
    updated_period = period_service.update_period(period_id, period)
    return PeriodResponse.model_validate(updated_period)


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
):
    """
    Delete a specific period by its ID.
    """
    period_service.delete_period(period_id)
