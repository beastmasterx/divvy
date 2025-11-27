"""
Unit tests for AccountLinkRequestRepository.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccountLinkRequestStatus, IdentityProviderName
from app.models.user import AccountLinkRequest, User
from app.repositories import AccountLinkRequestRepository
from tests.fixtures.factories import create_test_account_link_request


@pytest.mark.unit
class TestAccountLinkRequestRepository:
    """Test suite for AccountLinkRequestRepository."""

    @pytest.fixture
    def account_link_request_repository(self, db_session: AsyncSession) -> AccountLinkRequestRepository:
        return AccountLinkRequestRepository(db_session)

    async def test_get_request_by_id_exists(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving an account link request by ID when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="test_token_123",
        )

        retrieved = await account_link_request_repository.get_request_by_id(request.id)

        assert retrieved is not None
        assert retrieved.id == request.id
        assert retrieved.request_token == "test_token_123"
        assert retrieved.user_id == user.id
        assert retrieved.status == AccountLinkRequestStatus.PENDING.value

    async def test_get_request_by_id_not_exists(self, account_link_request_repository: AccountLinkRequestRepository):
        """Test retrieving an account link request by ID when it doesn't exist."""
        result = await account_link_request_repository.get_request_by_id(99999)

        assert result is None

    async def test_get_request_by_token_exists(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving an account link request by token when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
            request_token="unique_token_789",
        )

        retrieved = await account_link_request_repository.get_request_by_token(request.request_token)

        assert retrieved is not None
        assert retrieved.request_token == request.request_token
        assert retrieved.user_id == user.id

    async def test_get_request_by_token_not_exists(self, account_link_request_repository: AccountLinkRequestRepository):
        """Test retrieving an account link request by token when it doesn't exist."""
        result = await account_link_request_repository.get_request_by_token("nonexistent_token")

        assert result is None

    async def test_get_pending_requests_by_user_id_empty(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test retrieving pending requests for a user when none exist."""
        user = await user_factory(email="test@example.com", name="Test User")

        requests = await account_link_request_repository.get_pending_requests_by_user_id(user.id)

        assert isinstance(requests, list)
        assert len(requests) == 0

    async def test_get_pending_requests_by_user_id_multiple(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving all pending requests for a user when multiple exist."""
        user = await user_factory(email="test@example.com", name="Test User")
        user2 = await user_factory(email="test2@example.com", name="Test User 2")

        # Create multiple pending requests for user
        request1 = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="token_1",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        request2 = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
            request_token="token_2",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        # Create approved request (should not be included)
        request3 = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.FACEBOOK,
            external_id="fb_789",
            request_token="token_3",
            status=AccountLinkRequestStatus.APPROVED.value,
        )
        # Create request for different user (should not be included)
        request4 = await account_link_request_factory(
            user_id=user2.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_999",
            request_token="token_4",
            status=AccountLinkRequestStatus.PENDING.value,
        )

        requests = await account_link_request_repository.get_pending_requests_by_user_id(user.id)

        assert len(requests) == 2

        tokens = {req.request_token for req in requests}

        assert request1.request_token in tokens
        assert request2.request_token in tokens
        assert request3.request_token not in tokens
        assert request4.request_token not in tokens

    async def test_get_pending_request_by_provider_and_external_id_exists(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving a pending request by provider and external_id when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="pending_token",
            status=AccountLinkRequestStatus.PENDING.value,
        )

        retrieved = await account_link_request_repository.get_pending_request_by_provider_and_external_id(
            request.identity_provider, request.external_id
        )

        assert retrieved is not None
        assert retrieved.request_token == request.request_token
        assert retrieved.user_id == user.id

    async def test_get_pending_request_by_provider_and_external_id_not_exists(
        self, account_link_request_repository: AccountLinkRequestRepository
    ):
        """Test retrieving a pending request by provider and external_id when it doesn't exist."""
        result = await account_link_request_repository.get_pending_request_by_provider_and_external_id(
            IdentityProviderName.MICROSOFT, "nonexistent"
        )

        assert result is None

    async def test_get_pending_request_by_provider_and_external_id_approved_not_included(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test that approved requests are not returned by get_pending_request_by_provider_and_external_id."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approved_token",
            status=AccountLinkRequestStatus.APPROVED.value,
        )

        result = await account_link_request_repository.get_pending_request_by_provider_and_external_id(
            request.identity_provider, request.external_id
        )

        assert result is None

    async def test_get_expired_requests(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving all expired pending requests."""
        user = await user_factory(email="test@example.com", name="Test User")

        # Create expired pending request
        expired_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="expired_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
        )
        # Create future pending request (should not be included)
        _ = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
            request_token="future_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),  # Expires in 24 hours
        )
        # Approved request (should not be included even if expired)
        _ = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.FACEBOOK,
            external_id="fb_789",
            request_token="approved_expired_token",
            status=AccountLinkRequestStatus.APPROVED.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        expired_requests = await account_link_request_repository.get_expired_requests()

        assert len(expired_requests) == 1
        assert expired_requests[0].request_token == expired_request.request_token
        assert expired_requests[0].status == AccountLinkRequestStatus.PENDING.value

    async def test_create_request(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test creating a new account link request."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = create_test_account_link_request(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="new_token_123",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        created = await account_link_request_repository.create_request(request)

        assert created.id is not None
        assert created.request_token == request.request_token
        assert created.user_id == user.id
        assert created.status == AccountLinkRequestStatus.PENDING.value

        # Verify it's in the database
        retrieved = await account_link_request_repository.get_request_by_id(created.id)

        assert retrieved is not None
        assert retrieved.request_token == request.request_token

    async def test_update_request(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test updating an existing account link request."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="update_token",
            status=AccountLinkRequestStatus.PENDING.value,
        )

        # Update it
        request.status = AccountLinkRequestStatus.APPROVED.value
        updated = await account_link_request_repository.update_request(request)

        assert updated.status == AccountLinkRequestStatus.APPROVED.value

        # Verify the update persisted
        retrieved = await account_link_request_repository.get_request_by_id(request.id)

        assert retrieved is not None
        assert retrieved.status == AccountLinkRequestStatus.APPROVED.value

    async def test_delete_request_exists(
        self,
        account_link_request_repository: AccountLinkRequestRepository,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test deleting an account link request that exists."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="delete_token",
        )

        # Delete it
        await account_link_request_repository.delete_request(request.id)

        # Verify it's gone
        retrieved = await account_link_request_repository.get_request_by_id(request.id)

        assert retrieved is None

    async def test_delete_request_not_exists(self, account_link_request_repository: AccountLinkRequestRepository):
        """Test deleting an account link request that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await account_link_request_repository.delete_request(99999)
