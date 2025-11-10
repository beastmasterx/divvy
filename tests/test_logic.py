import app.db as database
from app.db import Transaction
from app.db.session import get_session
from app.services import member, period, settlement, transaction


def test_add_new_member():
    """Test adding a new member."""
    result = member.add_new_member("alice@example.com", "Alice")
    assert result == "Member 'Alice' added successfully."

    member_data = database.get_member_by_name("Alice")
    assert member_data is not None
    assert member_data["name"] == "Alice"
    assert member_data["is_active"] == 1
    assert member_data["paid_remainder_in_cycle"] == 0

    # Check no transactions recorded (except default categories and periods)
    with get_session() as session:
        count = (
            session.query(Transaction)
            .filter(Transaction.transaction_type.in_(["deposit", "expense"]))
            .count()
        )
        assert count == 0


def test_record_expense_no_remainder():
    """Test recording an expense that splits evenly."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    member.add_new_member("charlie@example.com", "Charlie")

    result = transaction.record_expense("Dinner", "30.00", "Alice", "Other")
    assert (
        result
        == "Expense 'Dinner' of 30.00 recorded successfully. Remainder of 0.00 assigned to N/A."
    )

    # Verify transaction recorded
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Dinner").first()
        assert tx is not None
        assert tx.amount == 3000
        assert tx.payer_id == database.get_member_by_name("Alice")["id"]
        assert tx.category_id == database.get_category_by_name("Other")["id"]
        assert tx.period_id is not None  # Should be assigned to a period

    # Verify remainder status (should all be False as no remainder was assigned)
    members = database.get_active_members()
    for member_data in members:
        assert member_data["paid_remainder_in_cycle"] == 0


def test_record_expense_with_remainder_round_robin():
    """Test recording expenses with remainder, verifying round-robin logic."""
    member.add_new_member("alice@example.com", "Alice")  # id 1
    member.add_new_member("bob@example.com", "Bob")  # id 2
    member.add_new_member("charlie@example.com", "Charlie")  # id 3

    # Expense 1: 10.00 / 3 = 3.33 with 1 cent remainder
    # Alice should get the remainder (first in order)
    result1 = transaction.record_expense("Coffee", "10.00", "Alice", "Other")
    assert (
        result1
        == "Expense 'Coffee' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 0
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0

    # Expense 2: 10.00 / 3 = 3.33 with 1 cent remainder
    # Bob should get the remainder (next in order)
    result2 = transaction.record_expense("Snacks", "10.00", "Bob", "Groceries")
    assert (
        result2
        == "Expense 'Snacks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Bob."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0

    # Expense 3: 10.00 / 3 = 3.33 with 1 cent remainder
    # Charlie should get the remainder (next in order)
    result3 = transaction.record_expense("Drinks", "10.00", "Charlie", "Groceries")
    assert (
        result3
        == "Expense 'Drinks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Charlie."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 1

    # Expense 4: 10.00 / 3 = 3.33 with 1 cent remainder
    # All members have paid a remainder, so status should reset, and Alice gets it again
    result4 = transaction.record_expense("Lunch", "10.00", "Alice", "Other")
    assert (
        result4
        == "Expense 'Lunch' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice."
    )
    assert database.get_member_by_name("Alice")["paid_remainder_in_cycle"] == 1
    assert database.get_member_by_name("Bob")["paid_remainder_in_cycle"] == 0
    assert database.get_member_by_name("Charlie")["paid_remainder_in_cycle"] == 0


def test_get_settlement_balances_empty():
    """Test settlement balances when no members or transactions exist."""
    balances = settlement.get_settlement_balances()
    assert balances == {}


def test_get_settlement_balances_deposits_only():
    """Test settlement balances with only deposits."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    database.add_transaction("deposit", 5000, "Bob's deposit", bob["id"])

    balances = settlement.get_settlement_balances()
    assert balances["Alice"] == "Is owed 100.00"
    assert balances["Bob"] == "Is owed 50.00"


