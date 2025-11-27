"""
API v1 router for Period endpoints.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_period_service,
    get_serializable_db,
    get_serializable_settlement_service,
    get_settlement_service,
)
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.schemas import PeriodCreateRequest, PeriodResponse, PeriodUpdateRequest, SettlementPlanResponse
from app.services import PeriodService, SettlementService

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("/", response_model=list[PeriodResponse])
async def list_periods(
    period_service: PeriodService = Depends(get_period_service),
) -> Sequence[PeriodResponse]:
    """
    List all periods.
    """
    return await period_service.get_all_periods()


@router.get("/{period_id}", response_model=PeriodResponse)
async def get_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Get a specific period by its ID.
    """
    period = await period_service.get_period_by_id(period_id)
    if not period:
        raise NotFoundError(_("Period %s not found") % period_id)
    return period


@router.post("/", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    period: PeriodCreateRequest,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Create a new period.
    """
    return await period_service.create_period(period)


@router.put("/{period_id}", response_model=PeriodResponse)
async def update_period(
    period_id: int,
    period: PeriodUpdateRequest,
    period_service: PeriodService = Depends(get_period_service),
) -> PeriodResponse:
    """
    Update a specific period by its ID.
    """
    return await period_service.update_period(period_id, period)


@router.delete("/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_period(
    period_id: int,
    period_service: PeriodService = Depends(get_period_service),
) -> None:
    """
    Delete a specific period by its ID.
    """
    await period_service.delete_period(period_id)


@router.get("/{period_id}/balances", response_model=dict[int, int])
async def get_balances(
    period_id: int,
    settlement_service: SettlementService = Depends(get_settlement_service),
) -> dict[int, int]:
    """
    Get the balances for a specific period.
    """
    return await settlement_service.get_all_balances(period_id)


@router.get("/{period_id}/get-settlement-plan", response_model=list[SettlementPlanResponse])
async def get_settlement_plan(
    period_id: int,
    settlement_service: SettlementService = Depends(get_settlement_service),
) -> list[SettlementPlanResponse]:
    """
    Get the settlement plan for a specific period.
    """
    return await settlement_service.get_settlement_plan(period_id)


@router.post("/{period_id}/apply-settlement-plan", status_code=status.HTTP_204_NO_CONTENT)
async def apply_settlement_plan(
    period_id: int,
    settlement_service: SettlementService = Depends(get_serializable_settlement_service),
    db: AsyncSession = Depends(get_serializable_db),
) -> None:
    """
    Apply the settlement plan and settle the period.
    """
    await settlement_service.apply_settlement_plan(period_id, db)
