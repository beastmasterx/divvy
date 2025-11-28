"""
Authorization and RBAC-related models.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .base import AuditMixin, Base

if TYPE_CHECKING:
    from .group import Group
    from .user import User


class SystemRole(str, Enum):
    """System-wide roles."""

    ADMIN = "system:admin"
    USER = "system:user"


class GroupRole(str, Enum):
    """Roles within a group context."""

    OWNER = "group:owner"
    ADMIN = "group:admin"
    MEMBER = "group:member"


class SystemRoleBinding(Base):
    """System-wide role binding (user → role at system level)."""

    __tablename__ = "system_role_bindings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_system_role"),
        Index("ix_system_role_binding_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="system_role_bindings")

    @validates("role")
    def validate_role(self, key: str, value: str | SystemRole) -> str:
        """Ensure role is a valid SystemRole value."""
        if isinstance(value, SystemRole):
            return value.value
        valid_values = [r.value for r in SystemRole]
        if value not in valid_values:
            raise ValueError(f"Invalid system role: {value}. Must be one of {valid_values}")
        return value

    def __repr__(self) -> str:
        return f"<SystemRoleBinding(user_id={self.user_id}, role='{self.role}')>"


class GroupRoleBinding(AuditMixin, Base):
    """Group-level role binding (authorization and membership).

    This represents: "User X has role Y in group Z"
    - Membership: If a user has any GroupRoleBinding for a group, they are a member
    - Authorization: The role determines what actions the user can perform in the group

    This is the group-level equivalent of SystemRoleBinding (system-level).
    """

    __tablename__ = "group_role_bindings"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_group_role"),
        Index("ix_group_role_binding_user", "user_id"),
        Index("ix_group_role_binding_group", "group_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id], back_populates="group_role_bindings")
    group: Mapped[Group] = relationship("Group", back_populates="role_bindings")

    @validates("role")
    def validate_role(self, key: str, value: str | GroupRole) -> str:
        """Ensure role is a valid GroupRole value."""
        if isinstance(value, GroupRole):
            return value.value
        valid_values = [r.value for r in GroupRole]
        if value not in valid_values:
            raise ValueError(f"Invalid group role: {value}. Must be one of {valid_values}")
        return value

    def __repr__(self) -> str:
        return f"<GroupRoleBinding(user_id={self.user_id}, group_id={self.group_id}, role='{self.role}')>"
