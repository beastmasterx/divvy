"""
FastAPI dependencies for dependency injection.
Provides common dependencies like database sessions, authentication, etc.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UserResponse
from app.db import get_session
from app.db.audit import set_current_user_id
from app.exceptions import UnauthorizedError
from app.services import (
    AuthService,
    CategoryService,
    GroupService,
    IdentityProviderService,
    PeriodService,
    SettlementService,
    TransactionService,
    UserService,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    async with get_session() as session:
        yield session


# Service dependencies
# Base services (no dependencies on other services)
def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency that provides UserService instance."""
    return UserService(db)


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> AuthService:
    """Dependency that provides AuthService instance."""
    return AuthService(
        session=db,
        user_service=user_service,
    )


def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    """Dependency that provides CategoryService instance."""
    return CategoryService(db)


def get_period_service(db: AsyncSession = Depends(get_db)) -> PeriodService:
    """Dependency that provides PeriodService instance."""
    return PeriodService(db)


def get_transaction_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    """Dependency that provides TransactionService instance."""
    return TransactionService(db)


# Services with dependencies on other services
def get_group_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> GroupService:
    """Dependency that provides GroupService instance."""
    return GroupService(db, user_service)


def get_settlement_service(
    db: AsyncSession = Depends(get_db),
    transaction_service: TransactionService = Depends(get_transaction_service),
    period_service: PeriodService = Depends(get_period_service),
    category_service: CategoryService = Depends(get_category_service),
    user_service: UserService = Depends(get_user_service),
) -> SettlementService:
    """Dependency that provides SettlementService instance."""
    return SettlementService(transaction_service, period_service, category_service, user_service)


def get_identity_provider_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> IdentityProviderService:
    """Dependency that provides IdentityProviderService instance."""
    return IdentityProviderService(
        session=db,
        user_service=user_service,
        auth_service=auth_service,
    )


# Authentication dependencies
_oauth2_schema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_schema)],
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Get current authenticated user from JWT token.

    Extracts JWT token from Authorization header, verifies it, and returns the User object.

    Args:
        token: JWT token
        auth_service: Authentication service instance
        user_service: User service instance

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid, expired, or user not found/inactive
    """
    try:
        payload = await auth_service.verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedError("Invalid authentication token")
        user_id = int(user_id_str)
    except (UnauthorizedError, ValueError, KeyError) as e:
        raise UnauthorizedError("Invalid authentication token") from e

    user = await user_service.get_user_by_id(user_id)

    if not user or not user.is_active:
        raise UnauthorizedError("User account not found or inactive")

    # Set user ID in audit context for SQLAlchemy events
    # This allows automatic setting of created_by and updated_by fields
    set_current_user_id(user.id)

    return user


def _get_optional_token(request: Request) -> str | None:
    """Extract optional token from Authorization header."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        return token
    except ValueError:
        return None


async def get_current_user_optional(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse | None:
    """
    Get current authenticated user from JWT token (optional).

    Returns None if no token is provided or token is invalid.
    This is useful for endpoints that work both with and without authentication.

    Args:
        request: FastAPI request object
        auth_service: Authentication service instance
        user_service: User service instance

    Returns:
        Authenticated User object if token is valid, None otherwise
    """
    token = _get_optional_token(request)
    if not token:
        return None

    try:
        payload = await auth_service.verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
    except (UnauthorizedError, ValueError, KeyError):
        return None

    user = await user_service.get_user_by_id(user_id)

    if not user or not user.is_active:
        return None

    # Set user ID in audit context for SQLAlchemy events
    set_current_user_id(user.id)

    return user
