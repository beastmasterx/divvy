"""
User and authentication-related models.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .group import Group, GroupUser
    from .transaction import ExpenseShare, Transaction


class IdentityProvider(str, Enum):
    """Supported identity providers."""

    MICROSOFT = "microsoft"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class AccountLinkRequestStatus(str, Enum):
    """Status of account link requests."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


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
        "Transaction", foreign_keys="Transaction.payer_id", back_populates="payer"
    )
    expense_shares: Mapped[list[ExpenseShare]] = relationship(
        "ExpenseShare", foreign_keys="ExpenseShare.user_id", back_populates="user"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
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
