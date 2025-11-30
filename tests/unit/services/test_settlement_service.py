"""
Unit tests for SettlementService.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Category, Group, Period, SplitKind, TransactionKind, User
from app.schemas import ExpenseShareRequest, TransactionRequest
from app.services import PeriodService, SettlementService, TransactionService


@pytest.mark.unit
class TestSettlementService:
    """Test suite for SettlementService."""

    async def test_get_all_balances_empty_period(
        self,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances for a period with no transactions."""
        # Create required dependencies
        user = await user_factory(email="user@example.com", name="User")
        group = await group_factory(name="Test Group")

        period = await period_factory(group_id=group.id, name="Empty Period", created_by=user.id)

        balances = await transaction_service.get_all_balances(period.id)

        assert isinstance(balances, dict)
        assert len(balances) == 0

    async def test_get_all_balances_with_deposits(
        self,
        settlement_service: SettlementService,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        category_factory: Callable[..., Awaitable[Category]],
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

        assert balances[user1.id] == 10000  # User 1 is owed $100
        assert balances[user2.id] == 5000  # User 2 is owed $50

    async def test_get_all_balances_with_expenses(
        self,
        settlement_service: SettlementService,
        transaction_service: TransactionService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting balances with expense transactions."""
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

        # User 1 paid $100, owes $50 share = +$50
        # User 2 owes $50 share = -$50
        assert balances[user1.id] == 5000
        assert balances[user2.id] == -5000

    async def test_get_settlement_plan_period_not_exists(self, settlement_service: SettlementService):
        """Test getting settlement plan for non-existent period raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await settlement_service.get_settlement_plan(99999)

    async def test_get_settlement_plan_period_already_closed(
        self,
        settlement_service: SettlementService,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting settlement plan for already closed period raises BusinessRuleError."""
        # Create required dependencies
        group = await group_factory(name="Test Group")

        period = await period_factory(group_id=group.id, name="Closed Period", end_date=datetime.now(UTC))

        with pytest.raises(BusinessRuleError):
            await settlement_service.get_settlement_plan(period.id)

    async def test_get_settlement_plan_no_settlement_category(
        self,
        settlement_service: SettlementService,
        period_service: PeriodService,
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting settlement plan for a period with no transactions returns empty plan."""
        # Create required dependencies
        group = await group_factory(name="Test Group")

        period = await period_factory(group_id=group.id, name="Test Period")

        # Close the period first (required for settlement plan)
        await period_service.close_period(period.id)

        # Get settlement plan for period with no transactions
        plan = await settlement_service.get_settlement_plan(period.id)

        # Should return empty plan when there are no balances
        assert isinstance(plan, list)
        assert len(plan) == 0

    async def test_get_settlement_plan_with_balances(
        self,
        settlement_service: SettlementService,
        transaction_service: TransactionService,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test getting settlement plan for period with balances."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Groceries")
        _ = await category_factory(name="Settlement")

        period = await period_factory(group_id=group.id, name="Test Period")

        # Create expense: User 1 pays $100, split equally
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

        # Close the period first (required for settlement plan)
        await period_service.close_period(period.id)

        plan = await settlement_service.get_settlement_plan(period.id)

        assert isinstance(plan, list)
        # User 1 is owed $50, User 2 owes $50
        # Settlement algorithm minimizes transfers, so there should be 1 transfer: User 2 pays User 1 $50
        assert len(plan) == 1
        # Find the settlement entry
        settlement = plan[0]
        # User 2 should pay User 1
        assert settlement.payer_id == user2.id
        assert settlement.payee_id == user1.id
        assert settlement.amount == 5000  # $50.00

    async def test_apply_settlement_plan(
        self,
        db_session: AsyncSession,
        settlement_service: SettlementService,
        transaction_service: TransactionService,
        period_service: PeriodService,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        category_factory: Callable[..., Awaitable[Category]],
        period_factory: Callable[..., Awaitable[Period]],
    ):
        """Test applying settlement plan to a period."""
        # Create required dependencies
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")
        group = await group_factory(name="Test Group")
        category = await category_factory(name="Groceries")
        _ = await category_factory(name="Settlement")

        period = await period_factory(group_id=group.id, name="Test Period")

        # Create expense
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

        # Close the period first (required for settlement)
        await period_service.close_period(period.id)

        # Apply settlement
        await settlement_service.apply_settlement_plan(period.id, db_session)

        # Verify period is settled
        settled_period = await period_service.get_period_by_id(period.id)
        assert settled_period is not None
        assert settled_period.status.value == "settled"

        # Verify settlement entities were created
        settlements = await settlement_service.get_settlements_by_period_id(period.id)
        assert len(settlements) > 0
        # Verify settlement structure
        for settlement in settlements:
            assert settlement.payer_id is not None
            assert settlement.payee_id is not None
            assert settlement.amount > 0
            assert settlement.period_id == period.id
