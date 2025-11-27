"""
Pydantic schemas for authentication requests and responses.
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    password: str = Field(..., min_length=8, description="User's password (minimum 8 characters)")


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access tokens."""

    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")


class TokenResponse(BaseModel):
    """
    OAuth2 token endpoint response schema (RFC 6749).

    This response follows the OAuth2 specification for token endpoint responses.
    Field order matches OAuth2 standard: access_token, token_type, expires_in, refresh_token, scope.
    """

    response_type: Literal["token"] = Field(
        default="token",
        description="Response type discriminator - only used in OAuth callback endpoint for discriminated union. Not part of OAuth2 RFC 6749 spec.",
    )
    access_token: str = Field(
        ..., description="The access token issued by the authorization server (OAuth 2.0 RFC 6749)"
    )
    token_type: str = Field(
        default="Bearer",
        description="The type of token issued. Value is case-insensitive per OAuth 2.0 RFC 6749",
    )
    expires_in: int = Field(..., description="The lifetime in seconds of the access token (OAuth 2.0 RFC 6749)")
    refresh_token: str = Field(
        ..., description="The refresh token used to obtain new access tokens (OAuth 2.0 RFC 6749)"
    )
    scope: str | None = Field(
        default=None,
        description="The scope of the access token as a space-delimited string (OAuth 2.0 RFC 6749, optional)",
    )


class OAuthAuthorizeResponse(BaseModel):
    """Response schema for OAuth authorization URL."""

    authorization_url: str = Field(..., description="URL to redirect user to for OAuth login")


class LinkingRequiredResponse(BaseModel):
    """Response schema for OAuth callback when account linking is required."""

    response_type: Literal["linking_required"] = Field(
        default="linking_required",
        description="Response type discriminator - indicates account linking is required",
    )
    requires_linking: bool = Field(default=True, description="Whether account linking is required")
    request_token: str = Field(..., description="Token for account linking request")
    email: str = Field(..., description="Email address for account linking")
    message: str = Field(..., description="Message explaining the account linking requirement")
