import app.db as database
from app.db import Transaction
from app.db.session import get_session


def test_add_member():
    """Test adding a member."""
    member_id = database.add_member("testmember@example.com", "TestMember")
    assert member_id is not None

    member = database.get_member_by_name("TestMember")
    assert member is not None
    assert member.name == "TestMember"
    assert member.email == "testmember@example.com"
    assert member.is_active is True


def test_add_duplicate_member():
    """Test that adding duplicate member (by email) returns None."""
    database.add_member("duplicate@example.com", "Duplicate")
    member_id = database.add_member("duplicate@example.com", "Duplicate2")
    assert member_id is None


def test_get_member_by_id():
    """Test getting member by ID."""
    member_id = database.add_member("testmember@example.com", "TestMember")
    assert member_id is not None
    member = database.get_member_by_id(member_id)
    assert member is not None
    assert member.name == "TestMember"
    assert member.email == "testmember@example.com"


def test_get_all_members():
    """Test getting all members."""
    database.add_member("member1@example.com", "Member1")
    database.add_member("member2@example.com", "Member2")

    members = database.get_all_members()
    assert len(members) >= 2
    names = [m.name for m in members]
    assert "Member1" in names
    assert "Member2" in names


def test_get_active_members():
    """Test getting active members only."""
    database.add_member("active1@example.com", "Active1")
    database.add_member("active2@example.com", "Active2")

    active = database.get_active_members()
    names = [m.name for m in active]
    assert "Active1" in names
    assert "Active2" in names


def test_get_current_period():
    """Test getting current period."""
    period = database.get_current_period()
    assert period is not None
    assert period.is_settled is False


def test_create_new_period():
    """Test creating a new period."""
    period_id = database.create_new_period("Test Period")
    assert period_id is not None

    period = database.get_period_by_id(period_id)
    assert period is not None
    assert period.name == "Test Period"
    assert period.is_settled is False


def test_settle_period():
    """Test settling a period."""
    period_id = database.create_new_period("To Settle")
    result = database.settle_period(period_id)
    assert result is True

    period = database.get_period_by_id(period_id)
    assert period is not None
    assert period.is_settled is True
    assert period.end_date is not None


def test_add_transaction():
    """Test adding a transaction."""
    member_id = database.add_member("payer@example.com", "Payer")
    assert member_id is not None
    category = database.get_category_by_name("Groceries")
    assert category is not None

    period = database.get_current_period()
    assert period is not None
    tx_id = database.add_transaction(
        "expense",
        5000,
        description="Test expense",
        payer_id=member_id,
        category_id=category.id,
        period_id=period.id,
    )
    assert tx_id is not None

    with get_session() as session:
        tx = session.query(Transaction).filter_by(id=tx_id).first()
        assert tx is not None
        assert tx.amount == 5000
        assert tx.description == "Test expense"
        assert tx.period_id == period.id


def test_add_transaction_auto_period():
    """Test adding transaction without period_id (auto-assigns to current)."""
    member_id = database.add_member("payer@example.com", "Payer")
    assert member_id is not None
    category = database.get_category_by_name("Groceries")
    assert category is not None

    current_period = database.get_current_period()
    assert current_period is not None
    tx_id = database.add_transaction(
        "expense",
        3000,
        description="Auto period",
        payer_id=member_id,
        category_id=category.id,
        # period_id not provided
    )
    assert tx_id is not None

    with get_session() as session:
        tx = session.query(Transaction).filter_by(id=tx_id).first()
        assert tx is not None
        assert tx.period_id == current_period.id


def test_get_transactions_by_period():
    """Test getting transactions for a period."""
    period = database.get_current_period()
    assert period is not None
    member_id = database.add_member("payer@example.com", "Payer")
    assert member_id is not None
    category = database.get_category_by_name("Groceries")
    assert category is not None

    tx1_id = database.add_transaction(
        "expense", 1000, period_id=period.id, payer_id=member_id, category_id=category.id
    )
    tx2_id = database.add_transaction(
        "expense", 2000, period_id=period.id, payer_id=member_id, category_id=category.id
    )

    transactions = database.get_transactions_by_period(period.id)
    assert len(transactions) >= 2
    tx_ids = [tx.id for tx in transactions]
    assert tx1_id in tx_ids
    assert tx2_id in tx_ids


