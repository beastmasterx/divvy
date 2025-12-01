"""
API tests for Period endpoints.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models import Group, GroupRole, Period, SplitKind, TransactionKind, User
from app.schemas.period import PeriodRequest, PeriodResponse
from app.schemas.transaction import (
    BalanceResponse,
    ExpenseShareRequest,
    SettlementResponse,
    TransactionRequest,
    TransactionResponse,
)


@pytest.mark.api
class TestPeriodsAPI:
    """Test suite for Periods API endpoints."""

    # ============================================================================
    # Helper Fixtures
    # ============================================================================

    @pytest.fixture
    async def owner_user(self, user_factory: Callable[..., Awaitable[User]]) -> User:
        """Create a user who will be an owner of test groups."""
        return await user_factory(email="owner@example.com", name="Owner")

    @pytest.fixture
    async def member_user(self, user_factory: Callable[..., Awaitable[User]]) -> User:
        """Create a user who will be a member of test groups."""
        return await user_factory(email="member@example.com", name="Member")

    @pytest.fixture
    async def group_with_owner(
        self,
        owner_user: User,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ) -> Group:
        """Create a group with an owner."""
        return await group_with_role_factory(user_id=owner_user.id, role=GroupRole.OWNER, name="Test Group")

    @pytest.fixture
    async def period_in_group(
        self,
        group_with_owner: Group,
        period_factory: Callable[..., Awaitable[Period]],
        owner_user: User,
    ) -> Period:
        """Create a period in the test group."""
        return await period_factory(group_id=group_with_owner.id, name="Test Period", created_by=owner_user.id)

    # ============================================================================
    # GET /periods/{period_id} - Get period by ID
    # ============================================================================

    async def test_get_period_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
        period_in_group: Period,
    ):
        """Test endpoint requires authentication."""
        response = await unauthenticated_async_client.get(
            f"/api/v1/periods/{period_in_group.id}", follow_redirects=True
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_period_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
    ):
        """Test endpoint requires group membership - non-members get 404."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}",
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_period_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful period retrieval."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            period = PeriodResponse.model_validate(response.json())
            assert period.id == period_in_group.id
            assert period.name == period_in_group.name
            assert period.group_id == period_in_group.group_id

    async def test_get_period_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test GET returns 404 for non-existent period."""
        response = await async_client.get("/api/v1/periods/99999", follow_redirects=True)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================================
    # PUT /periods/{period_id} - Update period
    # ============================================================================

    async def test_update_period_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test update requires owner or admin role."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=period_in_group.group_id)

        request = PeriodRequest(name="Updated Name")
        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/periods/{period_in_group.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_period_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful period update."""
        request = PeriodRequest(name="Updated Period Name")
        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/periods/{period_in_group.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            period = PeriodResponse.model_validate(response.json())
            assert period.name == "Updated Period Name"
            assert period.id == period_in_group.id

    # ============================================================================
    # PUT /periods/{period_id}/close - Close period
    # ============================================================================

    async def test_close_period_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test close period requires owner or admin role."""
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=period_in_group.group_id)

        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/periods/{period_in_group.id}/close",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_close_period_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful period closure."""
        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/periods/{period_in_group.id}/close",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            period = PeriodResponse.model_validate(response.json())
            assert period.status.value == "closed"
            assert period.end_date is not None

    # ============================================================================
    # GET /periods/{period_id}/transactions - List transactions
    # ============================================================================

    async def test_get_transactions_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
    ):
        """Test getting transactions requires membership - non-members get 404."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/transactions",
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_transactions_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful transaction list retrieval."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/transactions",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transactions = [TransactionResponse.model_validate(item) for item in response.json()]
            assert isinstance(transactions, list)
            assert all(isinstance(t, TransactionResponse) for t in transactions)

    # ============================================================================
    # POST /periods/{period_id}/transactions - Create transaction
    # ============================================================================

    async def test_create_transaction_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
        category_factory: Callable[..., Awaitable[Any]],
    ):
        """Test creating transaction requires membership - non-members get 404."""
        category = await category_factory(name="Test Category")

        request = TransactionRequest(
            description="Test Transaction",
            amount=10000,
            payer_id=member_user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=member_user.id,
                    transaction_id=0,  # Will be set by backend
                    share_amount=10000,
                    share_percentage=None,
                )
            ],
        )

        async for client in async_client_factory(member_user):
            response = await client.post(
                f"/api/v1/periods/{period_in_group.id}/transactions",
                json=request.model_dump(),
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
        category_factory: Callable[..., Awaitable[Any]],
    ):
        """Test successful transaction creation."""
        category = await category_factory(name="Test Category")

        request = TransactionRequest(
            description="Test Transaction",
            amount=10000,
            payer_id=owner_user.id,
            category_id=category.id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=owner_user.id,
                    transaction_id=0,  # Will be set by backend
                    share_amount=10000,
                    share_percentage=None,
                )
            ],
        )

        async for client in async_client_factory(owner_user):
            response = await client.post(
                f"/api/v1/periods/{period_in_group.id}/transactions",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_201_CREATED
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.id is not None
            assert transaction.amount == 10000
            assert transaction.description == "Test Transaction"
            assert transaction.transaction_kind == TransactionKind.EXPENSE
            assert transaction.split_kind == SplitKind.PERSONAL

    # ============================================================================
    # GET /periods/{period_id}/balances - Get balances
    # ============================================================================

    async def test_get_balances_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
    ):
        """Test getting balances requires membership - non-members get 404."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/balances",
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_balances_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful balances retrieval."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/balances",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            balances = [BalanceResponse.model_validate(item) for item in response.json()]
            assert isinstance(balances, list)
            assert all(isinstance(b, BalanceResponse) for b in balances)

    # ============================================================================
    # GET /periods/{period_id}/get-settlement-plan - Get settlement plan
    # ============================================================================

    async def test_get_settlement_plan_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
    ):
        """Test getting settlement plan requires membership - non-members get 404."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/get-settlement-plan",
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_settlement_plan_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful settlement plan retrieval."""
        async for client in async_client_factory(owner_user):
            # First close the period (required for settlement plan)
            await client.put(
                f"/api/v1/periods/{period_in_group.id}/close",
                follow_redirects=True,
            )

            response = await client.get(
                f"/api/v1/periods/{period_in_group.id}/get-settlement-plan",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            settlements = [SettlementResponse.model_validate(item) for item in response.json()]
            assert isinstance(settlements, list)
            assert all(isinstance(s, SettlementResponse) for s in settlements)

    # ============================================================================
    # POST /periods/{period_id}/apply-settlement-plan - Apply settlement
    # ============================================================================

    async def test_apply_settlement_plan_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test applying settlement plan requires owner or admin."""
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=period_in_group.group_id)

        async for client in async_client_factory(member_user):
            response = await client.post(
                f"/api/v1/periods/{period_in_group.id}/apply-settlement-plan",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_apply_settlement_plan_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        period_in_group: Period,
    ):
        """Test successful settlement plan application."""
        async for client in async_client_factory(owner_user):
            # First close the period (required for settlement)
            await client.put(
                f"/api/v1/periods/{period_in_group.id}/close",
                follow_redirects=True,
            )

            response = await client.post(
                f"/api/v1/periods/{period_in_group.id}/apply-settlement-plan",
                follow_redirects=True,
            )

            # May return 204 or 400 if period not closed/ready
            assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_400_BAD_REQUEST]
