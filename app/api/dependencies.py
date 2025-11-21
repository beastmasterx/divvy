"""
FastAPI dependencies for dependency injection.
Provides common dependencies like database sessions, authentication, etc.
"""

from collections.abc import Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.exceptions import UnauthorizedError
from app.models import User
from app.services import (
    AuthService,
    CategoryService,
    GroupService,
    PeriodService,
    SettlementService,
    TransactionService,
    UserService,
)


def get_db() -> Iterator[Session]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    with get_session() as session:
        yield session


# Service dependencies
# Base services (no dependencies on other services)
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency that provides UserService instance."""
    return UserService(db)


def get_auth_service(
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """Dependency that provides AuthService instance."""
    return AuthService(
        session=db,
        user_service=user_service,
    )


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """Dependency that provides CategoryService instance."""
    return CategoryService(db)


def get_period_service(db: Session = Depends(get_db)) -> PeriodService:
    """Dependency that provides PeriodService instance."""
    return PeriodService(db)


def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    """Dependency that provides TransactionService instance."""
    return TransactionService(db)


# Services with dependencies on other services
def get_group_service(
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> GroupService:
    """Dependency that provides GroupService instance."""
    return GroupService(db, user_service)


def get_settlement_service(
    db: Session = Depends(get_db),
    transaction_service: TransactionService = Depends(get_transaction_service),
    period_service: PeriodService = Depends(get_period_service),
    category_service: CategoryService = Depends(get_category_service),
    user_service: UserService = Depends(get_user_service),
) -> SettlementService:
    """Dependency that provides SettlementService instance."""
    return SettlementService(transaction_service, period_service, category_service, user_service)


# Authentication dependencies
_security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Get current authenticated user from JWT token.

    Extracts JWT token from Authorization header, verifies it, and returns the User object.

    Args:
        credentials: HTTPBearer credentials containing the JWT token
        auth_service: Authentication service instance

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid, expired, or user not found/inactive
    """
    token = credentials.credentials

    try:
        payload = auth_service.verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedError("Invalid authentication token")
        user_id = int(user_id_str)
    except (UnauthorizedError, ValueError, KeyError) as e:
        raise UnauthorizedError("Invalid authentication token") from e

    user = user_service.get_user_by_id(user_id)

    if not user or not user.is_active:
        raise UnauthorizedError("User account not found or inactive")

    return user
