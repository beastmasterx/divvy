from datetime import datetime

from pydantic import BaseModel, Field


class PeriodRequest(BaseModel):
    """Schema for period request."""

    name: str = Field(..., description="Period name")
    start_date: datetime = Field(..., description="Period start date")
    end_date: datetime = Field(..., description="Period end date")


class PeriodResponse(BaseModel):
    """Schema for period response."""

    model_config = {"from_attributes": True}
    id: int = Field(..., description="Period ID")
    name: str = Field(..., description="Period name")
    start_date: datetime = Field(..., description="Period start date")
    end_date: datetime = Field(..., description="Period end date")
    is_settled: bool = Field(..., description="Period settled status")
    settled_date: datetime = Field(..., description="Period settled date")

    created_at: datetime = Field(..., description="Period created at")
    updated_at: datetime = Field(..., description="Period updated at")

    created_by: int = Field(..., description="Period created by")
    updated_by: int = Field(..., description="Period updated by")
