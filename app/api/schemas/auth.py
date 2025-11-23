"""
Pydantic schemas for authentication requests and responses.
"""

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
