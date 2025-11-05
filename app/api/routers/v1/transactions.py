"""
API v1 router for Transaction endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.transaction import (
    ExpenseCreate,
    DepositCreate,
    RefundCreate,
    TransactionMessageResponse,
)
from app.services import transaction as transaction_service
import app.db as database

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/expenses", response_model=TransactionMessageResponse, status_code=201)
def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new expense.
    
    Supports three expense types:
    - shared: Split among all members, no individual payer
    - personal: Only affects the payer (not split)
    - individual: Split among all members, payer gets credit
    
    Returns:
        Success or error message
    """
    # Handle expense_type if provided
    is_personal = expense.is_personal
    payer_name = expense.payer_name
    
    # If expense_type is provided, override is_personal
    if expense.expense_type:
        if expense.expense_type in ("s", "shared"):
            payer_name = database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
            is_personal = False
        elif expense.expense_type in ("p", "personal"):
            is_personal = True
        else:  # individual
            is_personal = False
    
    result = transaction_service.record_expense(
        description=expense.description,
        amount_str=expense.amount,
        payer_name=payer_name,
        category_name=expense.category_name,
        is_personal=is_personal,
    )
    
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return TransactionMessageResponse(message=result)


@router.post("/deposits", response_model=TransactionMessageResponse, status_code=201)
def create_deposit(
    deposit: DepositCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new deposit.
    
    Returns:
        Success or error message
    """
    result = transaction_service.record_deposit(
        description=deposit.description,
        amount_str=deposit.amount,
        payer_name=deposit.payer_name,
    )
    
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return TransactionMessageResponse(message=result)


@router.post("/refunds", response_model=TransactionMessageResponse, status_code=201)
def create_refund(
    refund: RefundCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new refund.
    
    Returns:
        Success or error message
    """
    result = transaction_service.record_refund(
        description=refund.description,
        amount_str=refund.amount,
        member_name=refund.member_name,
    )
    
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return TransactionMessageResponse(message=result)

