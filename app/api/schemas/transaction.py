from datetime import datetime

from pydantic import BaseModel, Field

from app.models import SplitKind, TransactionKind


class TransactionRequest(BaseModel):
    """Schema for transaction request."""

    description: str | None = Field(default=None, description="Transaction description")
    amount: int = Field(..., description="Transaction amount in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    expense_shares: list[ExpenseShareRequest] | None = Field(
        default=None, description="Expense shares for the transaction"
    )


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="ID of the transaction")
    description: str | None = Field(default=None, description="Transaction description")
    amount: int = Field(..., description="Transaction amount in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    payer_name: str | None = Field(default=None, description="Name of the user who paid the transaction")
    category_name: str | None = Field(default=None, description="Name of the category of the transaction")
    period_name: str | None = Field(default=None, description="Name of the period of the transaction")
    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    expense_shares: list[ExpenseShareResponse] | None = Field(
        default=None, description="Expense shares for the transaction"
    )

    created_at: datetime | None = Field(default=None, description="Transaction created at")
    updated_at: datetime | None = Field(default=None, description="Transaction updated at")

    created_by: int | None = Field(default=None, description="Transaction created by")
    updated_by: int | None = Field(default=None, description="Transaction updated by")


class ExpenseShareRequest(BaseModel):
    """Schema for share request."""

    user_id: int = Field(..., description="ID of the user who shared the transaction")
    transaction_id: int = Field(..., description="ID of the transaction who shared the transaction")
    share_amount: int | None = Field(default=None, description="Amount of the share in cents")
    share_percentage: float | None = Field(default=None, description="Percentage of the share")


class ExpenseShareResponse(BaseModel):
    """Schema for share response."""

    model_config = {"from_attributes": True}

    user_id: int = Field(..., description="ID of the user who shared the transaction")
    transaction_id: int = Field(..., description="ID of the transaction who shared the transaction")
    share_amount: int | None = Field(default=None, description="Amount of the share in cents")
    share_percentage: float | None = Field(default=None, description="Percentage of the share")


class SettlementPlanResponse(BaseModel):
    """Schema for settlement plan response."""

    model_config = {"from_attributes": True}

    transaction_kind: TransactionKind = Field(..., description="Kind of transaction")
    amount: int = Field(..., description="Amount of the transaction in cents")
    payer_id: int = Field(..., description="ID of the user who paid the transaction")
    period_id: int = Field(..., description="ID of the period of the transaction")
    category_id: int = Field(..., description="ID of the category of the transaction")
    split_kind: SplitKind = Field(..., description="Kind of split")
    description: str | None = Field(default=None, description="Description of the transaction")
    payer_name: str = Field(..., description="Name of the user who paid the transaction")
    category_name: str = Field(..., description="Name of the category of the transaction")
    period_name: str = Field(..., description="Name of the period of the transaction")
