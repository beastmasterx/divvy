import os
import sqlite3
from unittest.mock import patch

import pytest

from src.divvy import database, logic

# Path to the schema file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_FILE = os.path.join(PROJECT_ROOT, "src", "divvy", "schema.sql")


class DatabaseConnection:
    """Context manager wrapper for database connection."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close in tests - fixture handles it
        pass


@pytest.fixture
def db_connection():
    """Fixture for a temporary, in-memory SQLite database connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    with open(SCHEMA_FILE) as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()

    # Ensure there's an initial period - create it directly since we're using in-memory DB
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO periods (name, start_date, is_settled) VALUES (?, CURRENT_TIMESTAMP, 0)",
        ("Initial Period",),
    )
    conn.commit()

    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def mock_get_db_connection(db_connection):
    """Mock database.get_db_connection to use the in-memory test database."""

    def get_connection():
        return DatabaseConnection(db_connection)

    with patch("src.divvy.database.get_db_connection", side_effect=get_connection):
        yield


def test_add_new_member():
    """Test adding a new member."""
    result = logic.add_new_member("Alice")
    assert result == "Member 'Alice' added successfully."

    member = database.get_member_by_name("Alice")
    assert member is not None
    assert member["name"] == "Alice"
    assert member["is_active"] == 1
    assert member["paid_remainder_in_cycle"] == 0

    # Check no transactions recorded (except default categories and periods)
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_type IN ('deposit', 'expense')"
        )
        assert cursor.fetchone()[0] == 0


def test_record_expense_no_remainder():
    """Test recording an expense that splits evenly."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    logic.add_new_member("Charlie")

    result = logic.record_expense("Dinner", "30.00", "Alice", "Dining Out / Takeaway")
    assert (
        result
        == "Expense 'Dinner' of 30.00 recorded successfully. Remainder of 0.00 assigned to N/A."
    )

    # Verify transaction recorded
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE description = 'Dinner'")
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["amount"] == 3000
        assert tx["payer_id"] == database.get_member_by_name("Alice")["id"]
        assert tx["category_id"] == database.get_category_by_name("Dining Out / Takeaway")["id"]
        assert tx["period_id"] is not None  # Should be assigned to a period

    # Verify remainder status (should all be False as no remainder was assigned)
    members = database.get_active_members()
    for member in members:
        assert member["paid_remainder_in_cycle"] == 0


def test_record_expense_with_remainder_round_robin():
    """Test recording expenses with remainder, verifying round-robin logic."""
    logic.add_new_member("Alice")  # id 1
    logic.add_new_member("Bob")  # id 2
    logic.add_new_member("Charlie")  # id 3

    # Expense 1: 10.00 / 3 = 3.33 with 1 cent remainder
    # Alice should get the remainder (first in order)
    result1 = logic.record_expense("Coffee", "10.00", "Alice", "Dining Out / Takeaway")
    assert (
        result1
        == "Expense 'Coffee' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 0
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0

    # Expense 2: 10.00 / 3 = 3.33 with 1 cent remainder
    # Bob should get the remainder (next in order)
    result2 = logic.record_expense("Snacks", "10.00", "Bob", "Groceries")
    assert (
        result2
        == "Expense 'Snacks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Bob."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0

    # Expense 3: 10.00 / 3 = 3.33 with 1 cent remainder
    # Charlie should get the remainder (next in order)
    result3 = logic.record_expense("Drinks", "10.00", "Charlie", "Groceries")
    assert (
        result3
        == "Expense 'Drinks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Charlie."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 1

    # Expense 4: 10.00 / 3 = 3.33 with 1 cent remainder
    # All members have paid a remainder, so status should reset, and Alice gets it again
    result4 = logic.record_expense("Lunch", "10.00", "Alice", "Dining Out / Takeaway")
    assert (
        result4
        == "Expense 'Lunch' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 0
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0


def test_get_settlement_balances_empty():
    """Test settlement balances when no members or transactions exist."""
    balances = logic.get_settlement_balances()
    assert balances == {}


def test_get_settlement_balances_deposits_only():
    """Test settlement balances with only deposits."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    database.add_transaction("deposit", 5000, "Bob's deposit", bob["id"])

    balances = logic.get_settlement_balances()
    assert balances["Alice"] == "Is owed 100.00"
    assert balances["Bob"] == "Is owed 50.00"


