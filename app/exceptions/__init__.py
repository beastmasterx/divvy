"""
Exception Registry and Public Interface 🗃️

This module serves as the public interface for the application's custom exceptions,
re-exporting classes defined in sub-modules like 'http' and 'auth'.

This allows consuming modules to import all necessary exceptions from a single, clean path:
    from app.exceptions import ValidationError, InvalidAccessTokenError

The structure groups exceptions by their area of concern (HTTP status, Auth domain, etc.).
"""

# Import all exceptions from domain-specific modules for centralized access.
from .auth import (
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    InvalidStateTokenError,
)
from .http import (
    BusinessRuleError,  # Alias for UnprocessableContentError
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableContentError,
    ValidationError,
)

__all__ = [
    # Core HTTP Errors (Alphabetical by HTTP Status)
    "ValidationError",  # 400
    "UnauthorizedError",  # 401 (Base)
    "ForbiddenError",  # 403
    "NotFoundError",  # 404
    "ConflictError",  # 409
    "UnprocessableContentError",  # 422
    "BusinessRuleError",  # 422 (Alias)
    "InternalServerError",  # 500
    # Auth Domain Errors (Inherit from UnauthorizedError)
    "InvalidStateTokenError",
    "InvalidAccessTokenError",
    "InvalidRefreshTokenError",
]
