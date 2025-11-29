"""
Authentication and Authorization Exceptions 🔑

This module defines domain-specific exceptions related to authentication and token handling.
All exceptions here inherit from UnauthorizedError (HTTP 401), ensuring that API consumers
receive the appropriate status code when a token or credential fails validation.

Contents:
- InvalidStateTokenError: For CSRF protection/OAuth state issues.
- InvalidAccessTokenError: For malformed, expired, or invalid Access JWTs.
- InvalidRefreshTokenError: For malformed, expired, or revoked Refresh JWTs.
"""
from .http import UnauthorizedError


class InvalidStateTokenError(UnauthorizedError):
    """Raised when an OAuth State Token (used for CSRF protection) is invalid or expired."""

    def __init__(self, detail: str = "Invalid or expired OAuth state token."):
        super().__init__(detail=detail)


class InvalidAccessTokenError(UnauthorizedError):
    """Raised when an Access Token is invalid, expired, or improperly signed."""

    def __init__(self, detail: str = "Invalid or expired access token."):
        super().__init__(detail=detail)


class InvalidRefreshTokenError(UnauthorizedError):
    """Raised when a Refresh Token is invalid, expired, or revoked."""

    def __init__(self, detail: str = "Invalid, expired, or revoked refresh token."):
        super().__init__(detail=detail)
