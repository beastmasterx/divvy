"""
Integration tests for business rules that span multiple services.

These tests verify that business rules are correctly enforced
when multiple services interact.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Group, GroupRole, Period, SplitKind, TransactionKind, User
from app.schemas import ExpenseShareRequest, GroupRequest, PeriodRequest, TransactionRequest
from app.services import (
    AuthorizationService,
    GroupService,
    PeriodService,
    TransactionService,
)


@pytest.mark.integration
class TestBusinessRulesIntegration:
    """Integration tests for cross-service business rules."""

    async def test_cannot_delete_group_with_unsettled_period(
        self,
        db_session: AsyncSession,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test that groups with unsettled periods cannot be deleted via API."""
        # Setup services
        authorization_service = AuthorizationService(db_session)
        period_service = PeriodService(db_session)
        group_service = GroupService(db_session, authorization_service, period_service)
        transaction_service = TransactionService(db_session)

        # Create group and period
        owner = await user_factory(email="owner@example.com", name="Owner")
        group_request = GroupRequest(name="Test Group")
        group = await group_service.create_group(group_request, owner.id)

        period_request = PeriodRequest(name="Active Period")
        period = await period_service.create_period(group.id, period_request)

        # Add transaction to period
        category = await category_factory(name="Test Category")
        transaction_request = TransactionRequest(
            description="Test Transaction",
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
        from app.models import TransactionStatus

        await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)

        # Commit all changes so they're visible to the API client
        await db_session.commit()

        # Try to delete group via API - should fail with 422 (BusinessRuleError)
        async for client in async_client_factory(owner):
            response = await client.delete(f"/api/v1/groups/{group.id}", follow_redirects=True)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
            error_data = response.json()
            assert "detail" in error_data

        # Close and settle period
        await period_service.close_period(period.id)
        await period_service.settle_period(period.id)

        # Commit period status changes
        await db_session.commit()

        # Now should be able to delete group via API
        async for client in async_client_factory(owner):
            response = await client.delete(f"/api/v1/groups/{group.id}", follow_redirects=True)
            assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify group is deleted
        deleted_group = await group_service.get_group_by_id(group.id)
        assert deleted_group is None

    async def test_cannot_remove_user_with_unsettled_period(
        self,
        db_session: AsyncSession,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        category_factory: Callable[..., Awaitable[Category]],
        authorization_service: AuthorizationService,
    ):
        """Test that users with transactions in unsettled periods cannot be removed via API."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        member = await user_factory(email="member@example.com", name="Member")

        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)
        await authorization_service.assign_group_role(member.id, group.id, GroupRole.MEMBER)

        period = await period_factory(group_id=group.id, name="Active Period", created_by=owner.id)
        category = await category_factory(name="Test Category")

        transaction_service = TransactionService(db_session)
        group_service = GroupService(db_session, authorization_service, PeriodService(db_session))

        # Add transaction with member as payer
        transaction_request = TransactionRequest(
            description="Member's Transaction",
            amount=10000,
            payer_id=member.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
                ExpenseShareRequest(user_id=member.id, transaction_id=0, share_amount=5000, share_percentage=50.0),
            ],
        )
        transaction = await transaction_service.create_transaction(period.id, transaction_request)
        from app.models import TransactionStatus

        await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)

        # Commit all changes so they're visible to the API client
        await db_session.commit()

        # Try to remove member via API - should fail with 422 (BusinessRuleError)
        async for client in async_client_factory(owner):
            response = await client.delete(f"/api/v1/groups/{group.id}/users/{member.id}", follow_redirects=True)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
            error_data = response.json()
            assert "detail" in error_data

        # Close and settle period
        period_service = PeriodService(db_session)
        await period_service.close_period(period.id)
        await period_service.settle_period(period.id)

        # Commit period status changes
        await db_session.commit()

        # Now should be able to remove member via API
        async for client in async_client_factory(owner):
            response = await client.delete(f"/api/v1/groups/{group.id}/users/{member.id}", follow_redirects=True)
            assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify member is removed
        assert not await group_service.is_member(group.id, member.id)

    async def test_group_ownership_transfer_workflow(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test transferring group ownership between users."""
        # Setup
        authorization_service = AuthorizationService(db_session)
        group_service = GroupService(db_session, authorization_service, PeriodService(db_session))

        owner1 = await user_factory(email="owner1@example.com", name="Owner 1")
        owner2 = await user_factory(email="owner2@example.com", name="Owner 2")

        # Create group with owner1
        group_request = GroupRequest(name="Test Group")
        group = await group_service.create_group(group_request, owner1.id)

        # Verify owner1 is owner
        assert await group_service.is_owner(group.id, owner1.id)
        assert not await group_service.is_owner(group.id, owner2.id)

        # Add owner2 as a member first (required for transfer_group_owner)
        await group_service.assign_group_role(group.id, owner2.id, GroupRole.MEMBER)

        # Transfer ownership to owner2
        await group_service.transfer_group_owner(group.id, owner2.id)

        # Verify ownership transferred
        assert not await group_service.is_owner(group.id, owner1.id)
        assert await group_service.is_owner(group.id, owner2.id)

        # Verify owner1 is still a member
        assert await group_service.is_member(group.id, owner1.id)

    async def test_period_status_transitions(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test that period status transitions follow correct workflow."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)

        period_service = PeriodService(db_session)

        # Create period - should be OPEN
        period_request = PeriodRequest(name="Test Period")
        period = await period_service.create_period(group.id, period_request)
        assert period.status.value == "open"

        # Close period - should be CLOSED
        closed_period = await period_service.close_period(period.id)
        assert closed_period.status.value == "closed"

        # Settle period - should be SETTLED
        settled_period = await period_service.settle_period(period.id)
        assert settled_period.status.value == "settled"

        # Cannot close or modify settled period
        # (This would be tested in service unit tests, but verifying here for integration)

    async def test_transaction_approval_workflow_with_roles(
        self,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        group_factory: Callable[..., Awaitable[Group]],
        period_factory: Callable[..., Awaitable[Period]],
        category_factory: Callable[..., Awaitable[Category]],
        authorization_service: AuthorizationService,
    ):
        """Test that transaction approval requires proper role permissions."""
        # Setup
        owner = await user_factory(email="owner@example.com", name="Owner")
        admin = await user_factory(email="admin@example.com", name="Admin")
        member = await user_factory(email="member@example.com", name="Member")

        group = await group_factory(name="Test Group")
        await authorization_service.assign_group_role(owner.id, group.id, GroupRole.OWNER)
        await authorization_service.assign_group_role(admin.id, group.id, GroupRole.ADMIN)
        await authorization_service.assign_group_role(member.id, group.id, GroupRole.MEMBER)

        period = await period_factory(group_id=group.id, name="Test Period", created_by=owner.id)
        category = await category_factory(name="Test Category")

        transaction_service = TransactionService(db_session)

        # Member creates transaction
        transaction_request = TransactionRequest(
            description="Member's Transaction",
            amount=10000,
            payer_id=member.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.EQUAL,
            expense_shares=[
                ExpenseShareRequest(user_id=owner.id, transaction_id=0, share_amount=3333, share_percentage=33.33),
                ExpenseShareRequest(user_id=admin.id, transaction_id=0, share_amount=3333, share_percentage=33.33),
                ExpenseShareRequest(user_id=member.id, transaction_id=0, share_amount=3334, share_percentage=33.34),
            ],
        )
        transaction = await transaction_service.create_transaction(period.id, transaction_request)
        assert transaction.status.value == "draft"

        # Member submits transaction
        from app.models import TransactionStatus

        transaction = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.PENDING)
        assert transaction.status.value == "pending"

        # Admin approves transaction (admin has permission)
        transaction = await transaction_service.update_transaction_status(transaction.id, TransactionStatus.APPROVED)
        assert transaction.status.value == "approved"

        # Verify transaction affects balances
        balances = await transaction_service.get_all_balances(period.id)
        assert len(balances) > 0
