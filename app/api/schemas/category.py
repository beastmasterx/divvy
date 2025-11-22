"""
Pydantic schemas for Category API endpoints.
"""

from pydantic import BaseModel, Field


class CategoryRequest(BaseModel):
    """Schema for category request."""

    name: str = Field(..., description="Category name")


class CategoryResponse(BaseModel):
    """Schema for category response."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    is_default: bool = Field(..., description="Whether the category is a default category")
