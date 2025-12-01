"""
Unit tests for TransactionService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import NotFoundError, ValidationError
from app.models import Category, Group, Period, SplitKind, Transaction, TransactionKind, TransactionStatus, User
from app.schemas import ExpenseShareRequest, TransactionRequest
from app.services import TransactionService


@pytest.mark.unit
class TestTransactionService:
    """Test suite for TransactionService."""

    async def test_get_transaction_by_id_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving a transaction by ID when it exists."""
        # Create required dependencies
        user = await user_factory(email="payer@example.com", name="Payer")
        category = await category_factory(name="Test Category")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="Test Transaction"
        )

        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.id == transaction.id
        assert retrieved.description == "Test Transaction"

    async def test_get_transaction_by_id_not_exists(self, transaction_service: TransactionService):
        """Test retrieving a transaction by ID when it doesn't exist."""
        result = await transaction_service.get_transaction_by_id(99999)
        assert result is None

    async def test_get_transactions_by_period_id(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test retrieving transactions for a specific period."""
        # Create required dependencies
        user = await user_factory(email="payer@example.com", name="Payer")
        category = await category_factory(name="Test Category")
        period1 = await period_factory(group_id=1, name="Period 1")
        period2 = await period_factory(group_id=1, name="Period 2")

        tx1 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx2 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period1.id)
        tx3 = await transaction_factory(payer_id=user.id, category_id=category.id, period_id=period2.id)

        period1_transactions = await transaction_service.get_transactions_by_period_id(period1.id)

        assert len(period1_transactions) >= 2

        transaction_ids = {tx.id for tx in period1_transactions}

        assert tx1.id in transaction_ids
        assert tx2.id in transaction_ids
        assert tx3.id not in transaction_ids

    async def test_create_transaction_expense_equal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating an expense transaction with equal split."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )

        created = await transaction_service.create_transaction(period.id, request)

        assert created.id is not None
        assert created.description == "Dinner"
        assert created.amount == 10000
        assert created.transaction_kind == TransactionKind.EXPENSE
        assert created.split_kind == SplitKind.EQUAL
        assert len(created.expense_shares or []) == 2

    async def test_create_transaction_deposit(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating a deposit transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Monthly deposit",
            amount=50000,  # $500.00
            payer_id=user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )

        created = await transaction_service.create_transaction(period.id, request)

        assert created.id is not None
        assert created.description == "Monthly deposit"
        assert created.amount == 50000
        assert created.transaction_kind == TransactionKind.DEPOSIT

    async def test_create_transaction_expense_no_shares_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating an expense without expense_shares raises ValidationError."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Expense",
            amount=10000,
            payer_id=user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[],  # Empty shares should raise error
        )

        with pytest.raises(ValidationError):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_deposit_with_shares_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating a deposit with expense_shares raises ValidationError."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=1, name="Test Period")

        request = TransactionRequest(
            description="Deposit",
            amount=10000,
            payer_id=user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user.id, transaction_id=0, share_amount=10000, share_percentage=100.0)
            ],  # Deposits shouldn't have shares
        )

        with pytest.raises(ValidationError):
            await transaction_service.create_transaction(period.id, request)

    async def test_update_transaction_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating an existing transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Original Description",
            amount=10000,
        )

        request = TransactionRequest(
            description="Updated Description",
            amount=20000,
            payer_id=user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user.id, transaction_id=0, share_amount=20000, share_percentage=100.0)
            ],
        )

        updated = await transaction_service.update_transaction(transaction.id, request)

        assert updated.description == "Updated Description"
        assert updated.amount == 20000

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)

        assert retrieved is not None
        assert retrieved.description == "Updated Description"
        assert retrieved.amount == 20000

    async def test_update_transaction_not_exists(self, transaction_service: TransactionService):
        """Test updating a non-existent transaction raises NotFoundError."""
        request = TransactionRequest(
            description="Updated",
            amount=10000,
            payer_id=1,
            category_id=1,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=1, transaction_id=0, share_amount=10000, share_percentage=100.0)
            ],
        )

        with pytest.raises(NotFoundError):
            await transaction_service.update_transaction(99999, request)

    async def test_delete_transaction_exists(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test deleting a transaction that exists."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id, category_id=category.id, period_id=period.id, description="To Delete"
        )
        transaction_id = transaction.id

        # Delete it
        await transaction_service.delete_transaction(transaction_id)

        # Verify it's gone
        retrieved = await transaction_service.get_transaction_by_id(transaction_id)

        assert retrieved is None

    # ============================================================================
    # get_all_balances tests (indirectly tests _calculate_shares_for_transaction)
    # ============================================================================

    async def test_get_all_balances_empty_period(
        self,
        transaction_service: TransactionService,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances for a period with no transactions."""
        # Create required dependencies
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Empty Period")

        balances = await transaction_service.get_all_balances(period.id)

        assert isinstance(balances, list)
        assert len(balances) == 0

    async def test_get_all_balances_with_deposits(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with deposit transactions."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Deposit")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Create deposits
        deposit1 = TransactionRequest(
            description="User 1 deposit",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )
        deposit2 = TransactionRequest(
            description="User 2 deposit",
            amount=5000,  # $50.00
            payer_id=user2.id,
            category_id=category.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )
        await transaction_service.create_transaction(period.id, deposit1)
        await transaction_service.create_transaction(period.id, deposit2)

        balances = await transaction_service.get_all_balances(period.id)

        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        assert balances_dict[user1.id] == 10000  # User 1 is owed $100
        assert balances_dict[user2.id] == 5000  # User 2 is owed $50

    async def test_get_all_balances_with_expenses_equal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with expense transactions using equal split."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Create expense: User 1 pays $100, split equally between User 1 and User 2
        expense = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )
        await transaction_service.create_transaction(period.id, expense)

        balances = await transaction_service.get_all_balances(period.id)

        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User 1 paid $100, owes $50 share = +$50
        # User 2 owes $50 share = -$50
        assert balances_dict[user1.id] == 5000
        assert balances_dict[user2.id] == -5000

    async def test_get_all_balances_with_expenses_equal_split_three_users(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with equal split transaction (3 users, tests remainder distribution)."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        user3 = await user_factory(email="user3@example.com", name="User 3")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Create expense: $10.00 / 3 = $3.33 each with 1 cent remainder
        expense = TransactionRequest(
            description="Split bill",
            amount=1000,  # $10.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=333, share_percentage=33.33),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=333, share_percentage=33.33),
                ExpenseShareRequest(user_id=user3.id, transaction_id=0, share_amount=334, share_percentage=33.34),
            ],
        )
        await transaction_service.create_transaction(period.id, expense)

        balances = await transaction_service.get_all_balances(period.id)

        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User 1 paid $10.00, owes share (333 or 334 cents depending on remainder distribution)
        # Total shares must equal 1000 cents
        total_shares = abs(balances_dict[user1.id] - 1000) + abs(balances_dict[user2.id]) + abs(balances_dict[user3.id])
        assert total_shares == 1000

        # User 1 should have positive balance (paid more than owed)
        assert balances_dict[user1.id] > 0
        # Users 2 and 3 should have negative balances (owe money)
        assert balances_dict[user2.id] < 0
        assert balances_dict[user3.id] < 0

    async def test_get_all_balances_with_personal_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with personal split transaction."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Create expense: User pays $50, personal expense
        expense = TransactionRequest(
            description="Personal expense",
            amount=5000,  # $50.00
            payer_id=user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user.id, transaction_id=0, share_amount=5000, share_percentage=100.0)
            ],
        )
        await transaction_service.create_transaction(period.id, expense)

        balances = await transaction_service.get_all_balances(period.id)

        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User paid $50, owes $50 share = $0 balance
        assert balances_dict[user.id] == 0

    async def test_get_all_balances_with_mixed_transactions(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with mixed transactions (deposits, expenses, refunds)."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group = await group_factory(name="Test Group")
        deposit_category = await category_factory(name="Deposit")
        expense_category = await category_factory(name="Groceries")
        period = await period_factory(group_id=group.id, name="Test Period")

        # Create deposit: User 1 deposits $100
        deposit = TransactionRequest(
            description="User 1 deposit",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=deposit_category.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )
        await transaction_service.create_transaction(period.id, deposit)

        # Create expense: User 1 pays $50, split equally
        expense = TransactionRequest(
            description="Dinner",
            amount=5000,  # $50.00
            payer_id=user1.id,
            category_id=expense_category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=2500, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=2500, share_percentage=50.0),
            ],
        )
        await transaction_service.create_transaction(period.id, expense)

        balances = await transaction_service.get_all_balances(period.id)

        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User 1: +$100 (deposit) + $50 (paid) - $25 (share) = +$125
        # User 2: -$25 (share)
        assert balances_dict[user1.id] == 12500
        assert balances_dict[user2.id] == -2500

    # ============================================================================
    # Split Kind Tests: AMOUNT and PERCENTAGE
    # ============================================================================

    async def test_create_transaction_expense_amount_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating an expense transaction with amount-based split."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        user3 = await user_factory(email="user3@example.com", name="User 3")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Custom split dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.AMOUNT,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=4000, share_percentage=40.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=3500, share_percentage=35.0),
                ExpenseShareRequest(user_id=user3.id, transaction_id=0, share_amount=2500, share_percentage=25.0),
            ],
        )

        created = await transaction_service.create_transaction(period.id, request)

        assert created.id is not None
        assert created.description == "Custom split dinner"
        assert created.amount == 10000
        assert created.transaction_kind == TransactionKind.EXPENSE
        assert created.split_kind == SplitKind.AMOUNT
        assert len(created.expense_shares or []) == 3

        # Verify balances reflect the amount split
        balances = await transaction_service.get_all_balances(period.id)
        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User 1 paid $100, owes $40 = +$60
        # User 2 owes $35 = -$35
        # User 3 owes $25 = -$25
        assert balances_dict[user1.id] == 6000
        assert balances_dict[user2.id] == -3500
        assert balances_dict[user3.id] == -2500

    async def test_create_transaction_expense_percentage_split(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test creating an expense transaction with percentage-based split."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        user3 = await user_factory(email="user3@example.com", name="User 3")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Percentage split dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERCENTAGE,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=3000, share_percentage=30.0),
                ExpenseShareRequest(user_id=user3.id, transaction_id=0, share_amount=2000, share_percentage=20.0),
            ],
        )

        created = await transaction_service.create_transaction(period.id, request)

        assert created.id is not None
        assert created.description == "Percentage split dinner"
        assert created.amount == 10000
        assert created.transaction_kind == TransactionKind.EXPENSE
        assert created.split_kind == SplitKind.PERCENTAGE
        assert len(created.expense_shares or []) == 3

        # Verify balances reflect the percentage split
        balances = await transaction_service.get_all_balances(period.id)
        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # User 1 paid $100, owes $50 (50%) = +$50
        # User 2 owes $30 (30%) = -$30
        # User 3 owes $20 (20%) = -$20
        assert balances_dict[user1.id] == 5000
        assert balances_dict[user2.id] == -3000
        assert balances_dict[user3.id] == -2000

    # ============================================================================
    # Validation Error Tests (tests _validate_transaction indirectly)
    # ============================================================================

    async def test_create_transaction_amount_split_missing_share_amount_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating amount split without share_amount raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid amount split",
            amount=10000,
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.AMOUNT,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=None, share_percentage=50.0
                ),  # Missing share_amount
            ],
        )

        with pytest.raises(ValidationError, match="share_amount"):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_amount_split_totals_mismatch_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating amount split with totals not matching transaction amount raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid amount split",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.AMOUNT,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=6000, share_percentage=60.0),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0
                ),  # Total = 11000, should be 10000
            ],
        )

        with pytest.raises(ValidationError, match="share amounts total"):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_percentage_split_missing_share_percentage_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating percentage split without share_percentage raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid percentage split",
            amount=10000,
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERCENTAGE,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=None
                ),  # Missing share_percentage
            ],
        )

        with pytest.raises(ValidationError, match="share_percentage"):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_percentage_split_not_100_percent_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating percentage split with percentages not totaling 100% raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid percentage split",
            amount=10000,
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERCENTAGE,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=3000, share_percentage=30.0
                ),  # Total = 80%, should be 100%
            ],
        )

        with pytest.raises(ValidationError, match="must equal 100"):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_personal_split_multiple_shares_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating personal split with multiple shares raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid personal split",
            amount=10000,
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0
                ),  # Personal should have only 1 share
            ],
        )

        with pytest.raises(ValidationError, match="exactly 1 share"):
            await transaction_service.create_transaction(period.id, request)

    async def test_create_transaction_personal_split_wrong_user_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test that creating personal split with share for non-payer raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        request = TransactionRequest(
            description="Invalid personal split",
            amount=10000,
            payer_id=user1.id,  # User 1 is payer
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=0, share_amount=10000, share_percentage=100.0
                ),  # Share for user2, but payer is user1
            ],
        )

        with pytest.raises(ValidationError, match="share is not for the payer"):
            await transaction_service.create_transaction(period.id, request)

    async def test_update_transaction_invalid_amount_split_raises_error(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test that updating transaction with invalid amount split raises ValidationError."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        category = await category_factory(name="Groceries")
        group = await group_factory(name="Test Group")
        period = await period_factory(group_id=group.id, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            description="Original Transaction",
            amount=10000,
        )

        request = TransactionRequest(
            description="Updated Transaction",
            amount=10000,
            payer_id=user1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.AMOUNT,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=user1.id, transaction_id=transaction.id, share_amount=6000, share_percentage=60.0
                ),
                ExpenseShareRequest(
                    user_id=user2.id, transaction_id=transaction.id, share_amount=5000, share_percentage=50.0
                ),  # Total = 11000, should be 10000
            ],
        )

        with pytest.raises(ValidationError, match="share amounts total"):
            await transaction_service.update_transaction(transaction.id, request)

    async def test_update_transaction_status_approve(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to APPROVED."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.APPROVED

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.APPROVED

    async def test_update_transaction_status_reject(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to REJECTED."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.REJECTED)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.REJECTED

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.REJECTED

    async def test_update_transaction_status_submit(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to PENDING (submit)."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.DRAFT,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.PENDING)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.PENDING

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.PENDING

    async def test_update_transaction_status_draft(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ):
        """Test updating transaction status to DRAFT."""
        user = await user_factory(email="user@example.com", name="User")
        category = await category_factory(name="Groceries")
        period = await period_factory(group_id=1, name="Test Period")

        transaction = await transaction_factory(
            payer_id=user.id,
            category_id=category.id,
            period_id=period.id,
            description="Test Transaction",
            status=TransactionStatus.PENDING,
        )

        updated = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.DRAFT)

        assert updated.id == transaction.id
        assert updated.status == TransactionStatus.DRAFT

        # Verify the update persisted
        retrieved = await transaction_service.get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.status == TransactionStatus.DRAFT

    async def test_update_transaction_status_not_exists(self, transaction_service: TransactionService):
        """Test updating status for non-existent transaction raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await transaction_service.update_transaction_status(99999, TransactionStatus.APPROVED)