def test_get_settlement_balances_mixed_transactions():
    """Test settlement balances with a mix of deposits and expenses."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    member.add_new_member("charlie@example.com", "Charlie")

    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Alice deposits 100
    database.add_transaction("deposit", 10000, "Alice's fund", alice["id"])
    # Bob deposits 50
    database.add_transaction("deposit", 5000, "Bob's fund", bob["id"])

    # Expense 1: Dinner 30.00, Alice pays. Split among Alice, Bob, Charlie.
    # Each share: 10.00. Alice paid 30, owes 10. Net +20. Bob owes 10. Charlie owes 10.
    transaction.record_expense("Dinner", "30.00", "Alice", "Other")

    # Expense 2: Groceries 10.00, Bob pays. Split among Alice, Bob, Charlie.
    # Each share: 3.33 (1 cent remainder to Alice from round-robin)
    # Bob paid 10, owes 3.33. Net +6.67. Alice owes 3.33. Charlie owes 3.33.
    transaction.record_expense("Groceries", "10.00", "Bob", "Groceries")

    # Expected balances:
    # Alice: +100 (deposit) +30 (paid dinner) -10 (share dinner) -3.34 (share groceries + remainder) = +116.66
    # Bob:   +50 (deposit) +10 (paid groceries) -10 (share dinner) -3.33 (share groceries) = +46.67
    # Charlie: 0 (deposit) -10 (share dinner) -3.33 (share groceries) = -13.33

    balances = settlement.get_settlement_balances()
    assert balances["Alice"] == "Is owed 116.66"
    assert balances["Bob"] == "Is owed 46.67"
    assert balances["Charlie"] == "Owes 13.33"


def test_record_expense_with_null_description():
    """Test recording an expense with None description."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")

    result = transaction.record_expense(None, "10.00", "Alice", "Groceries")
    assert "Expense of 10.00 recorded successfully" in result

    # Verify transaction recorded with NULL description
    with get_session() as session:
        alice_id = database.get_member_by_name("Alice")["id"]
        tx = (
            session.query(Transaction)
            .filter_by(payer_id=alice_id)
            .order_by(Transaction.id.desc())
            .first()
        )
        assert tx is not None
        assert tx.description is None


def test_record_deposit():
    """Test recording a deposit."""
    member.add_new_member("alice@example.com", "Alice")

    result = transaction.record_deposit("Monthly contribution", "50.00", "Alice")
    assert "Deposit 'Monthly contribution'" in result
    assert "50.00" in result
    assert "Alice" in result

    # Verify transaction recorded
    with get_session() as session:
        alice_id = database.get_member_by_name("Alice")["id"]
        tx = (
            session.query(Transaction)
            .filter_by(transaction_type="deposit", payer_id=alice_id)
            .first()
        )
        assert tx is not None
        assert tx.amount == 5000
        assert tx.description == "Monthly contribution"
        assert tx.period_id is not None


def test_record_deposit_with_null_description():
    """Test recording a deposit with None description."""
    member.add_new_member("alice@example.com", "Alice")

    result = transaction.record_deposit(None, "25.00", "Alice")
    assert "Deposit of 25.00 from Alice recorded successfully" in result
    assert "25.00" in result

    # Verify transaction recorded with NULL description
    with get_session() as session:
        tx = (
            session.query(Transaction)
            .filter_by(transaction_type="deposit")
            .order_by(Transaction.id.desc())
            .first()
        )
        assert tx is not None
        assert tx.description is None


def test_get_period_balances():
    """Test getting balances for current period."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")

    # Add deposit and expense in current period
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    transaction.record_expense("Lunch", "20.00", "Alice", "Other")

    balances = period.get_period_balances()
    assert "Alice" in balances
    assert "Bob" in balances


def test_record_shared_expense():
    """Test recording a shared expense (using virtual member)."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    member.add_new_member("charlie@example.com", "Charlie")

    # Record shared expense (rent) - no individual payer
    result = transaction.record_expense(
        "Rent", "3000.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent"
    )
    assert "3000.00 recorded successfully" in result

    # Verify transaction recorded with virtual member as payer
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Rent").first()
        assert tx is not None
        assert tx.amount == 300000  # 3000.00 in cents

        payer = database.get_member_by_id(tx.payer_id)
        assert payer["name"] == database.PUBLIC_FUND_MEMBER_INTERNAL_NAME


