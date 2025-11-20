from datetime import datetime

from pydantic import BaseModel, Field

from app.models import SplitKind, TransactionKind


class TransactionRequest(BaseModel):
    """Schema for transaction request."""

    description: str = Field(..., description="Transaction description")
    amount: int = Field(..., description="Transaction amount in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    expense_shares: list[ExpenseShareRequest] = Field(..., description="Expense shares for the transaction")


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    id: int = Field(..., description="ID of the transaction")
    description: str = Field(..., description="Transaction description")
    amount: int = Field(..., description="Transaction amount in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    payer_name: str = Field(..., description="Name of the user who paid the transaction")
    category_name: str = Field(..., description="Name of the category of the transaction")
    period_name: str = Field(..., description="Name of the period of the transaction")
    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    expense_shares: list[ExpenseShareResponse] = Field(..., description="Expense shares for the transaction")

    created_at: datetime = Field(..., description="Transaction created at")
    updated_at: datetime = Field(..., description="Transaction updated at")

    created_by: int = Field(..., description="Transaction created by")
    updated_by: int = Field(..., description="Transaction updated by")


class ExpenseShareRequest(BaseModel):
    """Schema for share request."""

    user_id: int = Field(..., description="ID of the user who shared the transaction")
    transaction_id: int = Field(..., description="ID of the transaction who shared the transaction")
    share_amount: int = Field(..., description="Amount of the share in cents")
    share_percentage: float = Field(..., description="Percentage of the share")


class ExpenseShareResponse(BaseModel):
    """Schema for share response."""

    user_id: int = Field(..., description="ID of the user who shared the transaction")
    transaction_id: int = Field(..., description="ID of the transaction who shared the transaction")
    share_amount: int = Field(..., description="Amount of the share in cents")
    share_percentage: float = Field(..., description="Percentage of the share")


class SettlementPlanResponse(BaseModel):
    """Schema for settlement plan response."""

    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    amount: int = Field(..., description="Amount of the transaction in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    description: str = Field(..., description="Description of the transaction")
    payer_name: str = Field(..., description="Name of the user who paid the transaction")
    category_name: str = Field(..., description="Name of the category of the transaction")
    period_name: str = Field(..., description="Name of the period of the transaction")
