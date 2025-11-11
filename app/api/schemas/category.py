"""
Pydantic schemas for Category API endpoints.
"""

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Schema for category response."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
