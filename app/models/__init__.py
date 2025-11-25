"""
SQLAlchemy database models.
"""

from app.models.authorization import (
    GroupRole,
    GroupRoleBinding,
    Permission,
    RolePermission,
    SystemRole,
    SystemRoleBinding,
)
from app.models.base import AuditMixin, Base, TimestampMixin
from app.models.group import Group
from app.models.period import Period
from app.models.transaction import Category, ExpenseShare, SplitKind, Transaction, TransactionKind
from app.models.user import (
    AccountLinkRequest,
    AccountLinkRequestStatus,
    IdentityProvider,
    RefreshToken,
    User,
    UserIdentity,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "AuditMixin",
    # Enums
    "TransactionKind",
    "SplitKind",
    "IdentityProvider",
    "AccountLinkRequestStatus",
    # Authorization
    "SystemRole",
    "GroupRole",
    "Permission",
    "SystemRoleBinding",
    "RolePermission",
    "GroupRoleBinding",
    # User
    "User",
    "RefreshToken",
    "UserIdentity",
    "AccountLinkRequest",
    # Group
    "Group",
    # Period
    "Period",
    # Transaction
    "Transaction",
    "ExpenseShare",
    "Category",
]
