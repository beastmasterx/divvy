"""
Period-related models.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base

if TYPE_CHECKING:
    from .group import Group
    from .transaction import Transaction


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