def test_shared_expense_balance_calculation():
    """Test that shared expenses don't credit any member."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Alice deposits 100
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])

    # Shared expense: Rent 3000.00 (no one pays, everyone owes their share)
    transaction.record_expense("Rent", "3000.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent")

    # Expected balances:
    # Alice: +100 (deposit) -1500 (share of rent) = -1400 (owes 1400)
    # Bob: 0 (deposit) -1500 (share of rent) = -1500 (owes 1500)
    # No one gets credited for paying the rent (it's shared)

    balances = period.get_active_member_balances()
    assert balances["Alice"] == -140000  # -1400.00 in cents
    assert balances["Bob"] == -150000  # -1500.00 in cents


def test_mixed_shared_and_individual_expenses():
    """Test balance calculation with both shared and individual expenses."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Alice deposits 200
    database.add_transaction("deposit", 20000, "Alice's deposit", alice["id"])

    # Shared expense: Rent 1000.00 (split equally, no credit)
    transaction.record_expense("Rent", "1000.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent")

    # Individual expense: Groceries 60.00, Alice pays
    transaction.record_expense("Groceries", "60.00", "Alice", "Groceries")

    # Expected balances:
    # Alice: +200 (deposit) +60 (paid groceries) -500 (share rent) -30 (share groceries) = -270
    # Bob: 0 (deposit) -500 (share rent) -30 (share groceries) = -530

    balances = period.get_active_member_balances()
    assert balances["Alice"] == -27000  # -270.00 in cents
    assert balances["Bob"] == -53000  # -530.00 in cents


def test_get_period_summary():
    """Test getting period summary."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")

    # Add transactions
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    transaction.record_expense("Dinner", "30.00", "Alice", "Other")

    summary = period.get_period_summary()
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
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")

    # Add some transactions
    database.add_transaction("deposit", 10000, "Alice's deposit", alice["id"])
    transaction.record_expense("Dinner", "30.00", "Alice", "Other")

    # Get current period
    current_period = database.get_current_period()
    assert current_period is not None
    assert current_period["is_settled"] == 0

    # Get balances before settlement
    balances_before = period.get_active_member_balances(current_period["id"])

    # Settle the period
    result = period.settle_current_period("Settled Period")
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

    # Verify settlement transactions were created with correct amounts
    # Check that settlement transactions exist in the settled period
    settlement_transactions = database.get_transactions_by_period(current_period["id"])
    settlement_txs = [
        tx for tx in settlement_transactions if "Settlement" in (tx.get("description") or "")
    ]
    assert len(settlement_txs) > 0, "Settlement transactions should be created"


def test_public_fund_deposit():
    """Test depositing to public fund (virtual member)."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")

    # Deposit to public fund
    result = transaction.record_deposit(
        "Public fund contribution", "100.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
    )
    assert "100.00" in result

    # Verify transaction recorded
    with get_session() as session:
        tx = session.query(Transaction).filter_by(description="Public fund contribution").first()
        assert tx is not None
        assert tx.amount == 10000  # 100.00 in cents
        payer = database.get_member_by_id(tx.payer_id)
        assert payer["name"] == database.PUBLIC_FUND_MEMBER_INTERNAL_NAME


def test_shared_expense_with_sufficient_public_fund():
    """Test shared expense when public fund has sufficient balance."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)

    # Deposit 100 to public fund
    database.add_transaction("deposit", 10000, "Public fund", virtual_member["id"])

    # Shared expense: 50 (fully covered by public fund)
    transaction.record_expense(
        "Utilities",
        "50.00",
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME,
        "Utilities (Water & Electricity & Gas)",
    )

    # Expected: Fund covers all, members owe nothing
    balances = period.get_active_member_balances()
    assert balances["Alice"] == 0
    assert balances["Bob"] == 0


def test_shared_expense_with_insufficient_public_fund():
    """Test shared expense when public fund is insufficient."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)

    # Deposit 30 to public fund
    database.add_transaction("deposit", 3000, "Public fund", virtual_member["id"])

    # Shared expense: 100 (fund has 30, remainder 70 split between 2 members)
    transaction.record_expense("Rent", "100.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent")

    # Expected balances:
    # Fund covers 30, remainder 70 split: 35 each
    # Alice: -35 (owes 35)
    # Bob: -35 (owes 35)
    balances = period.get_active_member_balances()
    assert balances["Alice"] == -3500  # -35.00 in cents
    assert balances["Bob"] == -3500  # -35.00 in cents


