"""
Pydantic schemas for Period API endpoints.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class PeriodBase(BaseModel):
    """Base period schema."""
    name: str = Field(..., description="Period name", min_length=1)


class PeriodCreate(PeriodBase):
    """Schema for creating a new period."""
    pass


class PeriodResponse(BaseModel):
    """Schema for period response."""
    id: int
    name: str
    start_date: datetime
    end_date: datetime | None
    is_settled: bool
    settled_date: datetime | None

    class Config:
        from_attributes = True


class PeriodSummaryResponse(BaseModel):
    """Schema for period summary response."""
    period: dict
    transactions: list[dict]
    balances: dict[str, str]
    totals: dict
    transaction_count: int


class PeriodSettleRequest(BaseModel):
    """Schema for settling a period."""
    period_name: str | None = Field(None, description="Name for the new period (auto-generated if not provided)")


class PeriodSettleResponse(BaseModel):
    """Schema for period settlement response."""
    message: str

