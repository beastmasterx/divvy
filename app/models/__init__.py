"""
SQLAlchemy database models.
"""

from app.models.base import AuditMixin, Base, TimestampMixin
from app.models.group import Group, GroupUser
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

default_categories = [
    "Utilities (Water & Electricity & Gas)",
    "Groceries",
    "Daily Necessities",
    "Rent",
    "Settlement",
    "Other",
]

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
    # User
    "User",
    "RefreshToken",
    "UserIdentity",
    "AccountLinkRequest",
    # Group
    "Group",
    "GroupUser",
    # Period
    "Period",
    # Transaction
    "Transaction",
    "ExpenseShare",
    "Category",
    # Constants
    "default_categories",
]
