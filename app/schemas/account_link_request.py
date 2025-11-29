"""
Pydantic schemas for account link request requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import AccountLinkRequestStatus, IdentityProviderName


class AccountLinkRequestCreateRequest(BaseModel):
    """Schema for creating an account link request."""

    user_id: int = Field(..., description="ID of the user to link the identity to")
    identity_provider: IdentityProviderName = Field(..., description="Identity provider name")
    external_id: str = Field(..., max_length=255, description="Provider's unique user ID")
    external_email: str | None = Field(default=None, max_length=255, description="Email from provider")
    external_username: str | None = Field(default=None, max_length=255, description="Username from provider")


class AccountLinkRequestResponse(BaseModel):
    """Response schema for account link request information."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Account link request ID")
    request_token: str = Field(..., description="Unique token for the request")
    user_id: int = Field(..., description="ID of the user to link the identity to")
    identity_provider: IdentityProviderName = Field(..., description="Identity provider name")
    external_id: str = Field(..., description="Provider's unique user ID")
    external_email: str | None = Field(default=None, description="Email from provider")
    external_username: str | None = Field(default=None, description="Username from provider")
    status: AccountLinkRequestStatus = Field(..., description="Status of the request")
    expires_at: datetime = Field(..., description="When the request expires")


class AccountLinkVerifyRequest(BaseModel):
    """Request schema for verifying an account link request."""

    request_token: str = Field(..., description="Account link request token")