def test_public_fund_cannot_go_negative():
    """Test that public fund balance never goes negative."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")

    # No deposit to public fund (fund = 0)

    # Shared expense: 100 (fund is 0, all split between members)
    transaction.record_expense("Rent", "100.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent")

    # Expected: Fund stays at 0 (not -100), all 100 split between members
    balances = period.get_active_member_balances()
    assert balances["Alice"] == -5000  # -50.00 in cents (100/2)
    assert balances["Bob"] == -5000  # -50.00 in cents


def test_public_fund_accumulation():
    """Test that public fund accumulates over multiple deposits."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)

    # Multiple deposits to public fund: 10 + 20 + 5 = 35.00
    database.add_transaction("deposit", 1000, "Fund deposit 1", virtual_member["id"])
    database.add_transaction("deposit", 2000, "Fund deposit 2", virtual_member["id"])
    database.add_transaction("deposit", 500, "Fund deposit 3", virtual_member["id"])

    # Shared expense: 20.00 (fund has 35.00, covers fully)
    transaction.record_expense(
        "Utilities",
        "20.00",
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME,
        "Utilities (Water & Electricity & Gas)",
    )

    # Fund should have 15.00 remaining (35.00 - 20.00), members owe nothing
    balances = period.get_active_member_balances()
    assert balances["Alice"] == 0
    assert balances["Bob"] == 0

    # Another shared expense: 10.00 (fund has 15.00, covers fully)
    transaction.record_expense(
        "Maintenance", "10.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Other"
    )

    # Fund should have 5.00 remaining (15.00 - 10.00), members still owe nothing
    balances = period.get_active_member_balances()
    assert balances["Alice"] == 0
    assert balances["Bob"] == 0


def test_public_fund_mixed_scenario():
    """Test public fund with deposits, expenses, and individual transactions."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)
    alice = database.get_member_by_name("Alice")

    # Alice deposits 200
    database.add_transaction("deposit", 20000, "Alice's deposit", alice["id"])

    # Public fund deposit: 50
    database.add_transaction("deposit", 5000, "Public fund", virtual_member["id"])

    # Shared expense: 100 (fund has 50, covers 50, remainder 50 split)
    transaction.record_expense("Rent", "100.00", database.PUBLIC_FUND_MEMBER_INTERNAL_NAME, "Rent")

    # Individual expense: 60, Alice pays
    transaction.record_expense("Groceries", "60.00", "Alice", "Groceries")

    # Expected balances:
    # Alice: +200 (deposit) +60 (paid) -25 (share rent) -30 (share groceries) = +205
    # Bob: 0 (deposit) -25 (share rent) -30 (share groceries) = -55
    balances = period.get_active_member_balances()
    assert balances["Alice"] == 20500  # +205.00 in cents
    assert balances["Bob"] == -5500  # -55.00 in cents


def test_get_settlement_plan():
    """Test getting settlement plan without executing it."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Create unbalanced scenario where both are creditors
    # Expected balances: Alice: +50 -15 = +35, Bob: +200 +30 -15 = +215
    database.add_transaction("deposit", 5000, "Alice deposit", alice["id"])
    database.add_transaction("deposit", 20000, "Bob deposit", bob["id"])
    transaction.record_expense("Expense", "30.00", "Bob", "Other")  # Bob paid, split 15 each

    current_period = database.get_current_period()
    period_id = current_period["id"]

    # Get settlement plan
    plan = settlement.get_settlement_plan(period_id)

    assert isinstance(plan, list)
    assert len(plan) > 0, "Should have settlement transactions"

    # Verify plan structure
    for tx in plan:
        assert "date" in tx
        assert "transaction_type" in tx
        assert "amount" in tx
        assert "description" in tx
        assert "payer_id" in tx
        assert "payer_name" in tx
        assert "from_to" in tx

        # Verify from_to labels
        if tx["amount"] < 0:
            assert tx["from_to"] == "To", "Negative amounts should be 'To'"
        else:
            assert tx["from_to"] == "From", "Positive amounts should be 'From'"


