from pydantic import BaseModel, Field


class GroupRequest(BaseModel):
    """Schema for group request."""

    name: str = Field(..., description="Group name")


class GroupResponse(BaseModel):
    """Schema for group response."""

    model_config = {"from_attributes": True}
    id: int = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")
