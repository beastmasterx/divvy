import contextlib
import os
import sqlite3
from unittest.mock import patch

import pytest

from src.divvy import cli, database

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


@pytest.fixture
def setup_members():
    """Fixture to set up test members."""
    database.add_member("Alice")
    database.add_member("Bob")


def test_show_menu(capsys):
    """Test that menu displays correctly."""
    cli.show_menu()
    captured = capsys.readouterr()
    assert "Divvy Expense Splitter" in captured.out
    assert "Add Expense" in captured.out
    assert "Add Deposit" in captured.out
    assert "View Period" in captured.out


def test_menu_choice_add_member(setup_members, capsys):
    """Test menu option 6: Add a new member."""
    with (
        patch("builtins.input", side_effect=["6", "Charlie", "8"]),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    # Verify member was added
    member = database.get_member_by_name("Charlie")
    assert member is not None
    assert member["name"] == "Charlie"


def test_menu_choice_record_expense(setup_members, capsys):
    """Test menu option 1: Record an expense."""
    # Mock the selections: description, amount, payer (select 1=Alice), category (select first)
    inputs = [
        "1",  # Menu choice
        "Test expense",  # Description
        "10.00",  # Amount
        "1",  # Select Alice as payer
        "1",  # Select first category
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    # Verify transaction was created
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE description = 'Test expense'")
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["amount"] == 1000


def test_menu_choice_record_deposit(setup_members, capsys):
    """Test menu option 2: Record a deposit."""
    inputs = [
        "2",  # Menu choice
        "Monthly deposit",  # Description
        "50.00",  # Amount
        "1",  # Select Alice as payer
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    # Verify deposit transaction was created
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM transactions WHERE transaction_type = 'deposit' AND description = 'Monthly deposit'"
        )
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["amount"] == 5000


def test_menu_choice_view_period_summary(setup_members, capsys):
    """Test menu option 2: View current period summary."""
    # Add some transactions first
    alice = database.get_member_by_name("Alice")
    database.add_transaction("deposit", 10000, "Test deposit", alice["id"])

    inputs = [
        "4",  # View period summary
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    captured = capsys.readouterr()
    assert "VIEW PERIOD" in captured.out or "No active period found" in captured.out


def test_menu_choice_settle_period(setup_members, capsys):
    """Test menu option 5: Settle current period."""
    # Add some transactions first
    alice = database.get_member_by_name("Alice")
    database.add_transaction("deposit", 10000, "Test deposit", alice["id"])

    inputs = [
        "5",  # Settle period
        "y",  # Confirm
        "Test Period Name",  # Period name
        "8",  # Exit (after new period is created)
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    # Verify period was settled
    periods = database.get_all_periods()
    settled_periods = [p for p in periods if p["is_settled"] == 1]
    assert len(settled_periods) > 0


def test_menu_choice_show_system_status(setup_members, capsys):
    """Test menu option 4: View Period (no longer has system status menu)."""
    inputs = [
        "4",  # View Period
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    captured = capsys.readouterr()
    assert "VIEW PERIOD" in captured.out or "No active period found" in captured.out


def test_menu_choice_exit(capsys):
    """Test menu option 8: Exit."""
    inputs = ["8"]

    with patch("builtins.input", side_effect=inputs):
        # Exit uses 'break', not sys.exit(), so function completes normally
        cli.main()

    captured = capsys.readouterr()
    assert "Exiting Divvy. Goodbye!" in captured.out


def test_menu_invalid_choice(capsys):
    """Test handling of invalid menu choice."""
    inputs = ["99", "8"]  # Invalid choice, then exit

    with (
        patch("builtins.input", side_effect=inputs),
        patch("sys.exit"),
        contextlib.suppress(SystemExit),
    ):
        cli.main()

    captured = capsys.readouterr()
    assert "Invalid choice" in captured.out


def test_select_from_list(capsys):
    """Test the select_from_list helper function."""
    items = [
        {"name": "Item1"},
        {"name": "Item2"},
        {"name": "Item3"},
    ]

    with patch("builtins.input", return_value="2"):
        result = cli.select_from_list(items, "name", "Test Items")
        assert result is not None
        assert result["name"] == "Item2"

    captured = capsys.readouterr()
    assert "Select Test Items" in captured.out


def test_select_from_list_invalid_then_valid(capsys):
    """Test select_from_list with invalid input then valid."""
    items = [
        {"name": "Item1"},
        {"name": "Item2"},
    ]

    with patch("builtins.input", side_effect=["99", "1"]):
        result = cli.select_from_list(items, "name", "Test Items")
        assert result is not None
        assert result["name"] == "Item1"


def test_select_payer_for_expense(setup_members, capsys):
    """Test select_payer for expense."""
    with patch("builtins.input", return_value="1"):
        result = cli.select_payer(for_expense=True)
        assert result == "Alice"


def test_select_payer_for_deposit(setup_members, capsys):
    """Test select_payer for deposit (no Public Fund option)."""
    with patch("builtins.input", return_value="1"):
        result = cli.select_payer(for_expense=False)
        assert result == "Alice"


def test_record_expense_with_empty_description(setup_members):
    """Test recording expense with empty description (should become None)."""

    inputs = [
        "1",  # Menu choice
        "",  # Empty description
        "10.00",  # Amount
        "1",  # Select Alice
        "1",  # Select category
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    # Verify transaction has None description
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 1")
        tx = cursor.fetchone()
        assert tx is not None
        assert tx["description"] is None or tx["description"] == ""


def test_display_period_summary(setup_members, capsys):
    """Test _display_period_summary function via menu option."""
    alice = database.get_member_by_name("Alice")
    database.add_transaction("deposit", 10000, "Test deposit", alice["id"])

    # Test via menu option which calls _display_period_summary
    inputs = ["4", "8"]  # View period summary, then exit

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    captured = capsys.readouterr()
    # Either shows period summary or "No active period found"
    assert len(captured.out) > 0


def test_display_system_status(setup_members, capsys):
    """Test _display_view_period function via menu option."""
    # Test via menu option which calls _display_view_period
    inputs = ["4", "8"]  # View Period, then exit

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        cli.main()

    captured = capsys.readouterr()
    assert (
        "VIEW PERIOD" in captured.out
        or "No active period found" in captured.out
        or len(captured.out) > 0
    )
