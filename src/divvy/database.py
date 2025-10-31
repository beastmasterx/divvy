import sqlite3
import os

# Determine the absolute path to the project root and the database file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DB_FILE = os.path.join(PROJECT_ROOT, 'data', 'expenses.db')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), 'schema.sql')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def initialize_database():
    """Initializes the database by creating tables from the schema.sql file."""
    conn = get_db_connection()
    
    # Check if tables have already been created by checking for the 'members' table
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='members'")
    if cursor.fetchone():
        conn.close()
        return # Database already initialized

    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- Database operations for Members ---

def add_member(name: str) -> int | None:
    """Adds a new member to the database and returns their ID, or None if already exists."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO members (name) VALUES (?) RETURNING id", (name,))
        member_id = cursor.fetchone()[0]
        conn.commit()
        return member_id
    except sqlite3.IntegrityError: # Name is UNIQUE
        return None
    finally:
        pass

def get_member_by_name(name: str) -> dict | None:
    """Retrieves a member by their name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE name = ?", (name,))
    member = cursor.fetchone()
    return dict(member) if member else None

def get_member_by_id(member_id: int) -> dict | None:
    """Retrieves a member by their ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    member = cursor.fetchone()
    return dict(member) if member else None

def get_all_members() -> list[dict]:
    """Retrieves all members, active or inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY id")
    members = cursor.fetchall()
    return [dict(m) for m in members]

def get_active_members() -> list[dict]:
    """Retrieves all active members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE is_active = 1 ORDER BY id") # Order by ID for consistent remainder distribution
    members = cursor.fetchall()
    return [dict(m) for m in members]

def update_member_remainder_status(member_id: int, status: bool):
    """Updates the paid_remainder_in_cycle status for a member."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET paid_remainder_in_cycle = ? WHERE id = ?", (status, member_id))
    conn.commit()

def reset_all_member_remainder_status():
    """Resets paid_remainder_in_cycle to False for all active members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET paid_remainder_in_cycle = 0 WHERE is_active = 1")
    conn.commit()

# --- Database operations for Transactions ---

def add_transaction(transaction_type: str, description: str, amount: int, payer_id: int | None = None, category_id: int | None = None, remark: str | None = None) -> int:
    """Adds a new transaction to the database and returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (transaction_type, description, amount, payer_id, category_id, remark) VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
        (transaction_type, description, amount, payer_id, category_id, remark)
    )
    transaction_id = cursor.fetchone()[0]
    conn.commit()
    return transaction_id

def get_all_transactions() -> list[dict]:
    """Retrieves all transactions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY timestamp")
    transactions = cursor.fetchall()
    return [dict(t) for t in transactions]

def get_public_fund_balance() -> int:
    """Calculates the current balance of the public fund in cents."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sum of all deposits
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'deposit'")
    deposits = cursor.fetchone()[0] or 0
    
    # Sum of all expenses paid from the public fund (payer_id IS NULL)
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'expense' AND payer_id IS NULL")
    public_fund_expenses = cursor.fetchone()[0] or 0
    
    return deposits - public_fund_expenses


def get_category_by_name(name: str) -> dict | None:
    """Retrieves a category by its name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
    category = cursor.fetchone()
    return dict(category) if category else None

# ... other database functions to be implemented ...