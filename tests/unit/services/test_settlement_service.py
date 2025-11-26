"""
Unit tests for SettlementService.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, NotFoundError
from app.models import SplitKind, TransactionKind
from app.schemas import ExpenseShareRequest, TransactionRequest
from app.services import (
    CategoryService,
    PeriodService,
    SettlementService,
    TransactionService,
    UserService,
)
from tests.fixtures.factories import (
    create_test_category,
    create_test_group,
    create_test_period,
    create_test_user,
)


@pytest.mark.unit
class TestSettlementService:
    """Test suite for SettlementService."""

    @pytest.fixture
    def settlement_service(self, db_session: AsyncSession) -> SettlementService:
        """Create a SettlementService instance with all dependencies."""
        transaction_service = TransactionService(db_session)
        period_service = PeriodService(db_session)
        category_service = CategoryService(db_session)
        user_service = UserService(db_session)
        return SettlementService(
            transaction_service=transaction_service,
            period_service=period_service,
            category_service=category_service,
            user_service=user_service,
        )

    async def test_get_all_balances_empty_period(self, settlement_service: SettlementService, db_session: AsyncSession):
        """Test getting balances for a period with no transactions."""
        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Empty Period", created_by=user.id)
        db_session.add(period)
        await db_session.commit()

        balances = await settlement_service.get_all_balances(period.id)

        assert isinstance(balances, dict)
        assert len(balances) == 0

    async def test_get_all_balances_with_deposits(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting balances with deposit transactions."""
        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        category = create_test_category(name="Deposit")
        db_session.add(group)
        db_session.add(category)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period")
        db_session.add(period)
        await db_session.commit()

        # Create deposits
        transaction_service = TransactionService(db_session)
        deposit1 = TransactionRequest(
            description="User 1 deposit",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )
        deposit2 = TransactionRequest(
            description="User 2 deposit",
            amount=5000,  # $50.00
            payer_id=user2.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.DEPOSIT,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[],
        )
        await transaction_service.create_transaction(deposit1)
        await transaction_service.create_transaction(deposit2)

        balances = await settlement_service.get_all_balances(period.id)

        assert balances[user1.id] == 10000  # User 1 is owed $100
        assert balances[user2.id] == 5000  # User 2 is owed $50

    async def test_get_all_balances_with_expenses(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting balances with expense transactions."""
        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        category = create_test_category(name="Groceries")
        db_session.add(group)
        db_session.add(category)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period")
        db_session.add(period)
        await db_session.commit()

        # Create expense: User 1 pays $100, split equally between User 1 and User 2
        transaction_service = TransactionService(db_session)
        expense = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )
        await transaction_service.create_transaction(expense)

        balances = await settlement_service.get_all_balances(period.id)

        # User 1 paid $100, owes $50 share = +$50
        # User 2 owes $50 share = -$50
        assert balances[user1.id] == 5000
        assert balances[user2.id] == -5000

    async def test_get_settlement_plan_period_not_exists(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting settlement plan for non-existent period raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await settlement_service.get_settlement_plan(99999)

    async def test_get_settlement_plan_period_already_closed(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting settlement plan for already closed period raises BusinessRuleError."""
        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Closed Period", end_date=datetime.now(UTC))
        db_session.add(period)
        await db_session.commit()

        with pytest.raises(BusinessRuleError):
            await settlement_service.get_settlement_plan(period.id)

    async def test_get_settlement_plan_no_settlement_category(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting settlement plan when Settlement category doesn't exist raises NotFoundError."""
        # Create required dependencies
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        db_session.add(group)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period")
        db_session.add(period)
        await db_session.commit()

        # Settlement category doesn't exist
        with pytest.raises(NotFoundError):
            await settlement_service.get_settlement_plan(period.id)

    async def test_get_settlement_plan_with_balances(
        self, settlement_service: SettlementService, db_session: AsyncSession
    ):
        """Test getting settlement plan for period with balances."""
        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        category = create_test_category(name="Groceries")
        settlement_category = create_test_category(name="Settlement")
        db_session.add(group)
        db_session.add(category)
        db_session.add(settlement_category)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period")
        db_session.add(period)
        await db_session.commit()

        # Create expense: User 1 pays $100, split equally
        transaction_service = TransactionService(db_session)
        expense = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )
        await transaction_service.create_transaction(expense)

        plan = await settlement_service.get_settlement_plan(period.id)

        assert isinstance(plan, list)
        # User 1 is owed $50, User 2 owes $50
        # So plan should have transactions for both
        assert len(plan) == 2
        # Find transactions for each user
        user1_tx = next((t for t in plan if t.payer_id == user1.id), None)
        user2_tx = next((t for t in plan if t.payer_id == user2.id), None)
        assert user1_tx is not None
        assert user2_tx is not None
        # User 1 should receive deposit (positive balance)
        assert user1_tx.transaction_kind == TransactionKind.DEPOSIT
        assert user1_tx.amount > 0
        # User 2 should make payment (negative balance)
        assert user2_tx.transaction_kind == TransactionKind.REFUND
        assert user2_tx.amount < 0

    async def test_apply_settlement_plan(self, settlement_service: SettlementService, db_session: AsyncSession):
        """Test applying settlement plan to a period."""
        # Create required dependencies
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        group = create_test_group(name="Test Group")
        category = create_test_category(name="Groceries")
        settlement_category = create_test_category(name="Settlement")
        db_session.add(group)
        db_session.add(category)
        db_session.add(settlement_category)
        await db_session.commit()

        period = create_test_period(group_id=group.id, name="Test Period")
        db_session.add(period)
        await db_session.commit()

        # Create expense
        transaction_service = TransactionService(db_session)
        expense = TransactionRequest(
            description="Dinner",
            amount=10000,  # $100.00
            payer_id=user1.id,
            category_id=category.id,
            period_id=period.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=user1.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=user2.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )
        await transaction_service.create_transaction(expense)

        # Apply settlement
        await settlement_service.apply_settlement_plan(period.id, db_session)

        # Verify period is settled
        period_service = PeriodService(db_session)
        settled_period = await period_service.get_period_by_id(period.id)
        assert settled_period is not None
        assert settled_period.is_closed is True

        # Verify settlement transactions were created
        settlement_transactions = await transaction_service.get_transactions_by_period_id(period.id)
        settlement_txs = [tx for tx in settlement_transactions if "Settlement" in (tx.description or "")]
        assert len(settlement_txs) > 0
