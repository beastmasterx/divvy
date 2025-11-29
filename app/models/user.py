"""
User model.

This module contains the core User model representing users in the expense splitting system.
Authentication-related models (RefreshToken, UserIdentity, AccountLinkRequest) are in auth.py.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .auth import RefreshToken, UserIdentity
    from .authorization import GroupRoleBinding, SystemRoleBinding
    from .transaction import ExpenseShare, Transaction


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
    # Authorization relationships
    system_role_bindings: Mapped[list[SystemRoleBinding]] = relationship(
        "SystemRoleBinding", back_populates="user", cascade="all, delete-orphan"
    )
    group_role_bindings: Mapped[list[GroupRoleBinding]] = relationship(
        "GroupRoleBinding", foreign_keys="GroupRoleBinding.user_id", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', is_active={self.is_active})>"
