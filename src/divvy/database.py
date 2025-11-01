import os
import sqlite3

# Determine the absolute path to the project root and the database file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "expenses.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

# Virtual member for shared/public expenses
VIRTUAL_MEMBER_INTERNAL_NAME = "_system_group_"
SYSTEM_MEMBER_PREFIX = "_system_"


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn


def initialize_database():
    """Initializes the database by creating tables from the schema.sql file."""
    with get_db_connection() as conn:
        # Check if tables have already been created by checking for the 'members' table
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'")
        if cursor.fetchone():
            # Ensure there's a current period even if database was already initialized
            initialize_first_period_if_needed()
            # Ensure virtual member exists
            ensure_virtual_member_exists()
            return  # Database already initialized

        with open(SCHEMA_FILE) as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()

    print("Database initialized successfully.")
    # Ensure current period exists after initialization
    initialize_first_period_if_needed()
    # Ensure virtual member exists
    ensure_virtual_member_exists()


# --- Database operations for Members ---


def add_member(name: str) -> int | None:
    """Adds a new member to the database and returns their ID, or None if already exists."""
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO members (name) VALUES (?) RETURNING id", (name,))
            member_id = cursor.fetchone()[0]
            conn.commit()
            return member_id
        except sqlite3.IntegrityError:  # Name is UNIQUE
            return None


def get_member_by_name(name: str) -> dict | None:
    """Retrieves a member by their name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE name = ?", (name,))
        member = cursor.fetchone()
        return dict(member) if member else None


def get_member_by_id(member_id: int) -> dict | None:
    """Retrieves a member by their ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        member = cursor.fetchone()
        return dict(member) if member else None


def get_all_members() -> list[dict]:
    """Retrieves all members, active or inactive (excluding virtual member)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM members WHERE name != ? ORDER BY id",
            (VIRTUAL_MEMBER_INTERNAL_NAME,),
        )
        members = cursor.fetchall()
        return [dict(m) for m in members]


def get_active_members() -> list[dict]:
    """Retrieves all active members (excluding virtual member)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM members WHERE is_active = 1 AND name != ? ORDER BY id",
            (VIRTUAL_MEMBER_INTERNAL_NAME,),
        )  # Order by ID for consistent remainder distribution
        members = cursor.fetchall()
        return [dict(m) for m in members]


def update_member_remainder_status(member_id: int, status: bool):
    """Updates the paid_remainder_in_cycle status for a member."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE members SET paid_remainder_in_cycle = ? WHERE id = ?", (status, member_id)
        )
        conn.commit()


def reset_all_member_remainder_status():
    """Resets paid_remainder_in_cycle to False for all active members."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE members SET paid_remainder_in_cycle = 0 WHERE is_active = 1")
        conn.commit()


def deactivate_member(member_id: int) -> bool:
    """Deactivates a member by setting is_active to 0. Returns True if successful."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE members SET is_active = 0 WHERE id = ?", (member_id,))
        conn.commit()
        return cursor.rowcount > 0


def reactivate_member(member_id: int) -> bool:
    """Reactivates a member by setting is_active to 1. Returns True if successful."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE members SET is_active = 1 WHERE id = ?", (member_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Database operations for Periods ---


def get_current_period() -> dict | None:
    """Gets the current active (unsettled) period."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM periods WHERE is_settled = 0 ORDER BY start_date DESC LIMIT 1"
        )
        period = cursor.fetchone()
        return dict(period) if period else None


def create_new_period(name: str) -> int:
    """Creates a new settlement period and returns its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO periods (name, start_date, is_settled) VALUES (?, CURRENT_TIMESTAMP, 0) RETURNING id",
            (name,),
        )
        period_id = cursor.fetchone()[0]
        conn.commit()
        return period_id


def settle_period(period_id: int) -> bool:
    """Marks a period as settled and sets the end date."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE periods SET is_settled = 1, end_date = CURRENT_TIMESTAMP, settled_date = CURRENT_TIMESTAMP WHERE id = ?",
            (period_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_period_by_id(period_id: int) -> dict | None:
    """Retrieves a period by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods WHERE id = ?", (period_id,))
        period = cursor.fetchone()
        return dict(period) if period else None


def get_all_periods() -> list[dict]:
    """Retrieves all periods, ordered by start_date descending."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM periods ORDER BY start_date DESC")
        periods = cursor.fetchall()
        return [dict(p) for p in periods]


def get_transactions_by_period(period_id: int) -> list[dict]:
    """Retrieves all transactions for a specific period."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE period_id = ? ORDER BY TIMESTAMP", (period_id,)
        )
        transactions = cursor.fetchall()
        return [dict(t) for t in transactions]


def initialize_first_period_if_needed():
    """Ensures there's at least one period in the system."""
    # Check if periods table exists first
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='periods'")
        if not cursor.fetchone():
            # Periods table doesn't exist yet - skip period initialization
            return

    if get_current_period() is None:
        create_new_period("Initial Period")


def ensure_virtual_member_exists():
    """Ensures the virtual member exists for shared expenses."""
    virtual_member = get_member_by_name(VIRTUAL_MEMBER_INTERNAL_NAME)
    if not virtual_member:
        # Create virtual member (inactive so it doesn't appear in normal lists)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO members (name, is_active) VALUES (?, 0)",
                (VIRTUAL_MEMBER_INTERNAL_NAME,),
            )
            conn.commit()


def is_virtual_member(member: dict | None) -> bool:
    """Check if a member is the virtual/system member."""
    if not member:
        return False
    return member["name"].startswith(SYSTEM_MEMBER_PREFIX)


def get_member_display_name(member: dict) -> str:
    """Get display name for member (translates virtual member to user-friendly name)."""
    if is_virtual_member(member):
        from .i18n import _
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
) -> int:
    """Adds a new transaction to the database and returns its ID.
    If period_id is None, uses the current active period."""
    if period_id is None:
        current_period = get_current_period()
        if current_period is None:
            initialize_first_period_if_needed()
            current_period = get_current_period()
        period_id = current_period["id"]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (transaction_type, description, amount, payer_id, category_id, period_id) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
            (transaction_type, description, amount, payer_id, category_id, period_id),
        )
        transaction_id = cursor.fetchone()[0]
        conn.commit()
        return transaction_id


def get_all_transactions() -> list[dict]:
    """Retrieves all transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY TIMESTAMP")
        transactions = cursor.fetchall()
        return [dict(t) for t in transactions]


def get_category_by_name(name: str) -> dict | None:
    """Retrieves a category by its name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        category = cursor.fetchone()
        return dict(category) if category else None


def get_all_categories() -> list[dict]:
    """Retrieves all categories."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        categories = cursor.fetchall()
        return [dict(c) for c in categories]


def get_category_by_id(category_id: int) -> dict | None:
    """Retrieves a category by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        return dict(category) if category else None


# ... other database functions to be implemented ...
