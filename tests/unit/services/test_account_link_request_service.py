"""
Unit tests for AccountLinkRequestService.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime import utc_now
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.models import AccountLinkRequest, AccountLinkRequestStatus, IdentityProviderName, User, UserIdentity
from app.schemas import AccountLinkRequestCreateRequest, AccountLinkRequestResponse
from app.services import AccountLinkRequestService, UserIdentityService, UserService


@pytest.mark.unit
class TestAccountLinkRequestService:
    """Test suite for AccountLinkRequestService."""

    async def test_get_request_by_id_exists(
        self,
        account_link_request_service: AccountLinkRequestService,
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

        result = await account_link_request_service.get_request_by_id(request.id)

        assert result is not None
        assert isinstance(result, AccountLinkRequestResponse)
        assert result.id == request.id
        assert result.request_token == request.request_token
        assert result.user_id == user.id
        assert result.identity_provider == request.identity_provider
        assert result.status == AccountLinkRequestStatus.PENDING

    async def test_get_request_by_id_not_exists(self, account_link_request_service: AccountLinkRequestService):
        """Test retrieving an account link request by ID when it doesn't exist."""
        result = await account_link_request_service.get_request_by_id(99999)

        assert result is None

    async def test_get_request_by_token_exists(
        self,
        account_link_request_service: AccountLinkRequestService,
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

        result = await account_link_request_service.get_request_by_token(request.request_token)

        assert result is not None
        assert isinstance(result, AccountLinkRequestResponse)
        assert result.request_token == request.request_token
        assert result.user_id == user.id

    async def test_get_request_by_token_not_exists(self, account_link_request_service: AccountLinkRequestService):
        """Test retrieving an account link request by token when it doesn't exist."""
        result = await account_link_request_service.get_request_by_token("nonexistent_token")

        assert result is None

    async def test_get_pending_requests_by_user_id(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test retrieving all pending requests for a specific user."""
        user = await user_factory(email="test@example.com", name="Test User")
        user2 = await user_factory(email="test2@example.com", name="Test User 2")

        # Create pending requests for user
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

        results = await account_link_request_service.get_pending_requests_by_user_id(user.id)

        assert len(results) == 2

        tokens = {req.request_token for req in results}

        assert request1.request_token in tokens
        assert request2.request_token in tokens
        assert request3.request_token not in tokens
        assert request4.request_token not in tokens

    async def test_get_expired_requests(
        self,
        account_link_request_service: AccountLinkRequestService,
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
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        # Create future pending request (should not be included)
        await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
            request_token="future_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        # Create expired approved request (should not be included)
        await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.FACEBOOK,
            external_id="fb_789",
            request_token="approved_expired_token",
            status=AccountLinkRequestStatus.APPROVED.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        results = await account_link_request_service.get_expired_requests()

        assert len(results) == 1
        assert results[0].request_token == expired_request.request_token
        assert results[0].status == AccountLinkRequestStatus.PENDING

    async def test_create_request_success(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test creating a new account link request successfully."""
        user = await user_factory(email="test@example.com", name="Test User")

        request_data = AccountLinkRequestCreateRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_new_123",
            external_email="ms@example.com",
            external_username="ms_user",
        )

        result = await account_link_request_service.create_request(request_data)

        assert result is not None
        assert isinstance(result, AccountLinkRequestResponse)
        assert result.user_id == user.id
        assert result.identity_provider == request_data.identity_provider
        assert result.external_id == request_data.external_id
        assert result.external_email == request_data.external_email
        assert result.external_username == request_data.external_username
        assert result.status == AccountLinkRequestStatus.PENDING
        assert result.request_token is not None
        assert len(result.request_token) > 0
        assert result.expires_at > utc_now()

    async def test_create_request_with_pending_existing_raises_conflict(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test creating a request when a pending request already exists raises ConflictError."""
        user = await user_factory(email="test@example.com", name="Test User")

        # Create existing pending request
        existing_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="existing_token",
            status=AccountLinkRequestStatus.PENDING.value,
        )

        request_data = AccountLinkRequestCreateRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName(existing_request.identity_provider),
            external_id=existing_request.external_id,
            external_email="ms@example.com",
        )

        with pytest.raises(ConflictError, match="Pending account link request already exists"):
            await account_link_request_service.create_request(request_data)

    async def test_create_request_with_approved_existing_allows(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test creating a request when an approved request exists (should be allowed)."""
        user = await user_factory(email="test@example.com", name="Test User")

        # Create existing approved request
        existing_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approved_token",
            status=AccountLinkRequestStatus.APPROVED.value,  # Already approved
        )

        request_data = AccountLinkRequestCreateRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName(existing_request.identity_provider),
            external_id=existing_request.external_id,
            external_email="ms@example.com",
        )

        # Should succeed since previous request is approved, not pending
        result = await account_link_request_service.create_request(request_data)

        assert result is not None

    async def test_approve_request_success(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
        db_session: AsyncSession,
    ):
        """Test approving an account link request successfully."""
        user = await user_factory(email="test@example.com", name="Test User", is_active=True)

        request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email="ms@example.com",
            external_username="ms_user",
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        await account_link_request_service.approve_request(request.request_token, user.id)

        # Verify request was approved
        updated_request = await account_link_request_service.get_request_by_token(request.request_token)

        assert updated_request is not None
        assert updated_request.status == AccountLinkRequestStatus.APPROVED.value

        # Verify identity was created
        identity = await user_identity_service.get_identity_by_provider_and_external_id(
            IdentityProviderName(request.identity_provider), request.external_id
        )

        assert identity is not None
        assert identity.user_id == user.id
        assert identity.external_email == request.external_email
        assert identity.external_username == request.external_username

    async def test_approve_request_not_found_raises_error(
        self, account_link_request_service: AccountLinkRequestService
    ):
        """Test approving a non-existent request raises NotFoundError."""
        with pytest.raises(NotFoundError, match="Account link request not found"):
            await account_link_request_service.approve_request("nonexistent_token", 1)

    async def test_approve_request_already_approved_raises_error(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test approving an already approved request raises ValidationError."""
        user = await user_factory(email="test@example.com", name="Test User", is_active=True)

        approved_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approved_token",
            status=AccountLinkRequestStatus.APPROVED.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        with pytest.raises(ValidationError, match="already approved"):
            await account_link_request_service.approve_request(approved_request.request_token, user.id)

    async def test_approve_request_expired_raises_error(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test approving an expired request raises ValidationError."""
        user = await user_factory(email="test@example.com", name="Test User", is_active=True)

        expired_approved_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="expired_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        with pytest.raises(ValidationError, match="has expired"):
            await account_link_request_service.approve_request(expired_approved_request.request_token, user.id)

    async def test_approve_request_wrong_user_raises_error(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test approving a request with wrong user raises UnauthorizedError."""
        user1 = await user_factory(email="user1@example.com", name="User 1", is_active=True)
        user2 = await user_factory(email="user2@example.com", name="User 2", is_active=True)

        user1_request = await account_link_request_factory(
            user_id=user1.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        with pytest.raises(UnauthorizedError, match="does not match"):
            await account_link_request_service.approve_request(user1_request.request_token, user2.id)

    async def test_approve_request_inactive_user_raises_error(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test approving a request for inactive user raises UnauthorizedError."""
        user = await user_factory(email="test@example.com", name="Test User", is_active=False)

        pending_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        with pytest.raises(UnauthorizedError, match="not found or inactive"):
            await account_link_request_service.approve_request(pending_request.request_token, user.id)

    async def test_approve_request_existing_identity_raises_conflict(
        self,
        account_link_request_service: AccountLinkRequestService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
        account_link_request_factory: Callable[..., Awaitable[AccountLinkRequest]],
    ):
        """Test approving a request when identity already exists raises ConflictError."""
        user = await user_factory(email="test@example.com", name="Test User", is_active=True)

        # Create existing identity
        await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        pending_request = await account_link_request_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        with pytest.raises(ConflictError, match="Identity already exists"):
            await account_link_request_service.approve_request(pending_request.request_token, user.id)

    @patch("app.services.account_link_request.get_account_link_request_expiration_delta")
    async def test_create_request_uses_config_expiration(
        self,
        mock_get_expiration_delta: MagicMock,
        db_session: AsyncSession,
        user_service: UserService,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that create_request uses configured expiration delta."""
        # Mock the config function to return 48 hours as a timedelta
        mock_get_expiration_delta.return_value = timedelta(hours=48)

        # Create service after patching (so __init__ uses the mocked value)
        account_link_request_service = AccountLinkRequestService(session=db_session, user_service=user_service)

        user = await user_factory(email="test@example.com", name="Test User")

        request_data = AccountLinkRequestCreateRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        result = await account_link_request_service.create_request(request_data)

        # Verify expiration is approximately 48 hours from now
        expected_expires = utc_now() + timedelta(hours=48)
        time_diff = abs((result.expires_at - expected_expires).total_seconds())
        assert time_diff < 5  # Allow 5 seconds difference for test execution time

        # Verify the mock was called during service initialization
        mock_get_expiration_delta.assert_called_once()
