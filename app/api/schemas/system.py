"""
Pydantic schemas for System API endpoints.
"""

from pydantic import BaseModel, Field

from app.api.schemas.period import PeriodResponse, PeriodSummaryResponse


class SystemMemberInfo(BaseModel):
    """Schema for member information in system status."""

    id: int = Field(..., description="Member ID")
    name: str = Field(..., description="Member name")
    is_active: bool = Field(..., description="Whether the member is active")
    paid_remainder_in_cycle: bool = Field(
        ..., description="Whether the member has paid remainder in cycle"
    )
    period_balance: str = Field(
        ...,
        description="Period balance description (e.g., 'Is owed $123.45', 'Owes $67.89', or 'N/A')",
    )


class TransactionCounts(BaseModel):
    """Schema for transaction counts in system status."""

    total: int = Field(..., description="Total number of transactions")
    deposits: int = Field(..., description="Number of deposit transactions")
    expenses: int = Field(..., description="Number of expense transactions")


class SystemStatusResponse(BaseModel):
    """Schema for system status response."""

    current_period: PeriodResponse | None
    period_summary: PeriodSummaryResponse | None
    total_members: int
    active_members_count: int
    inactive_members_count: int
    members: list[SystemMemberInfo]
    transaction_counts: TransactionCounts
