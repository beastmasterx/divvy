"""
Database module for Divvy application.
Refactored to use SQLAlchemy ORM while maintaining backwards compatibility.
Supports SQLite, PostgreSQL, MySQL, and MSSQL via environment variable DIVVY_DATABASE_URL.
"""
import logging
import os
from datetime import datetime, timezone
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

# UTC timezone - Python 3.11+ has datetime.UTC, older versions use timezone.utc
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

# Module-level logger
logger = logging.getLogger(__name__)

# Import ORM components from submodules
from .connection import (
    create_engine_from_url,
    get_database_url,
    get_engine,
    reset_engine,
)
from .models import Base, Category, Member, Period, Transaction
from .session import create_session, get_session

# Virtual member constants
PUBLIC_FUND_MEMBER_INTERNAL_NAME = "_system_group_"
SYSTEM_MEMBER_PREFIX = "_system_"


def initialize_database():
    """
    Initializes the database by creating tables.
    Uses SQLAlchemy to create tables, which works across all database types.
    """
    engine = get_engine()
    
    # Check if tables exist (database-agnostic check)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "members" in existing_tables:
        # Database already initialized
        initialize_first_period_if_needed()
        ensure_virtual_member_exists()
        return
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Pre-populate default categories
    with get_session() as session:
        default_categories = [
            "Utilities (Water & Electricity & Gas)",
            "Groceries",
            "Daily Necessities",
            "Rent",
            "Other",
        ]
        
        for cat_name in default_categories:
            # Check if category already exists
            existing = session.query(Category).filter_by(name=cat_name).first()
            if not existing:
                session.add(Category(name=cat_name))
        session.commit()
    
    logger.info("Database initialized successfully.")
    # Ensure current period exists after initialization
    initialize_first_period_if_needed()
    # Ensure virtual member exists
    ensure_virtual_member_exists()


# --- Database operations for Members ---


def add_member(name: str) -> int | None:
    """Adds a new member to the database and returns their ID, or None if already exists."""
    with get_session() as session:
        try:
            member = Member(name=name)
            session.add(member)
            session.flush()  # Get the ID without committing yet
            member_id = member.id
            session.commit()
            return member_id
        except IntegrityError:
            session.rollback()
            return None


def get_member_by_name(name: str) -> dict | None:
    """Retrieves a member by their name."""
    with get_session() as session:
        member = session.query(Member).filter_by(name=name).first()
        return member.to_dict() if member else None


def get_member_by_id(member_id: int) -> dict | None:
    """Retrieves a member by their ID."""
    with get_session() as session:
        member = session.query(Member).filter_by(id=member_id).first()
        return member.to_dict() if member else None


def get_all_members() -> list[dict]:
    """Retrieves all members, active or inactive (excluding virtual member)."""
    with get_session() as session:
        members = (
            session.query(Member)
            .filter(Member.name != PUBLIC_FUND_MEMBER_INTERNAL_NAME)
            .order_by(Member.id)
            .all()
        )
        return [m.to_dict() for m in members]


def get_active_members() -> list[dict]:
    """Retrieves all active members (excluding virtual member)."""
    with get_session() as session:
        members = (
            session.query(Member)
            .filter(Member.is_active.is_(True), Member.name != PUBLIC_FUND_MEMBER_INTERNAL_NAME)
            .order_by(Member.id)
            .all()
        )
        return [m.to_dict() for m in members]


def update_member_remainder_status(member_id: int, status: bool):
    """Updates the paid_remainder_in_cycle status for a member."""
    with get_session() as session:
        member = session.query(Member).filter_by(id=member_id).first()
        if member:
            member.paid_remainder_in_cycle = status
            session.commit()


def reset_all_member_remainder_status():
    """Resets paid_remainder_in_cycle to False for all active members."""
    with get_session() as session:
        session.query(Member).filter(Member.is_active.is_(True)).update(
            {"paid_remainder_in_cycle": False}
        )
        session.commit()


def deactivate_member(member_id: int) -> bool:
    """Deactivates a member by setting is_active to 0. Returns True if successful."""
    with get_session() as session:
        result = session.query(Member).filter_by(id=member_id).update({"is_active": False})
        session.commit()
        return result > 0


def reactivate_member(member_id: int) -> bool:
    """Reactivates a member by setting is_active to 1. Returns True if successful."""
    with get_session() as session:
        result = session.query(Member).filter_by(id=member_id).update({"is_active": True})
        session.commit()
        return result > 0


# --- Database operations for Periods ---


def get_current_period() -> dict | None:
    """Gets the current active (unsettled) period."""
    with get_session() as session:
        period = (
            session.query(Period)
            .filter(Period.is_settled.is_(False))
            .order_by(Period.start_date.desc())
            .first()
        )
        return period.to_dict() if period else None


def create_new_period(name: str) -> int:
    """Creates a new settlement period and returns its ID."""
    with get_session() as session:
        period = Period(name=name, start_date=datetime.now(UTC), is_settled=False)
        session.add(period)
        session.flush()
        period_id = period.id
        session.commit()
        return period_id


