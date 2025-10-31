import pytest
import sqlite3
import os
from unittest.mock import patch

from src.divvy import logic
from src.divvy import database

# Path to the schema file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCHEMA_FILE = os.path.join(PROJECT_ROOT, 'src', 'divvy', 'schema.sql')

@pytest.fixture
def db_connection():
    """Fixture for a temporary, in-memory SQLite database connection."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def mock_get_db_connection(db_connection):
    """Mock database.get_db_connection to use the in-memory test database."""
    with patch('src.divvy.database.get_db_connection', return_value=db_connection):
        yield

def test_add_new_member_no_buy_in():
    """Test adding the first member, expecting no buy-in."""
    result = logic.add_new_member("Alice")
    assert "Member 'Alice' added successfully. No buy-in required as public fund is empty or no other active members." == result
    
    member = database.get_member_by_name("Alice")
    assert member is not None
    assert member['name'] == "Alice"
    assert member['is_active'] == 1
    assert member['paid_remainder_in_cycle'] == 0

    # Check no transactions recorded (except default categories)
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM transactions")
    assert cursor.fetchone()[0] == 0

def test_add_new_member_with_buy_in():
    """Test adding a member when a public fund exists, expecting a buy-in."""
    # Add initial member and a deposit to simulate public fund
    logic.add_new_member("Bob")
    bob = database.get_member_by_name("Bob")
    assert bob is not None
    
    # Manually add a deposit to the public fund for Bob
    database.add_transaction(
        transaction_type='deposit',
        description="Initial fund for Bob",
        amount=10000, # $100.00
        payer_id=bob['id']
    )

    # Add a second member, expecting buy-in
    result = logic.add_new_member("Charlie")
    assert "Member 'Charlie' added successfully. Buy-in of 100.00 recorded." == result

    charlie = database.get_member_by_name("Charlie")
    assert charlie is not None
    assert charlie['name'] == "Charlie"

    # Verify buy-in transaction for Charlie
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE payer_id = ? AND description LIKE 'Buy-in%'", (charlie['id'],))
    buy_in_tx = cursor.fetchone()
    assert buy_in_tx is not None
    assert buy_in_tx['amount'] == 10000 # $100.00

    # Verify public fund balance after buy-in
    assert database.get_public_fund_balance() == 20000 # Bob's 100 + Charlie's 100 = 200

def test_record_expense_no_remainder():
    """Test recording an expense that splits evenly."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    logic.add_new_member("Charlie")

    result = logic.record_expense("Dinner", "30.00", "Alice", "Dining Out / Takeaway")
    assert "Expense 'Dinner' of 30.00 recorded successfully. Remainder of 0.00 assigned to N/A." == result

    # Verify transaction recorded
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE description = 'Dinner'")
    tx = cursor.fetchone()
    assert tx is not None
    assert tx['amount'] == 3000
    assert tx['payer_id'] == database.get_member_by_name("Alice")['id']
    assert tx['category_id'] == database.get_category_by_name("Dining Out / Takeaway")['id']

    # Verify remainder status (should all be False as no remainder was assigned)
    members = database.get_active_members()
    for member in members:
        assert member['paid_remainder_in_cycle'] == 0

def test_record_expense_with_remainder_round_robin():
    """Test recording expenses with remainder, verifying round-robin logic."""
    logic.add_new_member("Alice") # id 1
    logic.add_new_member("Bob")   # id 2
    logic.add_new_member("Charlie") # id 3

    # Expense 1: 10.00 / 3 = 3.33 with 1 cent remainder
    # Alice should get the remainder (first in order)
    result1 = logic.record_expense("Coffee", "10.00", "Alice", "Dining Out / Takeaway")
    assert "Expense 'Coffee' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice." == result1
    assert database.get_member_by_name("Alice")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Bob")['paid_remainder_in_cycle'] == 0
    assert database.get_member_by_name("Charlie")['paid_remainder_in_cycle'] == 0

    # Expense 2: 10.00 / 3 = 3.33 with 1 cent remainder
    # Bob should get the remainder (next in order)
    result2 = logic.record_expense("Snacks", "10.00", "Bob", "Groceries")
    assert "Expense 'Snacks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Bob." == result2
    assert database.get_member_by_name("Alice")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Bob")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Charlie")['paid_remainder_in_cycle'] == 0

    # Expense 3: 10.00 / 3 = 3.33 with 1 cent remainder
    # Charlie should get the remainder (next in order)
    result3 = logic.record_expense("Drinks", "10.00", "Charlie", "Groceries")
    assert "Expense 'Drinks' of 10.00 recorded successfully. Remainder of 0.01 assigned to Charlie." == result3
    assert database.get_member_by_name("Alice")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Bob")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Charlie")['paid_remainder_in_cycle'] == 1

    # Expense 4: 10.00 / 3 = 3.33 with 1 cent remainder
    # All members have paid a remainder, so status should reset, and Alice gets it again
    result4 = logic.record_expense("Lunch", "10.00", "Alice", "Dining Out / Takeaway")
    assert "Expense 'Lunch' of 10.00 recorded successfully. Remainder of 0.01 assigned to Alice." == result4
    assert database.get_member_by_name("Alice")['paid_remainder_in_cycle'] == 1
    assert database.get_member_by_name("Bob")['paid_remainder_in_cycle'] == 0
    assert database.get_member_by_name("Charlie")['paid_remainder_in_cycle'] == 0

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

    database.add_transaction('deposit', "Alice's deposit", 10000, alice['id'])
    database.add_transaction('deposit', "Bob's deposit", 5000, bob['id'])

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
    charlie = database.get_member_by_name("Charlie")

    # Alice deposits 100
    database.add_transaction('deposit', "Alice's fund", 10000, alice['id'])
    # Bob deposits 50
    database.add_transaction('deposit', "Bob's fund", 5000, bob['id'])

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

def test_get_settlement_balances_public_fund_expense():
    """Test settlement balances when public fund pays for an expense."""
    logic.add_new_member("Alice")
    logic.add_new_member("Bob")
    alice = database.get_member_by_name("Alice")
    bob = database.get_member_by_name("Bob")

    # Alice deposits 100 (public fund has 100)
    database.add_transaction('deposit', "Alice's fund", 10000, alice['id'])

    # Expense 1: Utilities 20.00, Public Fund pays. Split among Alice, Bob.
    # Each share: 10.00. Public fund decreases by 20.
    # Alice owes 10. Bob owes 10.
    logic.record_expense("Utilities", "20.00", "Public Fund", "Utilities (Water & Electricity)")

    balances = logic.get_settlement_balances()
    assert balances["Alice"] == "Is owed 90.00"
    assert balances["Bob"] == "Owes 10.00"