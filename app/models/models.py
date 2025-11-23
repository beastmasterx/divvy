"""
SQLAlchemy ORM models for the Divvy application.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TransactionKind(str, Enum):
    """Types of transactions in the expense splitting system."""

    EXPENSE = "expense"
    DEPOSIT = "deposit"
    REFUND = "refund"


class SplitKind(str, Enum):
    """Methods for splitting transaction costs among users."""

    PERSONAL = "personal"  # Only the payer (no split)
    EQUAL = "equal"  # Split equally among all participants
    AMOUNT = "amount"  # Custom amounts per person (in cents)
    PERCENTAGE = "percentage"  # Custom percentages per person


class TimestampMixin:
    """Mixin to add automatic timestamp tracking to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        onupdate=lambda: datetime.now(UTC),
        index=True,
    )


class AuditMixin(TimestampMixin):
    """Mixin to add full audit trail (timestamps + user tracking) to models."""

    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class Group(AuditMixin, Base):
    """Group model representing groups in the expense splitting system."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    owner: Mapped[User] = relationship("User", foreign_keys="Group.owner_id", back_populates="owned_groups")
    group_users: Mapped[list[GroupUser]] = relationship(
        "GroupUser", back_populates="group", cascade="all, delete-orphan"
    )
    periods: Mapped[list[Period]] = relationship("Period", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name='{self.name}')>"


class User(TimestampMixin, Base):
    """User model representing users in the expense splitting system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    owned_groups: Mapped[list[Group]] = relationship("Group", foreign_keys="Group.owner_id", back_populates="owner")
    group_users: Mapped[list[GroupUser]] = relationship(
        "GroupUser", foreign_keys="GroupUser.user_id", back_populates="user"
    )
    paid_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys="Transaction.payer_id",
        back_populates="payer",
    )
    expense_shares: Mapped[list[ExpenseShare]] = relationship(
        "ExpenseShare", foreign_keys="ExpenseShare.user_id", back_populates="user"
    )

    # Refresh token relationship
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    # Identity provider relationships
    identities: Mapped[list[UserIdentity]] = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', is_active={self.is_active})>"


