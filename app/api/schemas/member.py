"""
Pydantic schemas for Member API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field


class MemberBase(BaseModel):
    """Base member schema with common fields."""
    email: EmailStr = Field(..., description="Member email address")
    name: str = Field(..., description="Member name", min_length=1)


class MemberCreate(MemberBase):
    """Schema for creating a new member."""
    pass


class MemberResponse(BaseModel):
    """Schema for member response."""
    model_config = {"from_attributes": True}
    
    id: int
    email: str
    name: str
    is_active: bool
    paid_remainder_in_cycle: bool


class MemberUpdate(BaseModel):
    """Schema for updating member status."""
    is_active: bool | None = None


class MemberMessageResponse(BaseModel):
    """Schema for member operation result messages."""
    message: str

