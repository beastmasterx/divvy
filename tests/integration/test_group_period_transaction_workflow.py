"""
Integration tests for the complete group → period → transaction → settlement workflow.

This test suite verifies that multiple services work together correctly
to support the full expense splitting workflow.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Category,
    Group,
    GroupRole,
    Period,
    PeriodStatus,
    SplitKind,
    TransactionKind,
    TransactionStatus,
    User,
)
from app.schemas import ExpenseShareRequest, GroupRequest, PeriodRequest, TransactionRequest
from app.services import (
    AuthorizationService,
    GroupService,
    PeriodService,
    SettlementService,
    TransactionService,
    UserService,
)


@pytest.mark.integration
class TestGroupPeriodTransactionWorkflow:
    """Integration tests for the complete expense splitting workflow."""

    # ============================================================================
    # Full Workflow: Create Group → Add Members → Create Period → Add Transactions → Settle
    # ============================================================================

    async def test_complete_expense_splitting_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test the complete workflow from group creation to settlement."""
        # Initialize services
        authorization_service = AuthorizationService(db_session)
        period_service = PeriodService(db_session)
        transaction_service = TransactionService(db_session)
        user_service = UserService(db_session)
        from app.repositories import SettlementRepository

        settlement_repository = SettlementRepository(db_session)
        settlement_service = SettlementService(period_service, transaction_service, user_service, settlement_repository)
        group_service = GroupService(db_session, authorization_service, period_service)

        # Step 1: Create users
        owner = await user_factory(email="owner@example.com", name="Owner")
        member1 = await user_factory(email="member1@example.com", name="Member 1")
        member2 = await user_factory(email="member2@example.com", name="Member 2")

        # Step 2: Create group
        group_request = GroupRequest(name="Test Group")
        group_response = await group_service.create_group(group_request, owner.id)
        group_id = group_response.id

        # Verify owner role was assigned
        assert await group_service.is_owner(group_id, owner.id)
        assert await group_service.is_member(group_id, owner.id)

        # Step 3: Add members to group
        await authorization_service.assign_group_role(member1.id, group_id, GroupRole.MEMBER)
        await authorization_service.assign_group_role(member2.id, group_id, GroupRole.MEMBER)

        # Verify memberships
        assert await group_service.is_member(group_id, member1.id)
        assert await group_service.is_member(group_id, member2.id)

        # Step 4: Create period
        period_request = PeriodRequest(name="January 2024")
        period_response = await period_service.create_period(group_id, period_request)
        period_id = period_response.id

        # Verify period was created
        assert period_response.group_id == group_id
        assert period_response.name == "January 2024"
        assert period_response.status == PeriodStatus.OPEN

        # Step 5: Create category
        category = await category_factory(name="Groceries")

        # Step 6: Add transactions
        # Transaction 1: Member 1 pays $100 expense, split evenly
        transaction1_request = TransactionRequest(
            description="Grocery shopping",
            amount=10000,  # $100.00 in cents
            payer_id=member1.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=3333, share_percentage=33.33),
                ExpenseShareRequest(user_id=member1.id, transaction_id=0, share_amount=3333, share_percentage=33.33),
                ExpenseShareRequest(user_id=member2.id, transaction_id=0, share_amount=3334, share_percentage=33.34),
            ],
        )
        transaction1 = await transaction_service.create_transaction(period_id, transaction1_request)
        assert transaction1.status == TransactionStatus.DRAFT
        assert transaction1.amount == 10000

        # Submit transaction 1
        transaction1 = await transaction_service.update_transaction_status(transaction1.id, TransactionStatus.PENDING)
        assert transaction1.status == TransactionStatus.PENDING

        # Approve transaction 1
        transaction1 = await transaction_service.update_transaction_status(transaction1.id, TransactionStatus.APPROVED)
        assert transaction1.status == TransactionStatus.APPROVED

        # Transaction 2: Member 2 pays $50 expense, split evenly
        transaction2_request = TransactionRequest(
            description="Utilities",
            amount=5000,  # $50.00 in cents
            payer_id=member2.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=1666, share_percentage=33.33),
                ExpenseShareRequest(user_id=member1.id, transaction_id=0, share_amount=1667, share_percentage=33.34),
                ExpenseShareRequest(user_id=member2.id, transaction_id=0, share_amount=1667, share_percentage=33.33),
            ],
        )
        transaction2 = await transaction_service.create_transaction(period_id, transaction2_request)
        transaction2 = await transaction_service.update_transaction_status(transaction2.id, TransactionStatus.APPROVED)
        assert transaction2.status == TransactionStatus.APPROVED

        # Step 7: Check balances
        balances = await transaction_service.get_all_balances(period_id)
        # Member 1 paid $100, owes $50 (split of $100) + $16.67 (split of $50) = owes $66.67, but paid $100
        # Member 2 paid $50, owes $50 (split of $100) + $16.67 (split of $50) = owes $66.67, but paid $50
        # Owner owes $50 (split of $100) + $16.67 (split of $50) = owes $66.67, paid $0
        assert len(balances) > 0

        # Step 8: Close period (must be closed before getting settlement plan)
        closed_period = await period_service.close_period(period_id)
        assert closed_period.status == PeriodStatus.CLOSED
        assert closed_period.end_date is not None

        # Step 9: Get settlement plan (requires period to be closed)
        settlement_plan = await settlement_service.get_settlement_plan(period_id)
        assert isinstance(settlement_plan, list)
        # Should have settlements to balance the accounts

        # Step 10: Apply settlement plan (this also calls settle_period internally)
        await settlement_service.apply_settlement_plan(period_id, db_session)

        # Verify period is settled
        settled_period = await period_service.get_period_by_id(period_id)
        assert settled_period is not None
        assert settled_period.status == PeriodStatus.SETTLED

    async def test_transaction_lifecycle_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        category_factory: Callable[..., Awaitable[Category]],
        authorization_service: AuthorizationService,
    ):
        """Test the complete transaction lifecycle: draft → submit → approve."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        period = await period_factory(group_id=group.id, name="Test Period", created_by=owner.id)
        category = await category_factory(name="Test Category")

        transaction_service = TransactionService(db_session)

        # Create draft transaction
        transaction_request = TransactionRequest(
            description="Test Expense",
            amount=10000,
            payer_id=owner.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=10000, share_percentage=100.0),
            ],
        )
        transaction = await transaction_service.create_transaction(period.id, transaction_request)

        # Verify draft state
        assert transaction.status == TransactionStatus.DRAFT
        assert transaction.description == "Test Expense"
        assert transaction.amount == 10000

        # Update transaction while in draft
        updated_request = TransactionRequest(
            description="Updated Expense",
            amount=15000,
            payer_id=owner.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=15000, share_percentage=100.0),
            ],
        )
        updated_transaction = await transaction_service.update_transaction(transaction.id, updated_request)
        assert updated_transaction.description == "Updated Expense"
        assert updated_transaction.amount == 15000

        # Submit transaction
        submitted_transaction = await transaction_service.update_transaction_status(
            updated_transaction.id, TransactionStatus.PENDING
        )
        assert submitted_transaction.status == TransactionStatus.PENDING

        # Approve transaction
        approved_transaction = await transaction_service.update_transaction_status(
            submitted_transaction.id, TransactionStatus.APPROVED
        )
        assert approved_transaction.status == TransactionStatus.APPROVED

        # Verify transaction affects balances
        balances = await transaction_service.get_all_balances(period.id)
        assert len(balances) > 0

    async def test_multi_user_transaction_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        category_factory: Callable[..., Awaitable[Category]],
        authorization_service: AuthorizationService,
    ):
        """Test transactions with multiple users and custom expense shares."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        member1 = await user_factory(email="member1@example.com", name="Member 1")
        member2 = await user_factory(email="member2@example.com", name="Member 2")

        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)
        await authorization_service.assign_group_role(member1.id, group.id, GroupRole.MEMBER)
        await authorization_service.assign_group_role(member2.id, group.id, GroupRole.MEMBER)

        period = await period_factory(group_id=group.id, name="Test Period", created_by=owner.id)
        category = await category_factory(name="Test Category")

        transaction_service = TransactionService(db_session)

        # Create transaction with custom expense shares
        expense_shares = [
            ExpenseShareRequest(
                user_id=member1.id, transaction_id=0, share_amount=6000  # $60
            ),  # transaction_id will be set by service
            ExpenseShareRequest(
                user_id=member2.id, transaction_id=0, share_amount=4000  # $40
            ),  # transaction_id will be set by service
        ]

        transaction_request = TransactionRequest(
            description="Custom Split Expense",
            amount=10000,  # $100 total
            payer_id=owner.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.AMOUNT,
            expense_shares=expense_shares,
        )

        transaction = await transaction_service.create_transaction(period.id, transaction_request)
        transaction = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)

        # Verify expense shares were created
        assert transaction.expense_shares is not None
        assert len(transaction.expense_shares) == 2

        # Check balances
        balances = await transaction_service.get_all_balances(period.id)
        # Convert to dict for easier assertions
        balances_dict = {b.user_id: b.balance for b in balances}
        # Owner paid $100, member1 owes $60, member2 owes $40
        assert balances_dict[owner.id] > 0  # Owner is owed money
        assert balances_dict[member1.id] < 0  # Member1 owes money
        assert balances_dict[member2.id] < 0  # Member2 owes money

    async def test_period_creation_and_management_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test creating and managing multiple periods for a group."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        period_service = PeriodService(db_session)

        # Create first period
        period1_request = PeriodRequest(name="January 2024")
        period1 = await period_service.create_period(group.id, period1_request)
        assert period1.status == PeriodStatus.OPEN
        assert period1.name == "January 2024"

        # Create second period (should be allowed - multiple open periods possible)
        period2_request = PeriodRequest(name="February 2024")
        period2 = await period_service.create_period(group.id, period2_request)
        assert period2.status == PeriodStatus.OPEN
        assert period2.name == "February 2024"

        # Get all periods for group
        periods = await period_service.get_periods_by_group_id(group.id)
        period_ids = {p.id for p in periods}
        assert period1.id in period_ids
        assert period2.id in period_ids

        # Close first period
        closed_period1 = await period_service.close_period(period1.id)
        assert closed_period1.status == PeriodStatus.CLOSED

        # Settle first period
        settled_period1 = await period_service.settle_period(period1.id)
        assert settled_period1.status == PeriodStatus.SETTLED

        # Second period should still be open
        period2_after = await period_service.get_period_by_id(period2.id)
        assert period2_after is not None
        assert period2_after.status == PeriodStatus.OPEN
