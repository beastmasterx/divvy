"""
SQLAlchemy database models.
"""

from .models import (
    AccountLinkRequest,
    AccountLinkRequestStatus,
    Base,
    Category,
    ExpenseShare,
    Group,
    GroupUser,
    IdentityProvider,
    Period,
    RefreshToken,
    SplitKind,
    Transaction,
    TransactionKind,
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
    "AccountLinkRequest",
    "AccountLinkRequestStatus",
    "Base",
    "Category",
    "ExpenseShare",
    "Group",
    "GroupUser",
    "IdentityProvider",
    "Period",
    "RefreshToken",
    "SplitKind",
    "Transaction",
    "TransactionKind",
    "User",
    "UserIdentity",
]
