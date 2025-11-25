"""
Service dependencies.
"""

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db, get_serializable_db
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


# Services with SERIALIZABLE isolation level
@dataclass
class SerializableServices:
    """
    Container for all services configured with SERIALIZABLE isolation level.

    This dataclass groups all application services that share a single
    database session with SERIALIZABLE transaction isolation level. Use this
    for critical financial operations like settlement processing where
    concurrent transactions must be prevented to ensure data consistency.

    All services in this container use the same database session, ensuring
    that all operations within a request are part of the same transaction
    with the highest isolation level.

    Attributes:
        user_service: Service for user management operations
        auth_service: Service for authentication operations
        category_service: Service for category management
        period_service: Service for period management
        transaction_service: Service for transaction operations
        group_service: Service for group management
        settlement_service: Service for settlement calculations and processing
        identity_provider_service: Service for OAuth identity provider operations
    """

    user_service: UserService
    auth_service: AuthService
    category_service: CategoryService
    period_service: PeriodService
    transaction_service: TransactionService
    group_service: GroupService
    settlement_service: SettlementService
    identity_provider_service: IdentityProviderService


def get_serializable_services(
    db: AsyncSession = Depends(get_serializable_db),
) -> SerializableServices:
    """Dependency that provides SerializableServices instance with SERIALIZABLE isolation level."""
    # Create base services (no dependencies)
    user_service = UserService(db)
    category_service = CategoryService(db)
    period_service = PeriodService(db)
    transaction_service = TransactionService(db)

    # Create services with dependencies on base services
    auth_service = AuthService(session=db, user_service=user_service)
    group_service = GroupService(db, user_service)

    # Create services with dependencies on multiple services
    settlement_service = SettlementService(
        transaction_service=transaction_service,
        period_service=period_service,
        category_service=category_service,
        user_service=user_service,
    )
    identity_provider_service = IdentityProviderService(
        session=db,
        user_service=user_service,
        auth_service=auth_service,
    )

    return SerializableServices(
        user_service=user_service,
        auth_service=auth_service,
        category_service=category_service,
        period_service=period_service,
        transaction_service=transaction_service,
        group_service=group_service,
        settlement_service=settlement_service,
        identity_provider_service=identity_provider_service,
    )
