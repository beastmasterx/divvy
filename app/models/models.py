"""
SQLAlchemy ORM models for the Divvy application.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Mapper, mapped_column, relationship, validates


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
    CUSTOM = "custom"  # Custom amounts per person


class TimestampMixin:
    """Mixin to add automatic timestamp tracking to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), index=True
    )


class AuditMixin(TimestampMixin):
    """Mixin to add full audit trail (timestamps + user tracking) to models."""

    created_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    updated_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class Group(AuditMixin, Base):
    """Group model representing groups in the expense splitting system."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    group_users: Mapped[list[GroupUser]] = relationship(
        "GroupUser", back_populates="group", cascade="all, delete-orphan"
    )
    periods: Mapped[list[Period]] = relationship("Period", back_populates="group", cascade="all, delete-orphan")
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="group")

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name='{self.name}')>"


class User(TimestampMixin, Base):
    """User model representing users in the expense splitting system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    group_users: Mapped[list[GroupUser]] = relationship("GroupUser", back_populates="user")
    paid_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", foreign_keys="Transaction.payer_id", back_populates="payer"
    )
    expense_shares: Mapped[list[ExpenseShare]] = relationship("ExpenseShare", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', is_active={self.is_active})>"


class GroupUser(AuditMixin, Base):
    """GroupUser model representing the relationship between a group and a user."""

    __tablename__ = "group_users"

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="group_users")
    user: Mapped[User] = relationship("User", back_populates="group_users")

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
    user: Mapped[User] = relationship("User", back_populates="expense_shares")

    def __repr__(self) -> str:
        return f"<ExpenseShare(transaction_id={self.transaction_id}, user_id={self.user_id})>"


class Period(AuditMixin, Base):
    """Period model representing settlement periods.

    Each period belongs to a group and defines a timeframe for expense tracking and settlement.
    """

    __tablename__ = "periods"
    __table_args__ = (
        Index("ix_period_group_settled", "group_id", "is_settled"),
        Index("ix_period_group_dates", "group_id", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settled_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="periods")
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="period")

    @property
    def is_active(self) -> bool:
        """Check if this period is currently active (not ended or settled)."""
        now = datetime.now(UTC)
        return not self.is_settled and self.start_date <= now and (self.end_date is None or self.end_date >= now)

    def __repr__(self) -> str:
        return f"<Period(id={self.id}, name='{self.name}', is_settled={self.is_settled})>"


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

    Transactions belong to both a period and a group. Since periods belong to groups,
    the group_id is typically derived from the period's group, but can be set explicitly.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transaction_period_payer", "period_id", "payer_id"),
        Index("ix_transaction_group_period", "group_id", "period_id"),
        Index("ix_transaction_period_created", "period_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_kind: Mapped[str] = mapped_column(
        String(50), CheckConstraint("transaction_kind IN ('expense', 'deposit', 'refund')"), nullable=False
    )
    split_kind: Mapped[str] = mapped_column(
        String(20), CheckConstraint("split_kind IN ('personal', 'equal', 'custom')"), default="equal", nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Stored in cents
    payer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    period_id: Mapped[int] = mapped_column(Integer, ForeignKey("periods.id"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    # DEPRECATED: Use split_kind == 'personal' instead. This field is kept for backward compatibility.
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # DEPRECATED: Use created_at instead. This field is kept for backward compatibility.
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)

    # Relationships
    payer: Mapped[User] = relationship("User", foreign_keys="Transaction.payer_id", back_populates="paid_transactions")
    category: Mapped[Category] = relationship("Category", back_populates="transactions")
    period: Mapped[Period] = relationship("Period", back_populates="transactions")
    group: Mapped[Group] = relationship("Group", back_populates="transactions")
    expense_shares: Mapped[list[ExpenseShare]] = relationship(
        "ExpenseShare", back_populates="transaction", cascade="all, delete-orphan"
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

    def validate_shares_consistency(self) -> None:
        """Validate that expense shares are consistent with split_kind.

        Should be called after adding/modifying expense shares before commit.

        Raises:
            ValueError: If shares are inconsistent with split_kind.
        """
        num_shares = len(self.expense_shares)

        # Personal split should have exactly one share
        if self.split_kind == SplitKind.PERSONAL.value:
            if num_shares != 1:
                raise ValueError(
                    f"Transaction {self.id} has split_kind='personal' but has {num_shares} shares. "
                    f"Personal transactions must have exactly 1 share."
                )
            # Optionally verify the single share is the payer
            if self.expense_shares[0].user_id != self.payer_id:
                raise ValueError(
                    f"Transaction {self.id} has split_kind='personal' but the share is not for the payer. "
                    f"Personal expenses must be shared only by the payer."
                )

        # Equal and custom splits should have at least one share (preferably 2+)
        elif self.split_kind in (SplitKind.EQUAL.value, SplitKind.CUSTOM.value):
            if num_shares < 1:
                raise ValueError(
                    f"Transaction {self.id} has split_kind='{self.split_kind}' but has no expense shares. "
                    f"At least one share is required."
                )

            # For custom splits, validate that shares add up to transaction amount
            if self.split_kind == SplitKind.CUSTOM.value:
                total_amount = 0
                total_percentage = 0.0
                uses_amount = False
                uses_percentage = False

                for share in self.expense_shares:
                    if share.share_amount is not None:
                        total_amount += share.share_amount
                        uses_amount = True
                    elif share.share_percentage is not None:
                        total_percentage += share.share_percentage
                        uses_percentage = True
                    else:
                        raise ValueError(
                            f"Transaction {self.id} has split_kind='custom' but ExpenseShare for user "
                            f"{share.user_id} has neither share_amount nor share_percentage specified."
                        )

                # Cannot mix amounts and percentages
                if uses_amount and uses_percentage:
                    raise ValueError(
                        f"Transaction {self.id} has split_kind='custom' with mixed share_amount and "
                        f"share_percentage. All shares must use the same method."
                    )

                # Validate totals
                if uses_amount and total_amount != self.amount:
                    raise ValueError(
                        f"Transaction {self.id} custom share amounts total {total_amount} cents but "
                        f"transaction amount is {self.amount} cents. They must match."
                    )

                # Validate that the percentages add up to 100.0%
                if uses_percentage and abs(total_percentage - 100.0) > 0.0:
                    raise ValueError(
                        f"Transaction {self.id} custom share percentages total {total_percentage}% but "
                        f"must equal 100%. Current total: {total_percentage}%"
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
    def shared_by_users(self) -> list[User]:
        """Get all users who share in this transaction."""
        return [share.user for share in self.expense_shares]

    def validate_and_auto_fix_group(self) -> None:
        """Ensure transaction's group_id matches its period's group_id.

        Auto-fixes if group_id is None by setting it from period.
        Raises ValueError if they mismatch.
        """
        if self.period and self.period.group_id and self.group_id != self.period.group_id:
            raise ValueError(
                f"Transaction {self.id} group_id ({self.group_id}) doesn't match "
                f"period's group_id ({self.period.group_id})"
            )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, kind='{self.transaction_kind}', "
            f"amount={self.amount}, payer_id={self.payer_id}, split='{self.split_kind}')>"
        )


# Event listeners for automatic validation
@event.listens_for(Transaction, "before_insert")
@event.listens_for(Transaction, "before_update")
def validate_transaction_before_save(mapper: Mapper[Any], connection: Any, target: Transaction) -> None:
    """Automatically validate transaction consistency before insert/update."""
    target.validate_shares_consistency()
