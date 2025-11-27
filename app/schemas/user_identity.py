"""
Pydantic schemas for user identity requests and responses.
"""

from pydantic import BaseModel, Field

from app.models.user import IdentityProviderName


class UserIdentityRequest(BaseModel):
    """Schema for creating a user identity."""

    user_id: int = Field(..., description="ID of the user this identity belongs to")
    identity_provider: IdentityProviderName = Field(..., description="Name of the identity provider")
    external_id: str = Field(..., max_length=255, description="Provider's unique user ID")
    external_email: str | None = Field(default=None, max_length=255, description="Email from provider (optional)")
    external_username: str | None = Field(default=None, max_length=255, description="Username from provider (optional)")


class UserIdentityUpdateRequest(BaseModel):
    """Schema for updating a user identity."""

    external_email: str | None = Field(default=None, max_length=255, description="Email from provider")
    external_username: str | None = Field(default=None, max_length=255, description="Username from provider")


class UserIdentityResponse(BaseModel):
    """Response schema for user identity information."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="User identity ID")
    user_id: int = Field(..., description="ID of the user this identity belongs to")
    identity_provider: IdentityProviderName = Field(..., description="Name of the identity provider")
    external_id: str = Field(..., description="Provider's unique user ID")
    external_email: str | None = Field(None, description="Email from provider")
    external_username: str | None = Field(None, description="Username from provider")
