"""
SQLAlchemy database models.
"""

from .models import (
    Base,
    Category,
    ExpenseShare,
    Group,
    GroupUser,
    Period,
    RefreshToken,
    SplitKind,
    Transaction,
    TransactionKind,
    User,
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
    "Base",
    "Category",
    "ExpenseShare",
    "Group",
    "GroupUser",
    "Period",
    "RefreshToken",
    "SplitKind",
    "Transaction",
    "TransactionKind",
    "User",
]