def settle_period(period_id: int) -> bool:
    """Marks a period as settled and sets the end date."""
    with get_session() as session:
        now = datetime.now(UTC)
        result = (
            session.query(Period)
            .filter_by(id=period_id)
            .update(
                {
                    "is_settled": True,
                    "end_date": now,
                    "settled_date": now,
                }
            )
        )
        session.commit()
        return result > 0


def get_period_by_id(period_id: int) -> dict | None:
    """Retrieves a period by its ID."""
    with get_session() as session:
        period = session.query(Period).filter_by(id=period_id).first()
        return period.to_dict() if period else None


def get_all_periods() -> list[dict]:
    """Retrieves all periods, ordered by start_date descending."""
    with get_session() as session:
        periods = session.query(Period).order_by(Period.start_date.desc()).all()
        return [p.to_dict() for p in periods]


def get_transactions_by_period(period_id: int) -> list[dict]:
    """Retrieves all transactions for a specific period."""
    with get_session() as session:
        transactions = (
            session.query(Transaction)
            .filter_by(period_id=period_id)
            .order_by(Transaction.timestamp)
            .all()
        )
        return [t.to_dict() for t in transactions]


def initialize_first_period_if_needed():
    """Ensures there's at least one period in the system."""
    # Check if periods table exists (database-agnostic)
    engine = get_engine()
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "periods" not in existing_tables:
        # Periods table doesn't exist yet - skip period initialization
        return
    
    if get_current_period() is None:
        create_new_period("Initial Period")


def ensure_virtual_member_exists():
    """Ensures the virtual member exists for shared expenses."""
    virtual_member = get_member_by_name(PUBLIC_FUND_MEMBER_INTERNAL_NAME)
    if not virtual_member:
        with get_session() as session:
            virtual_member_obj = Member(name=PUBLIC_FUND_MEMBER_INTERNAL_NAME, is_active=False)
            session.add(virtual_member_obj)
            session.commit()


def is_virtual_member(member: dict | None) -> bool:
    """Check if a member is the virtual/system member."""
    if not member:
        return False
    return member["name"].startswith(SYSTEM_MEMBER_PREFIX)


def get_member_display_name(member: dict) -> str:
    """Get display name for member (translates virtual member to user-friendly name)."""
    if is_virtual_member(member):
        from app.core.i18n import _
        return _("Group")  # Translatable display name
    return member["name"]


# --- Database operations for Transactions ---


def add_transaction(
    transaction_type: str,
    amount: int,
    description: str | None = None,
    payer_id: int | None = None,
    category_id: int | None = None,
    period_id: int | None = None,
    is_personal: bool = False,
) -> int:
    """
    Adds a new transaction to the database and returns its ID.
    If period_id is None, uses the current active period.
    is_personal: If True, expense only affects payer (not split among members).
    """
    if period_id is None:
        current_period = get_current_period()
        if current_period is None:
            initialize_first_period_if_needed()
            current_period = get_current_period()
        period_id = current_period["id"]

    with get_session() as session:
        transaction = Transaction(
            transaction_type=transaction_type,
            description=description,
            amount=amount,
            payer_id=payer_id,
            category_id=category_id,
            period_id=period_id,
            is_personal=is_personal,
            timestamp=datetime.now(UTC),
        )
        session.add(transaction)
        session.flush()
        transaction_id = transaction.id
        session.commit()
        return transaction_id


def get_all_transactions() -> list[dict]:
    """Retrieves all transactions."""
    with get_session() as session:
        transactions = session.query(Transaction).order_by(Transaction.timestamp).all()
        return [t.to_dict() for t in transactions]


def get_category_by_name(name: str) -> dict | None:
    """Retrieves a category by its name."""
    with get_session() as session:
        category = session.query(Category).filter_by(name=name).first()
        return category.to_dict() if category else None


def get_all_categories() -> list[dict]:
    """Retrieves all categories."""
    with get_session() as session:
        categories = session.query(Category).order_by(Category.name).all()
        return [c.to_dict() for c in categories]


def get_category_by_id(category_id: int) -> dict | None:
    """Retrieves a category by its ID."""
    with get_session() as session:
        category = session.query(Category).filter_by(id=category_id).first()
        return category.to_dict() if category else None


# Export all public API
__all__ = [
    # Constants
    "PUBLIC_FUND_MEMBER_INTERNAL_NAME",
    "SYSTEM_MEMBER_PREFIX",
    # Models
    "Base",
    "Member",
    "Period",
    "Category",
    "Transaction",
    # Session management
    "get_session",
    "create_session",
    # Connection management
    "get_engine",
    "get_database_url",
    "create_engine_from_url",
    "reset_engine",
    # Database operations
    "initialize_database",
    # Member operations
    "add_member",
    "get_member_by_name",
    "get_member_by_id",
    "get_all_members",
    "get_active_members",
    "update_member_remainder_status",
    "reset_all_member_remainder_status",
    "deactivate_member",
    "reactivate_member",
    "is_virtual_member",
    "get_member_display_name",
    # Period operations
    "get_current_period",
    "create_new_period",
    "settle_period",
    "get_period_by_id",
    "get_all_periods",
    "get_transactions_by_period",
    "initialize_first_period_if_needed",
    "ensure_virtual_member_exists",
    # Transaction operations
    "add_transaction",
    "get_all_transactions",
    # Category operations
    "get_category_by_name",
    "get_all_categories",
    "get_category_by_id",
]
