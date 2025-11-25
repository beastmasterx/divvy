"""
Service dependencies.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.dependencies.db import get_db
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
    return SettlementService(
        transaction_service=transaction_service,
        period_service=period_service,
        category_service=category_service,
        user_service=user_service,
    )


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

