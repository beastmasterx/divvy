"""
Service instance fixtures for testing.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.fixture
def user_service(db_session: AsyncSession) -> UserService:
    """Create a UserService instance for testing."""
    return UserService(db_session)


@pytest.fixture
def authentication_service(db_session: AsyncSession, user_service: UserService) -> AuthenticationService:
    """Create an AuthenticationService instance for testing."""
    return AuthenticationService(session=db_session, user_service=user_service)


@pytest.fixture
def authorization_service(db_session: AsyncSession) -> AuthorizationService:
    """Create an AuthorizationService instance for testing."""
    return AuthorizationService(db_session)


@pytest.fixture
def period_service(db_session: AsyncSession) -> PeriodService:
    """Create a PeriodService instance for testing."""
    return PeriodService(db_session)


@pytest.fixture
def category_service(db_session: AsyncSession) -> CategoryService:
    """Create a CategoryService instance for testing."""
    return CategoryService(db_session)


@pytest.fixture
def group_service(
    db_session: AsyncSession, authorization_service: AuthorizationService, period_service: PeriodService
) -> GroupService:
    """Create a GroupService instance for testing."""
    return GroupService(db_session, authorization_service, period_service)


@pytest.fixture
def user_identity_service(db_session: AsyncSession, user_service: UserService) -> UserIdentityService:
    """Create a UserIdentityService instance for testing."""
    return UserIdentityService(session=db_session, user_service=user_service)


@pytest.fixture
def account_link_request_service(db_session: AsyncSession, user_service: UserService) -> AccountLinkRequestService:
    """Create an AccountLinkRequestService instance for testing."""
    return AccountLinkRequestService(session=db_session, user_service=user_service)


@pytest.fixture
def identity_provider_service(
    db_session: AsyncSession,
    user_service: UserService,
    user_identity_service: UserIdentityService,
    account_link_request_service: AccountLinkRequestService,
    authentication_service: AuthenticationService,
) -> IdentityProviderService:
    """Create an IdentityProviderService instance for testing."""
    return IdentityProviderService(
        session=db_session,
        user_service=user_service,
        user_identity_service=user_identity_service,
        account_link_request_service=account_link_request_service,
        authentication_service=authentication_service,
    )


@pytest.fixture
def transaction_service(db_session: AsyncSession) -> TransactionService:
    """Create a TransactionService instance for testing."""
    return TransactionService(db_session)


@pytest.fixture
def settlement_service(
    transaction_service: TransactionService,
    period_service: PeriodService,
    category_service: CategoryService,
    user_service: UserService,
) -> SettlementService:
    """Create a SettlementService instance for testing."""
    return SettlementService(
        transaction_service=transaction_service,
        period_service=period_service,
        category_service=category_service,
        user_service=user_service,
    )
