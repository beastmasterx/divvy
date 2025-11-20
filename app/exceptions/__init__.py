from fastapi import HTTPException


class ValidationError(HTTPException):
    """Raised when validation fails."""

    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class UnauthorizedError(HTTPException):
    """Raised when a user is not authorized to access a resource."""

    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    """Raised when a user is forbidden to access a resource."""

    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class NotFoundError(HTTPException):
    """Raised when a resource is not found."""

    def __init__(self, detail: str):
        super().__init__(status_code=404, detail=detail)


class ConflictError(HTTPException):
    """Raised when there's a conflict (e.g., duplicate resource)."""

    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)


class BusinessRuleError(HTTPException):
    """Raised when a business rule is violated."""

    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


class InternalServerError(HTTPException):
    """Raised when an internal server error occurs."""

    def __init__(self, detail: str):
        super().__init__(status_code=500, detail=detail)


__all__ = [
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "BusinessRuleError",
    "InternalServerError",
]
