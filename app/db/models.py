"""
SQLAlchemy ORM models for the Divvy application.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""
from datetime import datetime, timezone

# UTC timezone - Python 3.11+ has datetime.UTC, older versions use timezone.utc
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Member(Base):
    """Member model representing users in the expense splitting system."""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    paid_remainder_in_cycle = Column(Boolean, default=False, nullable=False)

    # Relationships
    transactions_as_payer = relationship(
        "Transaction", foreign_keys="Transaction.payer_id", back_populates="payer"
    )

    def to_dict(self) -> dict:
        """Convert model instance to dictionary (for backwards compatibility)."""
        return {
            "id": self.id,
            "name": self.name,
            "is_active": int(self.is_active) if isinstance(self.is_active, bool) else self.is_active,
            "paid_remainder_in_cycle": (
                int(self.paid_remainder_in_cycle)
                if isinstance(self.paid_remainder_in_cycle, bool)
                else self.paid_remainder_in_cycle
            ),
        }

    def __repr__(self) -> str:
        return f"<Member(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class Period(Base):
    """Period model representing settlement periods."""
    __tablename__ = "periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    start_date = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    end_date = Column(DateTime, nullable=True)
    is_settled = Column(Boolean, default=False, nullable=False)
    settled_date = Column(DateTime, nullable=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="period")

    def to_dict(self) -> dict:
        """Convert model instance to dictionary (for backwards compatibility)."""
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "is_settled": int(self.is_settled) if isinstance(self.is_settled, bool) else self.is_settled,
            "settled_date": self.settled_date,
        }

    def __repr__(self) -> str:
        return f"<Period(id={self.id}, name='{self.name}', is_settled={self.is_settled})>"


class Category(Base):
    """Category model for transaction categorization."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="category")

    def to_dict(self) -> dict:
        """Convert model instance to dictionary (for backwards compatibility)."""
        return {
            "id": self.id,
            "name": self.name,
        }

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"


class Transaction(Base):
    """Transaction model for expenses, deposits, and refunds."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_type = Column(String(50), nullable=False)  # 'expense', 'deposit', 'refund'
    description = Column(String(1000), nullable=True)
    amount = Column(Integer, nullable=False)  # Stored in cents
    payer_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=False, index=True)
    is_personal = Column(Boolean, default=False, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True)

    # Relationships
    payer = relationship("Member", foreign_keys=[payer_id], back_populates="transactions_as_payer")
    category = relationship("Category", back_populates="transactions")
    period = relationship("Period", back_populates="transactions")

    def to_dict(self) -> dict:
        """Convert model instance to dictionary (for backwards compatibility)."""
        # Note: SQLite uses 'TIMESTAMP' as column name, but SQLAlchemy uses 'timestamp'
        # Handle both for compatibility
        result = {
            "id": self.id,
            "transaction_type": self.transaction_type,
            "description": self.description,
            "amount": self.amount,
            "payer_id": self.payer_id,
            "category_id": self.category_id,
            "period_id": self.period_id,
            "is_personal": (
                int(self.is_personal) if isinstance(self.is_personal, bool) else self.is_personal
            ),
            "TIMESTAMP": self.timestamp,  # Keep uppercase for backwards compatibility
            "timestamp": self.timestamp,  # Also provide lowercase
        }
        return result

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, type='{self.transaction_type}', "
            f"amount={self.amount}, payer_id={self.payer_id})>"
        )

