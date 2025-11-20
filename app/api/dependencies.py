"""
FastAPI dependencies for dependency injection.
Provides common dependencies like database sessions, authentication, etc.
"""

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services import (
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
) -> SettlementService:
    """Dependency that provides SettlementService instance."""
    return SettlementService(db, transaction_service)


# Example: Add authentication dependency when needed
# def get_current_user(db: Session = Depends(get_db)) -> User:
#     """Get current authenticated user."""
#     ...
