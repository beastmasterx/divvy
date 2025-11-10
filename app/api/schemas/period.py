"""
Pydantic schemas for Period API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.transaction import TransactionResponse


class PeriodBase(BaseModel):
    """Base period schema."""

    name: str = Field(..., description="Period name", min_length=1)


class PeriodCreate(PeriodBase):
    """Schema for creating a new period."""

    pass


class PeriodResponse(BaseModel):
    """Schema for period response."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    start_date: datetime
    end_date: datetime | None
    is_settled: bool
    settled_date: datetime | None


class MemberBalance(BaseModel):
    """Schema for a member's balance in a period."""

    member_name: str = Field(..., description="Member name")
    balance_description: str = Field(
        ...,
        description="Formatted balance description (e.g., 'Is owed $123.45', 'Owes $67.89', or 'Settled')",
    )


class PeriodTotalsResponse(BaseModel):
    """Schema for period totals."""

    deposits: int = Field(..., description="Total deposits in cents")
    deposits_formatted: str = Field(..., description="Total deposits formatted as dollars")
    expenses: int = Field(..., description="Total expenses in cents")
    expenses_formatted: str = Field(..., description="Total expenses formatted as dollars")
    net: int = Field(..., description="Net amount (deposits - expenses) in cents")
    net_formatted: str = Field(..., description="Net amount formatted as dollars")


class PeriodSummaryResponse(BaseModel):
    """Schema for period summary response."""

    period: PeriodResponse
    transactions: list[TransactionResponse]
    balances: list[MemberBalance]
    totals: PeriodTotalsResponse
    transaction_count: int


class PeriodSettleRequest(BaseModel):
    """Schema for settling a period."""

    period_name: str | None = Field(
        None, description="Name for the new period (auto-generated if not provided)"
    )


class PeriodSettleResponse(BaseModel):
    """Schema for period settlement response."""

    message: str
