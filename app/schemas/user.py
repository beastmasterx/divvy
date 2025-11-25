"""
Pydantic schemas for user requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field


class UserRequest(BaseModel):
    """Schema for user creation requests."""

    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    password: str | None = Field(default=None, description="User's password (optional, will be hashed if provided)")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    avatar: str | None = Field(default=None, description="URL to user's avatar image")


class ProfileRequest(BaseModel):
    """Schema for updating user profile."""

    email: EmailStr | None = Field(default=None, description="User's email address")
    name: str | None = Field(default=None, min_length=1, max_length=255, description="User's full name")
    is_active: bool | None = Field(default=True, description="Whether the user account is active")
    avatar: str | None = Field(default=None, description="URL to user's avatar image")


class PasswordChangeRequest(BaseModel):
    """Schema for changing password (requires old password verification)."""

    old_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class PasswordResetRequest(BaseModel):
    """Schema for resetting password."""

    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class UserResponse(BaseModel):
    """Response schema for user information."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User's email address")
    name: str = Field(..., description="User's full name")
    avatar: str | None = Field(None, description="URL to user's avatar image")
    is_active: bool = Field(default=True, description="Whether the user account is active")
