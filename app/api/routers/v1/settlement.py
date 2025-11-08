"""
API v1 router for Settlement endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.settlement import (
    SettlementBalanceResponse,
    SettlementPlanResponse,
    SettlementTransaction,
)
from app.api.schemas.period import MemberBalance
from app.services import settlement as settlement_service
import app.db as database

router = APIRouter(prefix="/settlement", tags=["settlement"])


@router.get("/balances", response_model=SettlementBalanceResponse)
def get_settlement_balances(
    db: Session = Depends(get_db),
):
    """
    Get final settlement balances for all members.
    
    Calculates total paid vs. total share to determine who owes money
    and who is owed money.
    
    Returns:
        List of member balances with descriptions
    """
    balances_dict = settlement_service.get_settlement_balances()
    # Convert balances from dict[str, str] to list[MemberBalance]
    balances = [
        MemberBalance(member_name=name, balance_description=desc)
        for name, desc in balances_dict.items()
    ]
    return SettlementBalanceResponse(balances=balances)


@router.get("/plan", response_model=SettlementPlanResponse)
def get_settlement_plan(
    period_id: int | None = Query(None, description="Period ID (defaults to current period)"),
    db: Session = Depends(get_db),
):
    """
    Get settlement plan without executing it.
    
    Calculates the transactions that would be created to settle balances.
    
    Args:
        period_id: Optional period ID (defaults to current period)
    
    Returns:
        List of settlement transactions that would be created
    """
    plan = settlement_service.get_settlement_plan(period_id)
    
    # Convert to SettlementTransaction schemas
    transactions = [
        SettlementTransaction(**tx) for tx in plan
    ]
    
    return SettlementPlanResponse(transactions=transactions)

