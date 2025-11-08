"""
Pydantic schemas for Transaction API endpoints.
"""
from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    """Base transaction schema."""
    description: str | None = Field(None, description="Transaction description")
    amount: str = Field(..., description="Amount as dollar string (e.g., '123.45')")


class ExpenseCreate(TransactionBase):
    """Schema for creating an expense."""
    payer_name: str = Field(..., description="Name of the member paying")
    category_name: str = Field(..., description="Expense category name")
    is_personal: bool = Field(False, description="Whether this is a personal expense (not split)")
    expense_type: str | None = Field(
        None,
        description="Expense type: 'shared', 'personal', or 'individual' (default: 'individual')"
    )


class DepositCreate(TransactionBase):
    """Schema for creating a deposit."""
    payer_name: str = Field(..., description="Name of the member making the deposit")


class RefundCreate(TransactionBase):
    """Schema for creating a refund."""
    member_name: str = Field(..., description="Name of the member to refund")


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    model_config = {"from_attributes": True}
    
    id: int
    transaction_type: str
    description: str | None
    amount: int  # Amount in cents
    payer_id: int | None
    payer_name: str | None
    category_id: int | None
    category_name: str | None
    period_id: int
    is_personal: bool
    timestamp: str


class TransactionMessageResponse(BaseModel):
    """Schema for transaction operation result messages."""
    message: str

