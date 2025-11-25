"""
Transaction-related models.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import AuditMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from .period import Period
    from .user import User


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