def test_get_settlement_balances_mixed_transactions():
    """Test settlement balances with a mix of deposits and expenses."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    logic.add_new_member("Charlie")

    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Alice deposits 100
    database.add_transaction("deposit", 10000, "Alice's fund", alice["id"])
    # Bob deposits 50
    database.add_transaction("deposit", 5000, "Bob's fund", bob["id"])

    # Expense 1: Dinner 30.00, Alice pays. Split among Alice, Bob, Charlie.
    # Each share: 10.00. Alice paid 30, owes 10. Net +20. Bob owes 10. Charlie owes 10.
    logic.record_expense("Dinner", "30.00", "Alice", "Dining Out / Takeaway")

    # Expense 2: Groceries 10.00, Bob pays. Split among Alice, Bob, Charlie.
    # Each share: 3.33 (1 cent remainder to Alice from round-robin)
    # Bob paid 10, owes 3.33. Net +6.67. Alice owes 3.33. Charlie owes 3.33.
    logic.record_expense("Groceries", "10.00", "Bob", "Groceries")

    # Expected balances:
    # Alice: +100 (deposit) +30 (paid dinner) -10 (share dinner) -3.34 (share groceries + remainder) = +116.66
    # Bob:   +50 (deposit) +10 (paid groceries) -10 (share dinner) -3.33 (share groceries) = +46.67
    # Charlie: 0 (deposit) -10 (share dinner) -3.33 (share groceries) = -13.33

    balances = logic.get_settlement_balances()
    assert balances["Alice"] == "Is owed 116.66"
    assert balances["Bob"] == "Is owed 46.67"
    assert balances["Charlie"] == "Owes 13.33"


def test_record_expense_with_null_description():
    """Test recording an expense with None description."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")

    result = logic.record_expense(None, "10.00", "Alice", "Groceries")
    assert "Expense '(no description)'" in result

    # Verify transaction recorded with NULL description
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE payer_id = ? ORDER BY id DESC LIMIT 1",
            (database.get_member_by_name("Alice")["id"],),
        )
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["description"] is None


def test_record_deposit():
    """Test recording a deposit."""
    logic.add_new_member("Alice")

    result = logic.record_deposit("Monthly contribution", "50.00", "Alice")
    assert "Deposit 'Monthly contribution'" in result
    assert "50.00" in result
    assert "Alice" in result

    # Verify transaction recorded
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE transaction_type = 'deposit' AND payer_id = ?",
            (database.get_member_by_name("Alice")["id"],),
        )
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["amount"] == 5000
        assert tx["description"] == "Monthly contribution"
        assert tx["period_id"] is not None


def test_record_deposit_with_null_description():
    """Test recording a deposit with None description."""
    logic.add_new_member("Alice")

    result = logic.record_deposit(None, "25.00", "Alice")
    assert "Deposit '(no description)'" in result
    assert "25.00" in result

    # Verify transaction recorded with NULL description
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE transaction_type = 'deposit' ORDER BY id DESC LIMIT 1"
        )
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["description"] is None


def test_get_period_balances():
    """Test getting balances for current period."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    alice = database.get_member_by_name("Alice")

    # Add deposit and expense in current period
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    logic.record_expense("Lunch", "20.00", "Alice", "Dining Out / Takeaway")

    balances = logic.get_period_balances()
    assert "Alice" in balances
    assert "Bob" in balances


def test_get_period_summary():
    """Test getting period summary."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    alice = database.get_member_by_name("Alice")

    # Add transactions
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    logic.record_expense("Dinner", "30.00", "Alice", "Dining Out / Takeaway")

    summary = logic.get_period_summary()
    assert summary is not None
    assert "period" in summary
    assert "transactions" in summary
    assert "balances" in summary
    assert "totals" in summary
    assert summary["transaction_count"] == 2
    assert summary["totals"]["deposits"] == 10000
    assert summary["totals"]["expenses"] == 3000


def test_settle_current_period():
    """Test settling current period."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    alice = database.get_member_by_name("Alice")

    # Add some transactions
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    logic.record_expense("Dinner", "30.00", "Alice", "Dining Out / Takeaway")

    # Get current period
    current_period = database.get_current_period()
    assert current_period is not None
    assert current_period["is_settled"] == 0

    # Settle the period
    result = logic.settle_current_period("Settled Period")
    assert "has been settled" in result
    assert "New period" in result

    # Verify period is settled
    settled_period = database.get_period_by_id(current_period["id"])
    assert settled_period["is_settled"] == 1
    assert settled_period["end_date"] is not None

    # Verify new period created
    new_period = database.get_current_period()
    assert new_period is not None
    assert new_period["id"] != current_period["id"]
    assert new_period["name"] == "Settled Period"
    assert new_period["is_settled"] == 0