def test_settlement_no_duplicate_public_fund():
    """Test that settlement doesn't create duplicate public fund transactions."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)

    current_period = database.get_current_period()
    period_id = current_period["id"]

    # Add public fund deposit
    database.add_transaction("deposit", 5000, "Public fund", virtual_member["id"])

    # Create scenario where Alice is owed money (creditor)
    alice = database.get_member_by_name("Alice")
    database.add_transaction("deposit", 10000, "Alice deposit", alice["id"])
    transaction.record_expense("Expense", "20.00", "Alice", "Other")

    # Settle the period
    period.settle_current_period("Test Period")

    # Check settlement transactions in the settled period
    settlement_transactions = database.get_transactions_by_period(period_id)
    public_fund_settlements = [
        tx
        for tx in settlement_transactions
        if "Public fund distribution" in (tx.get("description") or "")
    ]

    # Should only have ONE public fund distribution transaction
    assert (
        len(public_fund_settlements) == 1
    ), f"Expected 1 public fund transaction, got {len(public_fund_settlements)}"


def test_settlement_zeroes_balances():
    """Test that settlement correctly zeroes all member balances."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    current_period = database.get_current_period()
    period_id = current_period["id"]

    # Create unbalanced scenario
    database.add_transaction("deposit", 10000, "Alice deposit", alice["id"])  # +100
    database.add_transaction("deposit", 5000, "Bob deposit", bob["id"])  # +50
    transaction.record_expense("Dinner", "90.00", "Alice", "Other")  # Split 45 each

    # Expected balances before settlement:
    # Alice: +100 (deposit) +90 (paid) -45 (share) = +145
    # Bob: +50 (deposit) -45 (share) = +5

    balances_before = period.get_active_member_balances(period_id)
    assert balances_before["Alice"] > 0
    assert balances_before["Bob"] > 0

    # Settle the period
    period.settle_current_period("Settled")

    # Check balances in the settled period (after settlement transactions)
    balances_after = period.get_active_member_balances(period_id)

    # All balances should be zero (within rounding)
    assert (
        abs(balances_after["Alice"]) < 2
    ), f"Alice balance should be ~0, got {balances_after['Alice']}"
    assert abs(balances_after["Bob"]) < 2, f"Bob balance should be ~0, got {balances_after['Bob']}"


def test_settlement_creditor_negative_deposit():
    """Test that settlement creates negative deposits for creditors."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    alice = database.get_member_by_name("Alice")

    current_period = database.get_current_period()
    period_id = current_period["id"]

    # Create scenario where both are creditors (Alice larger, Bob smaller)
    # Expected balances: Alice: +100 -25 = +75, Bob: +50 -25 = +25
    # They pair together: Bob pays Alice 25, so Alice receives "Settlement payment from Bob"
    database.add_transaction("deposit", 10000, "Alice deposit", alice["id"])
    transaction.record_expense("Expense", "50.00", "Bob", "Other")

    # Settle the period
    period.settle_current_period("Test")

    # Check settlement transactions - creditor should receive negative deposit
    settlement_transactions = database.get_transactions_by_period(period_id)
    alice_settlement_refunds = [
        tx
        for tx in settlement_transactions
        if tx.get("payer_id") == alice["id"]
        and "Settlement payment from" in (tx.get("description") or "")
    ]

    assert len(alice_settlement_refunds) > 0, "Alice should receive settlement refunds"
    for tx in alice_settlement_refunds:
        assert tx["amount"] < 0, "Creditor settlement should be negative deposit (refund)"


def test_settlement_debtor_positive_deposit():
    """Test that settlement creates positive deposits for debtors."""
    member.add_new_member("alice@example.com", "Alice")
    member.add_new_member("bob@example.com", "Bob")
    bob = database.get_member_by_name("Bob")
    alice = database.get_member_by_name("Alice")

    current_period = database.get_current_period()
    period_id = current_period["id"]

    # Create scenario where Bob is debtor (owes money) and Alice is creditor (owed money)
    # Alice pays expense, so she gets credit and Bob owes his share
    transaction.record_expense("Expense", "50.00", "Alice", "Other")

    # Expected balances:
    # Alice: +50 (paid) -25 (share) = +25 (creditor)
    # Bob: -25 (share) = -25 (debtor)

    # Settle the period
    period.settle_current_period("Test")

    # Check settlement transactions - debtor (Bob) should make positive deposit
    settlement_transactions = database.get_transactions_by_period(period_id)
    bob_settlement_deposits = [
        tx
        for tx in settlement_transactions
        if tx.get("payer_id") == bob["id"]
        and "Settlement payment to" in (tx.get("description") or "")
    ]

    assert len(bob_settlement_deposits) > 0, "Bob should make settlement deposits"
    for tx in bob_settlement_deposits:
        assert tx["amount"] > 0, "Debtor settlement should be positive deposit"
