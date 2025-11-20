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
    "Other",
]

__all__ = [
    "Base",
    "Category",
    "ExpenseShare",
    "Group",
    "GroupUser",
    "Period",
    "SplitKind",
    "Transaction",
    "TransactionKind",
    "User",
]
