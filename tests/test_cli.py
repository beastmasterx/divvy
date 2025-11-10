import contextlib
from unittest.mock import patch

import pytest

import app.db as database
from app.db import Transaction
from app.db.session import get_session
from cli.main import main, select_from_list, select_payer, show_menu


@pytest.fixture
def setup_members():
    """Fixture to set up test members."""
    database.add_member("alice@example.com", "Alice")
    database.add_member("bob@example.com", "Bob")


def test_show_menu(capsys):
    """Test that menu displays correctly."""
    show_menu()
    captured = capsys.readouterr()
    assert "DIVVY" in captured.out
    assert "Add Expense" in captured.out
    assert "Add Deposit" in captured.out
    assert "View Period" in captured.out


def test_menu_choice_add_member(setup_members, capsys):
    """Test menu option 6: Add a new member."""
    with (
        patch("builtins.input", side_effect=["6", "charlie@example.com", "Charlie", "8"]),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    # Verify member was added
    member = database.get_member_by_email("charlie@example.com")
    assert member is not None
    assert member["name"] == "Charlie"
    assert member["email"] == "charlie@example.com"


def test_menu_choice_record_expense(setup_members, capsys):
    """Test menu option 1: Record an expense."""
    # Mock the selections: description, amount, expense type (i=individual), payer (select 1=Alice), category (select first)
    inputs = [
        "1",  # Menu choice
        "Test expense",  # Description
        "10.00",  # Amount
        "i",  # Individual split (default)
        "1",  # Select Alice as payer
        "1",  # Select first category
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    # Verify transaction was created
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Test expense").first()
        assert tx is not None
        assert tx.amount == 1000


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
        main()

    # Verify deposit transaction was created
    with get_session() as session:
        tx = (
            session.query(Transaction)
            .filter_by(transaction_type="deposit", description="Monthly deposit")
            .first()
        )
        assert tx is not None
        assert tx.amount == 5000


def test_menu_choice_view_period(setup_members, capsys):
    """Test menu option 4: View period summary with period selection."""
    # Add some transactions first
    alice = database.get_member_by_name("Alice")
    database.add_transaction("deposit", 10000, "Test deposit", alice["id"])

    inputs = [
        "4",  # View period
        "1",  # Select first period (default/current)
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    captured = capsys.readouterr()
    # Should show period selection menu and then period details
    assert (
        "Select Period" in captured.out
        or "选择" in captured.out
        or "Initial Period" in captured.out
        or "Started:" in captured.out
        or "开始日期：" in captured.out
        or "No active period found" in captured.out
        or "No periods available" in captured.out
    )


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
        main()

    # Verify period was settled
    periods = database.get_all_periods()
    settled_periods = [p for p in periods if p["is_settled"] == 1]
    assert len(settled_periods) > 0


def test_menu_choice_exit(capsys):
    """Test menu option 8: Exit."""
    inputs = ["8"]

    with patch("builtins.input", side_effect=inputs):
        # Exit uses 'break', not sys.exit(), so function completes normally
        main()

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
        main()

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
        result = select_from_list(items, "name", "Test Items")
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
        result = select_from_list(items, "name", "Test Items")
        assert result is not None
        assert result["name"] == "Item1"


def test_select_payer_for_expense(setup_members, capsys):
    """Test select_payer for expense."""
    with patch("builtins.input", return_value="1"):
        result = select_payer(for_expense=True)
        assert result == "Alice"


def test_select_payer_for_deposit(setup_members, capsys):
    """Test select_payer for deposit (includes Group/public fund option)."""
    with patch("builtins.input", return_value="1"):
        result = select_payer(for_expense=False)
        assert result == "Alice"


def test_record_expense_with_empty_description(setup_members):
    """Test recording expense with empty description (should become None)."""

    inputs = [
        "1",  # Menu choice
        "",  # Empty description
        "10.00",  # Amount
        "i",  # Individual split (default)
        "1",  # Select Alice
        "1",  # Select category
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    # Verify transaction has None description
    with get_session() as session:
        tx = session.query(Transaction).order_by(Transaction.id.desc()).first()
        assert tx is not None
        assert tx.description is None or tx.description == ""


def test_menu_choice_record_shared_expense(setup_members, capsys):
    """Test menu option 1: Record a shared expense (using virtual member)."""
    inputs = [
        "1",  # Menu choice
        "Rent payment",  # Description
        "3000.00",  # Amount
        "s",  # Shared expense
        "1",  # Select first category (Rent)
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    # Verify transaction was created with virtual member as payer
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Rent payment").first()
        assert tx is not None
        assert tx.amount == 300000  # 3000.00 in cents

        # Verify payer is virtual member
        payer = database.get_member_by_id(tx.payer_id)
        assert payer is not None
        assert payer["name"] == database.PUBLIC_FUND_MEMBER_INTERNAL_NAME


def test_menu_choice_record_deposit_to_public_fund(setup_members, capsys):
    """Test menu option 2: Record a deposit to public fund (Group)."""
    # setup_members creates 2 members (Alice, Bob), Group is 3rd option
    active_members = database.get_active_members()
    group_option = str(len(active_members) + 1)  # Group is after all active members

    inputs = [
        "2",  # Menu choice
        "Public fund",  # Description
        "100.00",  # Amount
        group_option,  # Select Group (last option)
        "8",  # Exit
    ]

    with (
        patch("builtins.input", side_effect=inputs),
        contextlib.suppress(SystemExit, KeyboardInterrupt),
    ):
        main()

    # Verify transaction was created with virtual member as payer
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Public fund").first()
        assert tx is not None
        assert tx.amount == 10000  # 100.00 in cents
        assert tx.transaction_type == "deposit"

        # Verify payer is virtual member
        payer = database.get_member_by_id(tx.payer_id)
        assert payer is not None
        assert payer["name"] == database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
