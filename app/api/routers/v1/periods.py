"""
API v1 router for Period endpoints.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.dependencies.authz import requires_group_role, requires_group_role_for_period
from app.api.dependencies.db import get_serializable_db
from app.api.dependencies.services import (
    get_period_service,
    get_serializable_settlement_service,
    get_settlement_service,
    get_transaction_service,
)
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import GroupRole
from app.schemas import PeriodRequest, PeriodResponse, SettlementResponse, TransactionResponse, UserResponse
from app.services import PeriodService, SettlementService, TransactionService

router = APIRouter(prefix="/periods", tags=["periods"], dependencies=[Depends(get_current_user)])


@router.get("/{period_id}", response_model=PeriodResponse)
async def get_period(
    period_id: int,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.MEMBER))],
) -> PeriodResponse:
    """
    Get a specific period by its ID.
    Requires group membership for the period's group.
    """
    period = await period_service.get_period_by_id(period_id)
    if not period:
        raise NotFoundError(_("Period %s not found") % period_id)
    return period


@router.post("/", response_model=PeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_period(
    group_id: int,
    period: PeriodRequest,
    _current_user: Annotated[UserResponse, Depends(requires_group_role(GroupRole.OWNER, GroupRole.ADMIN))],
    period_service: Annotated[PeriodService, Depends(get_period_service)],
) -> PeriodResponse:
    """
    Create a new period.
    Requires owner or admin role in the group specified in the request.
    """
    return await period_service.create_period(group_id, period)


@router.put("/{period_id}/close", response_model=PeriodResponse)
async def close_period(
    period_id: int,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.OWNER, GroupRole.ADMIN))],
) -> PeriodResponse:
    """
    Close a specific period by its ID.
    Requires owner or admin role in the period's group.
    """
    return await period_service.close_period(period_id)


@router.put("/{period_id}", response_model=PeriodResponse)
async def update_period(
    period_id: int,
    request: PeriodRequest,
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.OWNER, GroupRole.ADMIN))],
) -> PeriodResponse:
    """
    Update a specific period by its ID.
    Requires owner or admin role in the period's group.
    """
    return await period_service.update_period_name(period_id, request.name)


@router.get("/{period_id}/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    period_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.MEMBER))],
) -> Sequence[TransactionResponse]:
    """
    Get the transactions for a specific period.
    Requires group membership for the period's group.
    """
    return await transaction_service.get_transactions_by_period_id(period_id)


@router.get("/{period_id}/balances", response_model=dict[int, int])
async def get_balances(
    period_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.MEMBER))],
) -> dict[int, int]:
    """
    Get the balances for a specific period.
    Requires group membership for the period's group.
    """
    return await transaction_service.get_all_balances(period_id)


@router.get("/{period_id}/get-settlement-plan", response_model=list[SettlementResponse])
async def get_settlement_plan(
    period_id: int,
    settlement_service: Annotated[SettlementService, Depends(get_settlement_service)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.MEMBER))],
) -> Sequence[SettlementResponse]:
    """
    Get the settlement plan for a specific period.
    Requires group membership for the period's group.
    """
    return await settlement_service.get_settlement_plan(period_id)


@router.post("/{period_id}/apply-settlement-plan", status_code=status.HTTP_204_NO_CONTENT)
async def apply_settlement_plan(
    period_id: int,
    settlement_service: Annotated[SettlementService, Depends(get_serializable_settlement_service)],
    db: Annotated[AsyncSession, Depends(get_serializable_db)],
    _current_user: Annotated[UserResponse, Depends(requires_group_role_for_period(GroupRole.OWNER, GroupRole.ADMIN))],
) -> None:
    """
    Apply the settlement plan and settle the period.
    Requires owner or admin role in the period's group.
    """
    await settlement_service.apply_settlement_plan(period_id, db)
