"""
Service dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db, get_serializable_db
from app.repositories import PeriodRepository, SettlementRepository
from app.services import (
    AccountLinkRequestService,
    AuthenticationService,
    AuthorizationService,
    CategoryService,
    GroupService,
    IdentityProviderService,
    PeriodService,
    SettlementService,
    TransactionService,
    UserIdentityService,
    UserService,
)


# Base services (no dependencies on other services)
def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency that provides UserService instance."""
    return UserService(db)


def get_authentication_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> AuthenticationService:
    """Dependency that provides AuthenticationService instance."""
    return AuthenticationService(
        session=db,
        user_service=user_service,
    )


def get_authorization_service(db: AsyncSession = Depends(get_db)) -> AuthorizationService:
    """Dependency that provides AuthorizationService instance."""
    return AuthorizationService(db)


def get_user_identity_service(
    db: AsyncSession = Depends(get_db), user_service: UserService = Depends(get_user_service)
) -> UserIdentityService:
    """Dependency that provides UserIdentityService instance."""
    return UserIdentityService(db, user_service)


def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    """Dependency that provides CategoryService instance."""
    return CategoryService(db)


def get_period_service(db: AsyncSession = Depends(get_db)) -> PeriodService:
    """Dependency that provides PeriodService instance."""
    return PeriodService(db)


def get_transaction_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    """Dependency that provides TransactionService instance."""
    return TransactionService(db)


def get_account_link_request_service(
    db: AsyncSession = Depends(get_db), user_service: UserService = Depends(get_user_service)
) -> AccountLinkRequestService:
    """Dependency that provides AccountLinkRequestService instance."""
    return AccountLinkRequestService(db, user_service)


# Services with dependencies on other services
def get_group_service(
    db: AsyncSession = Depends(get_db),
    authorization_service: AuthorizationService = Depends(get_authorization_service),
    period_service: PeriodService = Depends(get_period_service),
) -> GroupService:
    """Dependency that provides GroupService instance."""
    return GroupService(db, authorization_service, period_service)


def get_settlement_service(
    db: AsyncSession = Depends(get_db),
    transaction_service: TransactionService = Depends(get_transaction_service),
    period_service: PeriodService = Depends(get_period_service),
    category_service: CategoryService = Depends(get_category_service),
    user_service: UserService = Depends(get_user_service),
) -> SettlementService:
    """Dependency that provides SettlementService instance."""
    settlement_repository = SettlementRepository(db)
    period_repository = PeriodRepository(db)
    return SettlementService(
        transaction_service=transaction_service,
        period_service=period_service,
        category_service=category_service,
        user_service=user_service,
        settlement_repository=settlement_repository,
        period_repository=period_repository,
    )


def get_identity_provider_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    authentication_service: AuthenticationService = Depends(get_authentication_service),
    user_identity_service: UserIdentityService = Depends(get_user_identity_service),
    account_link_request_service: AccountLinkRequestService = Depends(get_account_link_request_service),
) -> IdentityProviderService:
    """Dependency that provides IdentityProviderService instance."""
    return IdentityProviderService(
        session=db,
        user_service=user_service,
        user_identity_service=user_identity_service,
        account_link_request_service=account_link_request_service,
        authentication_service=authentication_service,
    )


# Services with SERIALIZABLE isolation level
def get_serializable_settlement_service(
    db: AsyncSession = Depends(get_serializable_db),
) -> SettlementService:
    """Dependency that provides SettlementService instance with SERIALIZABLE isolation level."""
    user_service = UserService(db)
    category_service = CategoryService(db)
    period_service = PeriodService(db)
    transaction_service = TransactionService(db)
    settlement_repository = SettlementRepository(db)
    period_repository = PeriodRepository(db)

    return SettlementService(
        transaction_service=transaction_service,
        period_service=period_service,
        category_service=category_service,
        user_service=user_service,
        settlement_repository=settlement_repository,
        period_repository=period_repository,
    )
