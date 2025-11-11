"""
API v1 router for System endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.period import (
    MemberBalance,
    PeriodResponse,
    PeriodSummaryResponse,
    PeriodTotalsResponse,
)
from app.api.schemas.system import (
    SystemMemberInfo,
    SystemStatusResponse,
    TransactionCounts,
)
from app.api.schemas.transaction import TransactionResponse
from app.services import system as system_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    db: Session = Depends(get_db),
):
    """
    Get comprehensive system status.

    Includes:
    - Member information (active/inactive, remainder flags)
    - Settlement balances
    - Transaction statistics
    - Current period information

    Returns:
        Complete system status
    """
    status = system_service.get_system_status()

    # Convert to proper Pydantic models
    period_summary = None
    if status["period_summary"]:
        period_summary = PeriodSummaryResponse(
            period=PeriodResponse.model_validate(status["period_summary"]["period"]),
            transactions=[
                TransactionResponse.model_validate(tx) for tx in status["period_summary"]["transactions"]
            ],
            balances=[
                MemberBalance(member_name=name, balance_description=desc)
                for name, desc in status["period_summary"]["balances"].items()
            ],
            totals=PeriodTotalsResponse(**status["period_summary"]["totals"]),
            transaction_count=status["period_summary"]["transaction_count"],
        )

    return SystemStatusResponse(
        current_period=(
            PeriodResponse.model_validate(status["current_period"]) if status["current_period"] else None
        ),
        period_summary=period_summary,
        total_members=status["total_members"],
        active_members_count=status["active_members_count"],
        inactive_members_count=status["inactive_members_count"],
        members=[SystemMemberInfo(**member) for member in status["members"]],
        transaction_counts=TransactionCounts(**status["transaction_counts"]),
    )
