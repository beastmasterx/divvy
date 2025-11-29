"""
HTTP-Based Application Exceptions 🚫

This module defines standard application-wide exception classes that map directly
to common HTTP status codes (4xx and 5xx). All exceptions inherit from FastAPI's
HTTPException to ensure automatic handling by the framework, returning the
correct status code and response body.

The exceptions are named to be semantically clearer than the raw status codes
in application logic (e.g., ValidationError instead of HTTPException(400)).

Contents:
- 400 Client Errors: ValidationError
- 401 Authorization Errors: UnauthorizedError (base for auth-specific exceptions)
- 403 Permission Errors: ForbiddenError
- 404 Resource Errors: NotFoundError
- 409 Conflict Errors: ConflictError
- 422 Semantic Errors: UnprocessableContentError, BusinessRuleError (alias)
- 500 Server Errors: InternalServerError
"""

from fastapi import HTTPException, status


class ValidationError(HTTPException):
    """Raised when general input or payload validation fails (e.g., missing field). (HTTP 400)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedError(HTTPException):
    """Base exception raised when a request is missing valid authentication credentials. (HTTP 401)"""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(HTTPException):
    """Raised when a user is authenticated but forbidden to access a resource (lacks permissions). (HTTP 403)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(HTTPException):
    """Raised when a specific resource requested is not found. (HTTP 404)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Raised when there's a conflict (e.g., duplicate resource creation). (HTTP 409)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnprocessableContentError(HTTPException):
    """Raised when the request is well-formed but cannot be processed due to a semantic error or business rule violation (per RFC 9110). (HTTP 422)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


# Alias for domain-specific clarity.
BusinessRuleError = UnprocessableContentError
"""Alias for UnprocessableContentError (HTTP 422). Use this in application code when a
request is valid but violates a core business constraint."""


class InternalServerError(HTTPException):
    """Raised when an internal server error occurs. (HTTP 500)"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