class RefreshToken(TimestampMixin, Base):
    """RefreshToken model for managing refresh tokens."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_token_token", "token"),
        Index("ix_refresh_token_user_expires", "user_id", "expires_at"),
        Index("ix_refresh_token_user_revoked", "user_id", "is_revoked"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, is_revoked={self.is_revoked})>"


class GroupUser(AuditMixin, Base):
    """GroupUser model representing the relationship between a group and a user."""

    __tablename__ = "group_users"

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="group_users")
    user: Mapped[User] = relationship("User", foreign_keys="GroupUser.user_id", back_populates="group_users")

    def __repr__(self) -> str:
        return f"<GroupUser(group_id={self.group_id}, user_id={self.user_id})>"


class ExpenseShare(AuditMixin, Base):
    """Tracks which users share in a transaction and their portion of the cost."""

    __tablename__ = "expense_shares"

    # Composite primary key
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id"), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True, index=True)

    # Share calculation - if null, split equally
    share_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Amount in cents
    share_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)  # Percentage (0.0 to 100.0)

    # Relationships
    transaction: Mapped[Transaction] = relationship("Transaction", back_populates="expense_shares")
    user: Mapped[User] = relationship("User", foreign_keys="ExpenseShare.user_id", back_populates="expense_shares")

    def __repr__(self) -> str:
        return f"<ExpenseShare(transaction_id={self.transaction_id}, user_id={self.user_id})>"


class Period(AuditMixin, Base):
    """Period model representing settlement periods.

    Each period belongs to a group and defines a timeframe for expense tracking and settlement.
    """

    __tablename__ = "periods"
    __table_args__ = (Index("ix_period_group_dates", "group_id", "start_date", "end_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="periods")
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="period")

    @property
    def is_closed(self) -> bool:
        """Check if this period is closed."""
        return self.end_date is not None

    def __repr__(self) -> str:
        return f"<Period(id={self.id}, name='{self.name}', start_date={self.start_date}, end_date={self.end_date})>"


class Category(TimestampMixin, Base):
    """Category model for transaction categorization."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Transaction(AuditMixin, Base):
    """Transaction model for expenses, deposits, and refunds.

    Transactions belong to a period. The group can be accessed through the period's group relationship.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transaction_period_payer", "period_id", "payer_id"),
        Index("ix_transaction_period_created", "period_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_kind: Mapped[str] = mapped_column(
        String(50),
        CheckConstraint("transaction_kind IN ('expense', 'deposit', 'refund')"),
        nullable=False,
    )
    split_kind: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("split_kind IN ('personal', 'equal', 'amount', 'percentage')"),
        default="equal",
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Stored in cents
    payer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("periods.id"), nullable=False, index=True)

    # Relationships
    payer: Mapped[User] = relationship(
        "User",
        foreign_keys="Transaction.payer_id",
        back_populates="paid_transactions",
    )
    category: Mapped[Category] = relationship("Category", back_populates="transactions")
    period: Mapped[Period] = relationship("Period", back_populates="transactions")
    expense_shares: Mapped[list[ExpenseShare]] = relationship(
        "ExpenseShare",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )

    @validates("transaction_kind")
    def validate_transaction_kind(self, key: str, value: str | TransactionKind) -> str:
        """Ensure transaction_kind is a valid TransactionKind value."""
        if isinstance(value, TransactionKind):
            return value.value
        valid_values = [k.value for k in TransactionKind]
        if value not in valid_values:
            raise ValueError(f"Invalid transaction_kind: {value}. Must be one of {valid_values}")
        return value

    @validates("split_kind")
    def validate_split_kind(self, key: str, value: str | SplitKind) -> str:
        """Ensure split_kind is a valid SplitKind value."""
        if isinstance(value, SplitKind):
            return value.value
        valid_values = [k.value for k in SplitKind]
        if value not in valid_values:
            raise ValueError(f"Invalid split_kind: {value}. Must be one of {valid_values}")
        return value

    @property
    def payer_name(self) -> str | None:
        """Get payer name from relationship."""
        return self.payer.name if self.payer else None

    @property
    def category_name(self) -> str | None:
        """Get category name from relationship."""
        return self.category.name if self.category else None

    @property
    def period_name(self) -> str | None:
        """Get period name from relationship."""
        return self.period.name if self.period else None

    @property
    def shared_by_users(self) -> list[User]:
        """Get all users who share in this transaction."""
        return [share.user for share in self.expense_shares]

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, kind='{self.transaction_kind}', "
            f"amount={self.amount}, payer_id={self.payer_id}, split='{self.split_kind}')>"
        )


class IdentityProvider(str, Enum):
    """Supported identity providers."""

    MICROSOFT = "microsoft"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class UserIdentity(TimestampMixin, Base):
    """Links external identity providers to user accounts."""

    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("identity_provider", "external_id", name="uq_provider_external_id"),
        Index("ix_user_identity_user", "user_id"),
        Index("ix_user_identity_provider", "identity_provider"),
        Index("ix_user_identity_external_id", "external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    identity_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Provider's unique user ID
    external_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Email from provider
    external_username: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Username from provider

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="identities")
    account_link_requests: Mapped[list[AccountLinkRequest]] = relationship(
        "AccountLinkRequest", back_populates="user_identity"
    )

    @validates("identity_provider")
    def validate_identity_provider(self, key: str, value: str | IdentityProvider) -> str:
        """Ensure identity_provider is a valid IdentityProvider value."""
        if isinstance(value, IdentityProvider):
            return value.value
        valid_values = [p.value for p in IdentityProvider]
        if value not in valid_values:
            raise ValueError(f"Invalid identity_provider: {value}. Must be one of {valid_values}")
        return value

    def __repr__(self) -> str:
        return (
            f"<UserIdentity(id={self.id}, provider='{self.identity_provider}', "
            f"user_id={self.user_id}, external_id='{self.external_id}')>"
        )


class AccountLinkRequestStatus(str, Enum):
    """Status of account link requests."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class AccountLinkRequest(TimestampMixin, Base):
    """Pending account linking requests requiring verification."""

    __tablename__ = "account_link_requests"
    __table_args__ = (
        Index("ix_link_request_token", "request_token"),
        Index("ix_link_request_user_identity", "user_identity_id"),
        Index("ix_link_request_status", "status"),
        Index("ix_link_request_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_identity_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_identities.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('pending', 'approved', 'denied', 'expired')"),
        default=AccountLinkRequestStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user_identity: Mapped[UserIdentity] = relationship("UserIdentity", back_populates="account_link_requests")

    @validates("status")
    def validate_status(self, key: str, value: str | AccountLinkRequestStatus) -> str:
        """Ensure status is a valid AccountLinkRequestStatus value."""
        if isinstance(value, AccountLinkRequestStatus):
            return value.value
        valid_values = [s.value for s in AccountLinkRequestStatus]
        if value not in valid_values:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_values}")
        return value

    def __repr__(self) -> str:
        return (
            f"<AccountLinkRequest(id={self.id}, token='{self.request_token[:8]}...', "
            f"user_identity_id={self.user_identity_id}, status='{self.status}')>"
        )
