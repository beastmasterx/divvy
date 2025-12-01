"""
API tests for Transaction endpoints.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Category,
    Group,
    GroupRole,
    Period,
    SplitKind,
    Transaction,
    TransactionKind,
    TransactionStatus,
    User,
)
from app.schemas.transaction import ExpenseShareRequest, TransactionRequest, TransactionResponse


@pytest.mark.api
class TestTransactionsAPI:
    """Test suite for Transactions API endpoints."""

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

    @pytest.fixture
    async def draft_transaction(
        self,
        period_in_group: Period,
        owner_user: User,
        category_factory: Callable[..., Awaitable[Category]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
    ) -> Transaction:
        """Create a draft transaction."""
        category = await category_factory(name="Test Category")
        return await transaction_factory(
            period_id=period_in_group.id,
            payer_id=owner_user.id,
            category_id=category.id,
            description="Draft Transaction",
            amount=10000,
            created_by=owner_user.id,
        )

    # ============================================================================
    # GET /transactions/{transaction_id} - Get transaction by ID
    # ============================================================================

    async def test_get_transaction_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
        draft_transaction: Transaction,
    ):
        """Test endpoint requires authentication."""
        response = await unauthenticated_async_client.get(
            f"/api/v1/transactions/{draft_transaction.id}", follow_redirects=True
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_transaction_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
    ):
        """Test endpoint requires group membership (security-by-obscurity: non-members get 404)."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            # Security-by-obscurity: non-members get 404, not 403
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction retrieval."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.id == draft_transaction.id
            assert transaction.amount == 10000

    async def test_get_transaction_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test GET returns 404 for non-existent transaction."""
        response = await async_client.get("/api/v1/transactions/99999", follow_redirects=True)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================================
    # PUT /transactions/{transaction_id} - Update transaction
    # ============================================================================

    async def test_update_transaction_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
    ):
        """Test update requires group membership (security-by-obscurity: non-members get 404)."""
        request = TransactionRequest(
            description="Updated Transaction",
            amount=20000,
            payer_id=draft_transaction.payer_id,
            category_id=draft_transaction.category_id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=draft_transaction.payer_id,
                    transaction_id=0,
                    share_amount=20000,
                    share_percentage=None,
                )
            ],
        )

        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            # Security-by-obscurity: non-members get 404, not 403
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_transaction_requires_draft_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test update requires transaction to be in draft status."""
        async for client in async_client_factory(owner_user):
            # First submit the transaction (changes status to pending)
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to update (should fail - not draft anymore)
            request = TransactionRequest(
                description="Updated Transaction",
                amount=20000,
                payer_id=draft_transaction.payer_id,
                category_id=draft_transaction.category_id,
                transaction_kind=TransactionKind.EXPENSE,
                split_kind=SplitKind.PERSONAL,
                expense_shares=[
                    ExpenseShareRequest(
                        user_id=draft_transaction.payer_id,
                        transaction_id=0,
                        share_amount=20000,
                        share_percentage=None,
                    )
                ],
            )
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction update."""
        request = TransactionRequest(
            description="Updated Transaction",
            amount=20000,
            payer_id=draft_transaction.payer_id,
            category_id=draft_transaction.category_id,
            transaction_kind=TransactionKind.EXPENSE,
            split_kind=SplitKind.PERSONAL,
            expense_shares=[
                ExpenseShareRequest(
                    user_id=draft_transaction.payer_id,
                    transaction_id=0,
                    share_amount=20000,
                    share_percentage=None,
                )
            ],
        )

        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.description == "Updated Transaction"
            assert transaction.amount == 20000

    # ============================================================================
    # PUT /transactions/{transaction_id}/submit - Submit transaction
    # ============================================================================

    async def test_submit_transaction_requires_creator(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test submit requires transaction creator (even if member)."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Member can access but not submit someone else's transaction
            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_submit_transaction_requires_draft_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test submit requires transaction to be in draft status."""
        async for client in async_client_factory(owner_user):
            # Submit once (changes to pending)
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to submit again (should fail - not draft anymore)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_submit_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction submission by owner."""
        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.status == TransactionStatus.PENDING

    async def test_submit_transaction_success_as_member(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        period_in_group: Period,
        category_factory: Callable[..., Awaitable[Category]],
        transaction_factory: Callable[..., Awaitable[Transaction]],
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test successful transaction submission by member (creator)."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        # Create a transaction by member_user
        category = await category_factory(name="Test Category")
        member_transaction = await transaction_factory(
            period_id=period_in_group.id,
            payer_id=member_user.id,
            category_id=category.id,
            description="Member Transaction",
            amount=5000,
            created_by=member_user.id,
        )

        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/transactions/{member_transaction.id}/submit",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.status == TransactionStatus.PENDING

    # ============================================================================
    # PUT /transactions/{transaction_id}/approve - Approve transaction
    # ============================================================================

    async def test_approve_transaction_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test approve requires owner or admin role."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        async for client in async_client_factory(member_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to approve as member (should fail - requires owner/admin)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/approve",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_approve_transaction_requires_pending_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test approve requires transaction to be in pending status."""
        async for client in async_client_factory(owner_user):
            # Try to approve draft (should fail - not pending)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/approve",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_approve_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction approval."""
        async for client in async_client_factory(owner_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Then approve
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/approve",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.status == TransactionStatus.APPROVED

    # ============================================================================
    # PUT /transactions/{transaction_id}/reject - Reject transaction
    # ============================================================================

    async def test_reject_transaction_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test reject requires owner or admin role."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        async for client in async_client_factory(member_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to reject as member (should fail - requires owner/admin)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/reject",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_reject_transaction_requires_pending_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test reject requires transaction to be in pending status."""
        async for client in async_client_factory(owner_user):
            # Try to reject draft (should fail - not pending)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/reject",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_reject_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction rejection."""
        async for client in async_client_factory(owner_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Then reject
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/reject",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.status == TransactionStatus.REJECTED

    # ============================================================================
    # PUT /transactions/{transaction_id}/draft - Draft transaction
    # ============================================================================

    async def test_draft_transaction_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
    ):
        """Test draft requires group membership (security-by-obscurity: non-members get 404)."""
        async for client in async_client_factory(member_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to draft as non-member (should get 404)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/draft",
                follow_redirects=True,
            )

            # Security-by-obscurity: non-members get 404, not 403
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_draft_transaction_requires_pending_or_rejected_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test draft requires transaction to be in pending or rejected status."""
        async for client in async_client_factory(owner_user):
            # Try to draft a draft transaction (should fail - not pending/rejected)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/draft",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_draft_transaction_requires_creator(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test draft requires transaction creator."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        async for client in async_client_factory(member_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Try to draft as non-creator (should fail)
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/draft",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_draft_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction drafting (from pending/rejected)."""
        async for client in async_client_factory(owner_user):
            # First submit to make it pending
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )

            # Then draft it back
            response = await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/draft",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            transaction = TransactionResponse.model_validate(response.json())
            assert transaction.status == TransactionStatus.DRAFT

    # ============================================================================
    # DELETE /transactions/{transaction_id} - Delete transaction
    # ============================================================================

    async def test_delete_transaction_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
    ):
        """Test delete requires group membership (security-by-obscurity: non-members get 404)."""
        async for client in async_client_factory(member_user):
            # Try to delete as non-member (should get 404)
            response = await client.delete(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            # Security-by-obscurity: non-members get 404, not 403
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_transaction_requires_creator(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        draft_transaction: Transaction,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        db_session: AsyncSession,
    ):
        """Test delete requires transaction creator."""
        # Add member_user as member of the group
        await group_with_role_factory(
            user_id=member_user.id,
            role=GroupRole.MEMBER,
            group_id=group_with_owner.id,
        )
        await db_session.commit()

        async for client in async_client_factory(member_user):
            # Try to delete as non-creator (should fail)
            response = await client.delete(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_transaction_requires_draft_or_rejected_status(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test delete requires transaction to be in draft or rejected status."""
        async for client in async_client_factory(owner_user):
            # Submit and approve (changes to approved)
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/submit",
                follow_redirects=True,
            )
            await client.put(
                f"/api/v1/transactions/{draft_transaction.id}/approve",
                follow_redirects=True,
            )

            # Try to delete (should fail - not draft/rejected)
            response = await client.delete(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_transaction_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        draft_transaction: Transaction,
    ):
        """Test successful transaction deletion."""
        async for client in async_client_factory(owner_user):
            response = await client.delete(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            # Verify transaction is deleted
            get_response = await client.get(
                f"/api/v1/transactions/{draft_transaction.id}",
                follow_redirects=True,
            )
            assert get_response.status_code == status.HTTP_404_NOT_FOUND