def test_get_category_by_name():
    """Test getting category by name."""
    category = database.get_category_by_name("Groceries")
    assert category is not None
    assert category.name == "Groceries"


def test_get_category_by_id():
    """Test getting category by ID."""
    category = database.get_category_by_name("Groceries")
    assert category is not None
    category_by_id = database.get_category_by_id(category.id)
    assert category_by_id is not None
    assert category_by_id.name == "Groceries"


def test_get_all_categories():
    """Test getting all categories."""
    categories = database.get_all_categories()
    assert len(categories) > 0
    names = [c.name for c in categories]
    assert "Groceries" in names
    assert "Rent" in names


def test_update_member_remainder_status():
    """Test updating member remainder status."""
    member_id = database.add_member("testmember@example.com", "TestMember")
    assert member_id is not None

    database.update_member_remainder_status(member_id, True)
    member = database.get_member_by_id(member_id)
    assert member is not None
    assert member.paid_remainder_in_cycle is True

    database.update_member_remainder_status(member_id, False)
    member = database.get_member_by_id(member_id)
    assert member is not None
    assert member.paid_remainder_in_cycle is False


def test_reset_all_member_remainder_status():
    """Test resetting all member remainder status."""
    member1_id = database.add_member("member1@example.com", "Member1")
    member2_id = database.add_member("member2@example.com", "Member2")
    assert member1_id is not None
    assert member2_id is not None

    database.update_member_remainder_status(member1_id, True)
    database.update_member_remainder_status(member2_id, True)

    database.reset_all_member_remainder_status()

    member1 = database.get_member_by_id(member1_id)
    member2 = database.get_member_by_id(member2_id)
    assert member1 is not None
    assert member2 is not None
    assert member1.paid_remainder_in_cycle is False
    assert member2.paid_remainder_in_cycle is False


def test_virtual_member_not_in_active_members():
    """Test that virtual member doesn't appear in get_active_members()."""
    # Add a regular member
    database.add_member("alice@example.com", "Alice")

    # Get active members
    active_members = database.get_active_members()

    # Virtual member should not appear
    member_names = [m.name for m in active_members]
    assert database.PUBLIC_FUND_MEMBER_INTERNAL_NAME not in member_names
    assert "Alice" in member_names


def test_virtual_member_not_in_all_members():
    """Test that virtual member doesn't appear in get_all_members()."""
    # Add a regular member
    database.add_member("alice@example.com", "Alice")

    # Get all members
    all_members = database.get_all_members()

    # Virtual member should not appear
    member_names = [m.name for m in all_members]
    assert database.PUBLIC_FUND_MEMBER_INTERNAL_NAME not in member_names
    assert "Alice" in member_names


def test_is_virtual_member():
    """Test is_virtual_member function."""
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)
    assert virtual_member is not None
    regular_member_id = database.add_member("alice@example.com", "Alice")
    assert regular_member_id is not None
    regular_member = database.get_member_by_id(regular_member_id)
    assert regular_member is not None

    assert database.is_virtual_member(virtual_member) is True
    assert database.is_virtual_member(regular_member) is False
    assert database.is_virtual_member(None) is False


def test_get_member_display_name():
    """Test get_member_display_name function."""
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)
    assert virtual_member is not None
    regular_member_id = database.add_member("alice@example.com", "Alice")
    assert regular_member_id is not None
    regular_member = database.get_member_by_id(regular_member_id)
    assert regular_member is not None

    # Virtual member should display as "Group"
    assert database.get_member_display_name(virtual_member) == "Group"

    # Regular member should display as their name
    assert database.get_member_display_name(regular_member) == "Alice"
