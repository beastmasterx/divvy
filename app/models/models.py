"""
SQLAlchemy ORM models for the Divvy application.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class Member(Base):
    """Member model representing users in the expense splitting system."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    paid_remainder_in_cycle: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    transactions_as_payer: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.payer_id",
        back_populates="payer",
    )

    def __repr__(self) -> str:
        return f"<Member(id={self.id}, email='{self.email}', name='{self.name}', is_active={self.is_active})>"


class Period(Base):
    """Period model representing settlement periods."""

    __tablename__ = "periods"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_settled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    settled_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="period"
    )

    def __repr__(self) -> str:
        return f"<Period(id={self.id}, name='{self.name}', is_settled={self.is_settled})>"


class Category(Base):
    """Category model for transaction categorization."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Transaction(Base):
    """Transaction model for expenses, deposits, and refunds."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'expense', 'deposit', 'refund'
    description: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    amount: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Stored in cents
    payer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=True, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )
    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("periods.id"), nullable=False, index=True
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    # Relationships
    payer: Mapped["Member | None"] = relationship(
        "Member",
        foreign_keys="Transaction.payer_id",
        back_populates="transactions_as_payer",
    )
    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="transactions"
    )
    period: Mapped["Period"] = relationship(
        "Period", back_populates="transactions"
    )

    @property
    def payer_name(self) -> str | None:
        """Get payer name from relationship."""
        return self.payer.name if self.payer else None

    @property
    def category_name(self) -> str | None:
        """Get category name from relationship."""
        return self.category.name if self.category else None

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, type='{self.transaction_type}', "
            f"amount={self.amount}, payer_id={self.payer_id})>"
        )
