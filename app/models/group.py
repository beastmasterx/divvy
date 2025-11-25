"""
Group-related models.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AuditMixin, Base

if TYPE_CHECKING:
    from .period import Period
    from .user import User


class Group(AuditMixin, Base):
    """Group model representing groups in the expense splitting system."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    owner: Mapped[User] = relationship("User", foreign_keys="Group.owner_id", back_populates="owned_groups")
    group_users: Mapped[list[GroupUser]] = relationship(
        "GroupUser", back_populates="group", cascade="all, delete-orphan"
    )
    periods: Mapped[list[Period]] = relationship("Period", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name='{self.name}')>"


class GroupUser(AuditMixin, Base):
    """GroupUser model representing the relationship between a group and a user."""

    __tablename__ = "group_users"

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)

    # Relationships
    group: Mapped[Group] = relationship("Group", back_populates="group_users")
    user: Mapped[User] = relationship("User", foreign_keys="GroupUser.user_id", back_populates="group_users")

    def __repr__(self) -> str:
        return f"<GroupUser(group_id={self.group_id}, user_id={self.user_id})>"
