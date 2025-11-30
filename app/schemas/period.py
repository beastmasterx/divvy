from datetime import datetime

from pydantic import BaseModel, Field

from app.models import PeriodStatus


class PeriodRequest(BaseModel):
    """Schema for period request."""

    name: str = Field(..., description="Period name")


class PeriodResponse(BaseModel):
    """Schema for period response."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Period ID")
    group_id: int = Field(..., description="Group ID")
    name: str = Field(..., description="Period name")
    status: PeriodStatus = Field(..., description="Period status")
    start_date: datetime = Field(..., description="Period start date")
    end_date: datetime | None = Field(default=None, description="Period end date")

    created_at: datetime | None = Field(default=None, description="Period created at")
    updated_at: datetime | None = Field(default=None, description="Period updated at")

    created_by: int | None = Field(default=None, description="Period created by")
    updated_by: int | None = Field(default=None, description="Period updated by")
