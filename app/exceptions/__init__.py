from fastapi import HTTPException, status


class ValidationError(HTTPException):
    """Raised when validation fails."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedError(HTTPException):
    """Raised when a user is not authorized to access a resource."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(HTTPException):
    """Raised when a user is forbidden to access a resource."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(HTTPException):
    """Raised when a resource is not found."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Raised when there's a conflict (e.g., duplicate resource)."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BusinessRuleError(HTTPException):
    """Raised when a business rule is violated."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class InternalServerError(HTTPException):
    """Raised when an internal server error occurs."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


__all__ = [
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "BusinessRuleError",
    "InternalServerError",
]
