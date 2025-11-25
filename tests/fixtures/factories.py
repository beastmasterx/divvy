"""
Factory functions for creating test data.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import (
    AccountLinkRequest,
    AccountLinkRequestStatus,
    Category,
    Group,
    Period,
    SplitKind,
    Transaction,
    TransactionKind,
    User,
    UserIdentity,
)


def create_test_user(
    email: str = "test@example.com",
    name: str = "Test User",
    password: str | None = None,
    is_active: bool = True,
    avatar: str | None = None,
    **kwargs: Any
) -> User:
    """
    Factory for creating test users.

    Args:
        email: User email address
        name: User name
        password: User password (will be hashed in real usage)
        is_active: Whether user is active
        avatar: User avatar URL
        **kwargs: Additional User model fields

    Returns:
        User instance (not persisted to database)
    """
    return User(email=email, name=name, password=password, is_active=is_active, avatar=avatar, **kwargs)


def create_test_group(name: str = "Test Group", **kwargs: Any) -> Group:
    """
    Factory for creating test groups.

    Args:
        name: Group name
        **kwargs: Additional Group model fields

    Returns:
        Group instance (not persisted to database)
    """
    return Group(name=name, **kwargs)


def create_test_category(name: str = "Test Category", is_default: bool = False, **kwargs: Any) -> Category:
    """
    Factory for creating test categories.

    Args:
        name: Category name
        is_default: Whether category is a default category
        **kwargs: Additional Category model fields

    Returns:
        Category instance (not persisted to database)
    """
    return Category(name=name, is_default=is_default, **kwargs)


def create_test_period(
    group_id: int = 1,
    name: str = "Test Period",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    created_by: int | None = None,
    **kwargs: Any
) -> Period:
    """
    Factory for creating test periods.

    Args:
        group_id: ID of the group this period belongs to
        name: Period name
        is_settled: Whether period is settled
        start_date: Period start date (defaults to now)
        end_date: Period end date (None for active periods)
        **kwargs: Additional Period model fields

    Returns:
        Period instance (not persisted to database)
    """
    if start_date is None:
        start_date = datetime.now(UTC)

    return Period(
        group_id=group_id, name=name, start_date=start_date, end_date=end_date, created_by=created_by, **kwargs
    )


def create_test_transaction(
    transaction_kind: TransactionKind = TransactionKind.EXPENSE,
    split_kind: SplitKind = SplitKind.EQUAL,
    amount: int = 10000,  # in cents (100.00)
    payer_id: int = 1,
    category_id: int = 1,
    period_id: int = 1,
    description: str | None = "Test transaction",
    **kwargs: Any
) -> Transaction:
    """
    Factory for creating test transactions.

    Args:
        transaction_kind: Type of transaction (expense, deposit, refund)
        split_kind: How to split the transaction (personal, equal, amount, percentage)
        amount: Transaction amount in cents
        payer_id: ID of the user who paid
        category_id: ID of the category
        period_id: ID of the period this transaction belongs to
        description: Transaction description
        **kwargs: Additional Transaction model fields

    Returns:
        Transaction instance (not persisted to database)
    """
    return Transaction(
        transaction_kind=transaction_kind,
        split_kind=split_kind,
        amount=amount,
        payer_id=payer_id,
        category_id=category_id,
        period_id=period_id,
        description=description,
        **kwargs
    )


def create_test_user_identity(
    user_id: int = 1,
    identity_provider: str = "microsoft",
    external_id: str = "external_123",
    external_email: str | None = "external@example.com",
    external_username: str | None = "external_user",
    **kwargs: Any
) -> UserIdentity:
    """
    Factory for creating test user identities.

    Args:
        user_id: ID of the user this identity belongs to
        identity_provider: Name of the identity provider (microsoft, google, facebook)
        external_id: Provider's unique user ID
        external_email: Email from provider (optional)
        external_username: Username from provider (optional)
        **kwargs: Additional UserIdentity model fields

    Returns:
        UserIdentity instance (not persisted to database)
    """
    return UserIdentity(
        user_id=user_id,
        identity_provider=identity_provider,
        external_id=external_id,
        external_email=external_email,
        external_username=external_username,
        **kwargs
    )


def create_test_account_link_request(
    user_identity_id: int = 1,
    request_token: str = "test_token_123",
    status: str = AccountLinkRequestStatus.PENDING.value,
    expires_at: datetime | None = None,
    email_at: datetime | None = None,
    verified_at: datetime | None = None,
    **kwargs: Any
) -> AccountLinkRequest:
    """
    Factory for creating test account link requests.

    Args:
        user_identity_id: ID of the user identity this request is for
        request_token: Unique token for the request
        status: Status of the request (pending, approved, denied, expired)
        expires_at: When the request expires (defaults to 24 hours from now)
        email_at: When the email was sent (optional)
        verified_at: When the request was verified (optional)
        **kwargs: Additional AccountLinkRequest model fields

    Returns:
        AccountLinkRequest instance (not persisted to database)
    """
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(hours=24)

    return AccountLinkRequest(
        user_identity_id=user_identity_id,
        request_token=request_token,
        status=status,
        expires_at=expires_at,
        email_at=email_at,
        verified_at=verified_at,
        **kwargs
    )
