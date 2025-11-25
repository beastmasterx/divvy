"""
Group-related models.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base

if TYPE_CHECKING:
    from .authorization import GroupRoleBinding
    from .period import Period


class Group(AuditMixin, Base):
    """Group model representing groups in the expense splitting system."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    periods: Mapped[list[Period]] = relationship("Period", back_populates="group", cascade="all, delete-orphan")
    # Role bindings represent both membership and roles in the group
    role_bindings: Mapped[list[GroupRoleBinding]] = relationship(
        "GroupRoleBinding", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name='{self.name}')>"
