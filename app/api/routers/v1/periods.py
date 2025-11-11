"""
API v1 router for Period endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import app.db as database
from app.api.dependencies import get_db
from app.api.schemas.period import (
    MemberBalance,
    PeriodResponse,
    PeriodSettleRequest,
    PeriodSettleResponse,
    PeriodSummaryResponse,
    PeriodTotalsResponse,
)
from app.api.schemas.transaction import TransactionResponse
from app.services import period as period_service

router = APIRouter(prefix="/periods", tags=["periods"])


@router.get("/current", response_model=PeriodResponse)
def get_current_period(
    db: Session = Depends(get_db),
):
    """
    Get the current active period.

    Returns:
        Current period details
    """
    current_period = database.get_current_period()
    if not current_period:
        raise HTTPException(status_code=404, detail="No active period found")

    return PeriodResponse.model_validate(current_period)


@router.get("/current/summary", response_model=PeriodSummaryResponse)
def get_current_period_summary(
    db: Session = Depends(get_db),
):
    """
    Get comprehensive summary of the current period.

    Returns:
        Period summary with transactions, balances, and totals
    """
    summary = period_service.get_period_summary()
    if not summary:
        raise HTTPException(status_code=404, detail="No active period found")

    # Convert balances from dict[str, str] to list[MemberBalance]
    balances = [
        MemberBalance(member_name=name, balance_description=desc)
        for name, desc in summary["balances"].items()
    ]

    return PeriodSummaryResponse(
        period=PeriodResponse.model_validate(summary["period"]),
        transactions=[TransactionResponse.model_validate(tx) for tx in summary["transactions"]],
        balances=balances,
        totals=PeriodTotalsResponse(**summary["totals"]),
        transaction_count=summary["transaction_count"],
    )


@router.get("/{period_id}", response_model=PeriodResponse)
def get_period(
    period_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific period by ID.

    Args:
        period_id: Period ID

    Returns:
        Period details
    """
    period_data = database.get_period_by_id(period_id)
    if not period_data:
        raise HTTPException(status_code=404, detail=f"Period {period_id} not found")

    return PeriodResponse.model_validate(period_data)


@router.get("/{period_id}/summary", response_model=PeriodSummaryResponse)
def get_period_summary(
    period_id: int,
    db: Session = Depends(get_db),
):
    """
    Get comprehensive summary of a specific period.

    Args:
        period_id: Period ID

    Returns:
        Period summary with transactions, balances, and totals
    """
    summary = period_service.get_period_summary(period_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Period {period_id} not found")

    # Convert balances from dict[str, str] to list[MemberBalance]
    balances = [
        MemberBalance(member_name=name, balance_description=desc)
        for name, desc in summary["balances"].items()
    ]

    return PeriodSummaryResponse(
        period=PeriodResponse.model_validate(summary["period"]),
        transactions=[TransactionResponse.model_validate(tx) for tx in summary["transactions"]],
        balances=balances,
        totals=PeriodTotalsResponse(**summary["totals"]),
        transaction_count=summary["transaction_count"],
    )


@router.get("/{period_id}/balances", response_model=dict)
def get_period_balances(
    period_id: int,
    db: Session = Depends(get_db),
):
    """
    Get balances for a specific period.

    Args:
        period_id: Period ID

    Returns:
        Dictionary of member names to balance descriptions
    """
    balances = period_service.get_period_balances(period_id)
    if not balances:
        raise HTTPException(
            status_code=404, detail=f"Period {period_id} not found or has no balances"
        )

    return balances


@router.post("/current/settle", response_model=PeriodSettleResponse)
def settle_current_period(
    request: PeriodSettleRequest,
    db: Session = Depends(get_db),
):
    """
    Settle the current period and create a new period.

    Args:
        request: Settlement request with optional new period name

    Returns:
        Success or error message
    """
    result = period_service.settle_current_period(request.period_name)

    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)

    return PeriodSettleResponse(message=result)
