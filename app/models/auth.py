"""
Authentication and identity-related models.

This module contains models for managing user authentication, including:
- Refresh tokens for session management
- User identities for OAuth/SSO providers
- Account link requests for linking external identities to existing accounts
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class IdentityProviderName(str, Enum):
    """Supported identity provider names."""

    MICROSOFT = "microsoft"
    GOOGLE = "google"
    FACEBOOK = "facebook"


class AccountLinkRequestStatus(str, Enum):
    """Status of account link requests.

    Status values:
    - pending: Request is waiting for approval
    - approved: Request has been approved and identity is linked
    """

    PENDING = "pending"
    APPROVED = "approved"


class RefreshToken(TimestampMixin, Base):
    """RefreshToken model for managing refresh tokens."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_token_user_revoked", "user_id", "is_revoked"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id='{self.id}', user_id={self.user_id}, is_revoked={self.is_revoked})>"


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

    @validates("identity_provider")
    def validate_identity_provider(self, key: str, value: str | IdentityProviderName) -> str:
        """Ensure identity_provider is a valid IdentityProviderName value."""
        if isinstance(value, IdentityProviderName):
            return value.value
        valid_values = [p.value for p in IdentityProviderName]
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
        Index("ix_link_request_user", "user_id"),
        Index("ix_link_request_status", "status"),
        Index("ix_link_request_expires", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    identity_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Provider's unique user ID
    external_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Email from provider
    external_username: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Username from provider
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('pending', 'approved')"),
        default=AccountLinkRequestStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    user: Mapped[User] = relationship("User")

    @validates("status")
    def validate_status(self, key: str, value: str | AccountLinkRequestStatus) -> str:
        """Ensure status is a valid AccountLinkRequestStatus value."""
        if isinstance(value, AccountLinkRequestStatus):
            return value.value
        valid_values = [s.value for s in AccountLinkRequestStatus]
        if value not in valid_values:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_values}")
        return value

    @validates("identity_provider")
    def validate_identity_provider(self, key: str, value: str | IdentityProviderName) -> str:
        """Ensure identity_provider is a valid IdentityProviderName value."""
        if isinstance(value, IdentityProviderName):
            return value.value
        valid_values = [p.value for p in IdentityProviderName]
        if value not in valid_values:
            raise ValueError(f"Invalid identity_provider: {value}. Must be one of {valid_values}")
        return value

    def __repr__(self) -> str:
        return (
            f"<AccountLinkRequest(id={self.id}, token='{self.request_token[:8]}...', "
            f"user_id={self.user_id}, provider='{self.identity_provider}', status='{self.status}')>"
        )
