"""
Period-related models.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base

if TYPE_CHECKING:
    from .group import Group
    from .transaction import Settlement, Transaction


class PeriodStatus(str, Enum):
    """
    Enumeration of period lifecycle states.

    Attributes:
        OPEN: Active period allowing transaction creation and modification.
              Balances are calculated dynamically as transactions change.
        CLOSED: Period locked for new transactions. Used for reconciliation
                and final reporting. Balances are finalized. May be reopened
                by administrators if needed.
        SETTLED: Final immutable state indicating all outstanding balances
                 have been paid. This status cannot be changed once set.
    """

    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


class Period(AuditMixin, Base):
    """Period model representing settlement periods.

    Each period belongs to a group and defines a timeframe for expense tracking and settlement.
    """

    __tablename__ = "periods"
    __table_args__ = (Index("ix_period_group_dates", "group_id", "start_date", "end_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(String(20), nullable=False, default=PeriodStatus.OPEN)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="periods")
    transactions: Mapped[list[Transaction]] = relationship("Transaction", back_populates="period")
    settlements: Mapped[list[Settlement]] = relationship("Settlement", back_populates="period")

    def __repr__(self) -> str:
        return f"<Period(id={self.id}, name='{self.name}', status='{self.status}', start_date={self.start_date}, end_date={self.end_date})>"
