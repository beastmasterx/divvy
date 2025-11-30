"""
Transaction-related models.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base, TimestampMixin

if TYPE_CHECKING:
    from .period import Period
    from .user import User


class TransactionKind(str, Enum):
    """
    Enumeration of transaction types in the expense splitting system.

    Attributes:
        EXPENSE: Standard expense transaction where a user pays for something
                 shared with others.
        DEPOSIT: Money deposited into the group's shared pool.
        REFUND: Money returned or refunded to participants.
    """

    EXPENSE = "expense"
    DEPOSIT = "deposit"
    REFUND = "refund"


class TransactionStatus(str, Enum):
    """
    Enumeration of transaction lifecycle states.

    Attributes:
        DRAFT: Transaction is being created or edited. Not yet finalized.
        PENDING: Transaction is submitted and awaiting approval.
        APPROVED: Transaction has been approved and is active in the period.
        REJECTED: Transaction has been rejected and will not be processed.
    """

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SplitKind(str, Enum):
    """
    Enumeration of methods for splitting transaction costs among users.

    Attributes:
        PERSONAL: Only the payer bears the cost (no split among participants).
        EQUAL: Split equally among all participants in the transaction.
        AMOUNT: Custom fixed amounts per person (specified in cents).
        PERCENTAGE: Custom percentage allocation per person (0.0 to 100.0).
    """

    PERSONAL = "personal"
    EQUAL = "equal"
    AMOUNT = "amount"
    PERCENTAGE = "percentage"


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
    transaction_kind: Mapped[TransactionKind] = mapped_column(
        String(50),
        nullable=False,
    )
    split_kind: Mapped[SplitKind] = mapped_column(
        String(20),
        default=SplitKind.PERSONAL,
        nullable=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        default=TransactionStatus.DRAFT,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Stored in cents
    date_incurred: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
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


class Settlement(AuditMixin, Base):
    """
    Settlement model representing actual money transfers between users to balance a period's debt.
    """

    __tablename__ = "settlements"
    __table_args__ = (Index("ix_settlement_period_payer_payee", "period_id", "payer_id", "payee_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("periods.id"), nullable=False, index=True)
    payer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Stored in cents
    date_paid: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    period: Mapped[Period] = relationship("Period", back_populates="settlements")
    payer: Mapped[User] = relationship("User", foreign_keys="Settlement.payer_id")
    payee: Mapped[User] = relationship("User", foreign_keys="Settlement.payee_id")

    @property
    def period_name(self) -> str | None:
        """Get period name from relationship."""
        return self.period.name if self.period else None

    @property
    def payer_name(self) -> str | None:
        """Get payer name from relationship."""
        return self.payer.name if self.payer else None

    @property
    def payee_name(self) -> str | None:
        """Get payee name from relationship."""
        return self.payee.name if self.payee else None

    def __repr__(self) -> str:
        return (
            f"<Settlement(id={self.id}, period_id={self.period_id}, "
            f"payer={self.payer_id} -> payee={self.payee_id}, amount={self.amount})>"
        )
