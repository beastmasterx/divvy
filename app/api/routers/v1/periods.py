"""
API v1 router for Period endpoints.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_period_service, get_settlement_service
from app.api.schemas import PeriodCreateRequest, PeriodResponse, PeriodUpdateRequest, SettlementPlanResponse
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.services import PeriodService, SettlementService

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("/", response_model=list[PeriodResponse])
def list_periods(
    period_service: PeriodService = Depends(get_period_service),
) -> Sequence[PeriodResponse]:
    """
    List all periods.
    """
    return period_service.get_all_periods()


@router.get("/{period_id}", response_model=PeriodResponse)
def get_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Get a specific period by its ID.
    """
    period = period_service.get_period_by_id(period_id)
    if not period:
        raise NotFoundError(_("Period %s not found") % period_id)
    return period


@router.post("/", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
def create_period(
    period: PeriodCreateRequest,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Create a new period.
    """
    return period_service.create_period(period)


@router.put("/{period_id}", response_model=PeriodResponse)
def update_period(
    period_id: int,
    period: PeriodUpdateRequest,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Update a specific period by its ID.
    """
    return period_service.update_period(period_id, period)


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
) -> None:
    """
    Delete a specific period by its ID.
    """
    period_service.delete_period(period_id)


@router.get("/{period_id}/balances", response_model=dict[int, int])
def get_balances(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
    settlement_service: SettlementService = Depends(get_settlement_service),
) -> dict[int, int]:
    """
    Get the balances for a specific period.
    """
    period = period_service.get_period_by_id(period_id)
    if not period:
        raise NotFoundError(_("Period %s not found") % period_id)
    return settlement_service.get_all_balances(period_id)


@router.get("/{period_id}/get-settlement-plan", response_model=list[SettlementPlanResponse])
def get_settlement_plan(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
    settlement_service: SettlementService = Depends(get_settlement_service),
) -> list[SettlementPlanResponse]:
    """
    Get the settlement plan for a specific period.
    """
    return settlement_service.get_settlement_plan(period_id)


@router.post("/{period_id}/apply-settlement-plan", status_code=status.HTTP_204_NO_CONTENT)
def apply_settlement_plan(
    period_id: int,
    settlement_service: SettlementService = Depends(get_settlement_service),
) -> None:
    """
    Apply the settlement plan and settle the period.
    """
    settlement_service.apply_settlement_plan(period_id)
