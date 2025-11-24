"""
Unit tests for IdentityProviderService.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from app.api.schemas import TokenResponse as TokenResponseSchema
from app.core.security import create_state_token, hash_password, is_signed_state_token, verify_state_token
from app.exceptions import UnauthorizedError, ValidationError
from app.models import AccountLinkRequestStatus
from app.repositories import AccountLinkRequestRepository, UserIdentityRepository, UserRepository
from app.services import AuthService, IdentityProviderService, UserService
from app.services.identity_providers.base import IdentityProviderTokenResponse, IdentityProviderUserInfo
from app.services.identity_providers.registry import IdentityProviderRegistry
from tests.fixtures.factories import (
    create_test_account_link_request,
    create_test_user,
    create_test_user_identity,
)


@pytest.mark.unit
class TestIdentityProviderService:
    """Test suite for IdentityProviderService."""

    @pytest.fixture
    def identity_provider_service(self, db_session: Session) -> IdentityProviderService:
        """Create an IdentityProviderService instance with dependencies."""
        user_service = UserService(db_session)
        auth_service = AuthService(session=db_session, user_service=user_service)
        return IdentityProviderService(
            session=db_session,
            user_service=user_service,
            auth_service=auth_service,
        )

    @pytest.fixture(autouse=True)
    def clear_provider_registry(self):
        """Clear the provider registry before and after each test to ensure test isolation."""
        from app.services.identity_providers.registry import IdentityProviderRegistry

        # Clear before test
        IdentityProviderRegistry.clear()
        yield
        # Clear after test
        IdentityProviderRegistry.clear()

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_new_user_creates_identity(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback creates user and identity for new users."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_123",
                email="newuser@example.com",
                name="New User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="microsoft",
            code="test_code",
            state=None,
            device_info="test_device",
        )

        # Should return TokenResponse for new user
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None
        assert result.refresh_token is not None

        # Verify user was created
        user_repo = UserRepository(db_session)
        user = user_repo.get_user_by_email("newuser@example.com")
        assert user is not None
        assert user.name == "New User"

        # Verify identity was created
        identity_repo = UserIdentityRepository(db_session)
        identity = identity_repo.get_identity_by_provider_and_external_id("microsoft", "ms_123")
        assert identity is not None
        assert identity.user_id == user.id
        assert identity.external_email == "newuser@example.com"
        assert identity.external_username == "New User"

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_existing_email_creates_link_request(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback creates account link request when email exists."""
        # Create existing user
        user = create_test_user(email="existing@example.com", name="Existing User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "google"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="go_456",
                email="existing@example.com",
                name="Google User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="google",
            code="test_code",
            state=None,
            device_info=None,
        )

        # Should return LinkingRequiredResponse
        from app.api.schemas.auth import LinkingRequiredResponse

        assert isinstance(result, LinkingRequiredResponse)
        assert result.response_type == "linking_required"
        assert result.requires_linking is True
        assert result.request_token is not None
        assert result.email == "existing@example.com"

        # Verify account link request was created
        request_repo = AccountLinkRequestRepository(db_session)
        request = request_repo.get_request_by_token(result.request_token)
        assert request is not None
        assert request.status == AccountLinkRequestStatus.PENDING.value

        # Verify identity was created
        identity_repo = UserIdentityRepository(db_session)
        identity = identity_repo.get_identity_by_provider_and_external_id("google", "go_456")
        assert identity is not None
        assert identity.user_id == user.id

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_existing_identity_returns_tokens(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback returns tokens for existing linked identity."""
        # Create user and existing identity
        user = create_test_user(email="test@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ms_existing",
        )
        db_session.add(identity)
        db_session.commit()

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_existing",
                email="test@example.com",
                name="Test User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="microsoft",
            code="test_code",
            state=None,
            device_info="test_device",
        )

        # Should return TokenResponse for existing identity
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None
        assert result.refresh_token is not None

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_no_access_token_raises_error(
        self, identity_provider_service: IdentityProviderService
    ):
        """Test that handle_oauth_callback raises UnauthorizedError when no access token received."""
        # Create and register a mock OAuth provider returning no access token
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="", token_type="Bearer")
        )

        IdentityProviderRegistry.register(mock_provider)

        with pytest.raises(UnauthorizedError, match="No access token received"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="microsoft",
                code="test_code",
                state=None,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_inactive_user_raises_error(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback raises UnauthorizedError for inactive user with existing identity."""
        # Create inactive user and existing identity
        user = create_test_user(email="test@example.com", name="Test User", is_active=False)
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ms_inactive",
        )
        db_session.add(identity)
        db_session.commit()

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_inactive",
                email="test@example.com",
                name="Test User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        with pytest.raises(UnauthorizedError, match="User account not found or inactive"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="microsoft",
                code="test_code",
                state=None,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_unregistered_provider_raises_error(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback raises ValueError for unregistered provider."""
        # Don't register any provider - registry should be empty due to clear_provider_registry fixture

        with pytest.raises(ValueError, match="Unknown identity provider"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="nonexistent",
                code="test_code",
                state=None,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_authenticated_link_with_signed_state_token(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback directly links account when signed state token with operation=link is provided."""
        # Create an authenticated user
        user = create_test_user(email="user@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_new_identity",
                email="user@example.com",  # Same email as user
                name="Microsoft User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="microsoft",
            code="test_code",
            state=state_token,
            device_info="test_device",
        )

        # Should return TokenResponse (directly linked, no password required)
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None
        assert result.refresh_token is not None

        # Verify identity was created and linked
        identity_repo = UserIdentityRepository(db_session)
        identity = identity_repo.get_identity_by_provider_and_external_id("microsoft", "ms_new_identity")
        assert identity is not None
        assert identity.user_id == user.id
        assert identity.external_email == "user@example.com"

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_authenticated_link_email_mismatch(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback allows linking even if provider email differs from account email."""
        # Create an authenticated user
        user = create_test_user(email="user@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider with different email
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_new_identity",
                email="different@microsoft.com",  # Different email from account
                name="Microsoft User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="microsoft",
            code="test_code",
            state=state_token,
            device_info="test_device",
        )

        # Should still return TokenResponse (email mismatch is logged but allowed)
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None

        # Verify identity was created with provider email
        identity_repo = UserIdentityRepository(db_session)
        identity = identity_repo.get_identity_by_provider_and_external_id("microsoft", "ms_new_identity")
        assert identity is not None
        assert identity.external_email == "different@microsoft.com"
        assert identity.user_id == user.id

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_authenticated_link_invalid_state_token(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback raises ValidationError for invalid signed state token."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        IdentityProviderRegistry.register(mock_provider)

        # Use an invalid signed state token (expired or malformed)
        invalid_state_token = "invalid.jwt.token"

        with pytest.raises(ValidationError, match="Invalid or expired state token"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="microsoft",
                code="test_code",
                state=invalid_state_token,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_authenticated_link_user_id_mismatch(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback raises ValidationError when user_id in state token doesn't match retrieved user."""
        # Create a user
        user = create_test_user(email="user@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create signed state token with different user_id (simulating tampering)
        # This shouldn't happen in practice, but we test the validation
        state_token = create_state_token(operation="link", user_id=99999)  # Non-existent user ID

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_new_identity",
                email="user@example.com",
                name="Microsoft User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        # Should raise UnauthorizedError when user is not found (user_id=99999 doesn't exist)
        with pytest.raises(UnauthorizedError, match="User account not found or inactive"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="microsoft",
                code="test_code",
                state=state_token,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_authenticated_link_inactive_user(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that handle_oauth_callback raises UnauthorizedError for inactive user in authenticated link flow."""
        # Create an inactive user
        user = create_test_user(email="user@example.com", name="Test User", is_active=False)
        db_session.add(user)
        db_session.commit()

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_new_identity",
                email="user@example.com",
                name="Microsoft User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        with pytest.raises(UnauthorizedError, match="User account not found or inactive"):
            await identity_provider_service.handle_oauth_callback(
                provider_name="microsoft",
                code="test_code",
                state=state_token,
                device_info=None,
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_frontend_generated_state_passed_through(
        self, identity_provider_service: IdentityProviderService
    ):
        """Test that handle_oauth_callback passes through frontend-generated state without verification."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="test_access_token", token_type="Bearer")
        )
        mock_provider.get_user_info = AsyncMock(
            return_value=IdentityProviderUserInfo(
                external_id="ms_123",
                email="newuser@example.com",
                name="New User",
            )
        )

        IdentityProviderRegistry.register(mock_provider)

        # Use frontend-generated state (random string, not JWT)
        frontend_state = "550e8400-e29b-41d4-a716-446655440000"

        result = await identity_provider_service.handle_oauth_callback(
            provider_name="microsoft",
            code="test_code",
            state=frontend_state,
            device_info="test_device",
        )

        # Should work normally (frontend will verify the state)
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None

    def test_get_authorization_url_registered_provider(self, identity_provider_service: IdentityProviderService):
        """Test that get_authorization_url works with registered provider."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth?state=test")
        IdentityProviderRegistry.register(mock_provider)

        url = identity_provider_service.get_authorization_url("microsoft", state="test")
        assert url == "https://example.com/auth?state=test"
        mock_provider.get_authorization_url.assert_called_once_with("test")

    def test_get_authorization_url_unregistered_provider_raises_error(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test that get_authorization_url raises ValueError for unregistered provider."""
        # Don't register any provider

        with pytest.raises(ValueError, match="Unknown identity provider"):
            identity_provider_service.get_authorization_url("nonexistent", state=None)

    def test_get_link_authorization_url_registered_provider(self, identity_provider_service: IdentityProviderService):
        """Test that get_link_authorization_url creates signed state token and returns URL."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = "microsoft"
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth?state=token")
        IdentityProviderRegistry.register(mock_provider)

        user_id = 123
        url = identity_provider_service.get_link_authorization_url("microsoft", user_id)

        # Verify URL was returned
        assert url == "https://example.com/auth?state=token"

        # Verify provider was called with a signed state token
        mock_provider.get_authorization_url.assert_called_once()
        state_arg = mock_provider.get_authorization_url.call_args[0][0]
        assert state_arg is not None
        assert is_signed_state_token(state_arg)

        # Verify the state token contains correct user_id
        from app.core.security.oauth import StateTokenPayload

        payload: StateTokenPayload = verify_state_token(state_arg)
        assert payload.operation == "link"
        assert payload.user_id == user_id

    def test_get_link_authorization_url_unregistered_provider_raises_error(
        self, identity_provider_service: IdentityProviderService
    ):
        """Test that get_link_authorization_url raises ValueError for unregistered provider."""
        # Don't register any provider

        with pytest.raises(ValueError, match="Unknown identity provider"):
            identity_provider_service.get_link_authorization_url("nonexistent", user_id=123)

    def test_approve_account_link_request_with_password(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request with valid password."""
        # Create a user with password
        password = "securepass123"
        user = create_test_user(
            email="test@example.com", name="Test User", password=hash_password(password), is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Approve the request
        token_response = identity_provider_service.approve_account_link_request(
            request_token="approve_token", password=password, user_id=None
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "Bearer"

        # Verify request was updated
        from app.repositories import AccountLinkRequestRepository

        repo = AccountLinkRequestRepository(db_session)
        updated_request = repo.get_request_by_token("approve_token")
        assert updated_request is not None
        assert updated_request.status == AccountLinkRequestStatus.APPROVED.value
        assert updated_request.verified_at is not None

    def test_approve_account_link_request_with_authenticated_user(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request with authenticated user."""
        # Create a user
        user = create_test_user(email="test@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Approve the request with authenticated user
        token_response = identity_provider_service.approve_account_link_request(
            request_token="approve_token", password=None, user_id=user.id
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

        # Verify request was updated
        from app.repositories import AccountLinkRequestRepository

        repo = AccountLinkRequestRepository(db_session)
        updated_request = repo.get_request_by_token("approve_token")
        assert updated_request is not None
        assert updated_request.status == AccountLinkRequestStatus.APPROVED.value

    def test_approve_account_link_request_invalid_password(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request with invalid password raises UnauthorizedError."""
        # Create a user with password
        password = "securepass123"
        user = create_test_user(
            email="test@example.com", name="Test User", password=hash_password(password), is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve with wrong password
        with pytest.raises(UnauthorizedError):
            identity_provider_service.approve_account_link_request(
                request_token="approve_token", password="wrongpassword", user_id=None
            )

    def test_approve_account_link_request_user_no_password(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request for user without password raises UnauthorizedError."""
        # Create a user without password
        user = create_test_user(email="test@example.com", password=None, name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve with password when user has no password set
        with pytest.raises(UnauthorizedError, match="User has no password set"):
            identity_provider_service.approve_account_link_request(
                request_token="approve_token", password="pass123", user_id=None
            )

    def test_approve_account_link_request_user_inactive(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request for inactive user raises UnauthorizedError."""
        # Create an inactive user
        password = "securepass123"
        user = create_test_user(
            email="test@example.com", name="Test User", password=hash_password(password), is_active=False
        )
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve for inactive user
        with pytest.raises(UnauthorizedError, match="User account not found or inactive"):
            identity_provider_service.approve_account_link_request(
                request_token="approve_token", password=password, user_id=None
            )

    def test_approve_account_link_request_expired(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an expired account link request raises ValidationError."""
        # Create a user
        password = "securepass123"
        user = create_test_user(
            email="test@example.com", name="Test User", password=hash_password(password), is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Create an identity and expired request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="expired_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve expired request
        with pytest.raises(ValidationError, match="Account link request has expired"):
            identity_provider_service.approve_account_link_request(
                request_token="expired_token", password=password, user_id=None
            )

        # Verify status was updated to expired
        from app.repositories import AccountLinkRequestRepository

        repo = AccountLinkRequestRepository(db_session)
        updated_request = repo.get_request_by_token("expired_token")
        assert updated_request is not None
        assert updated_request.status == AccountLinkRequestStatus.EXPIRED.value

    def test_approve_account_link_request_already_processed(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an already processed account link request raises ValidationError."""
        # Create a user
        password = "securepass123"
        user = create_test_user(
            email="test@example.com", name="Test User", password=hash_password(password), is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Create an identity and approved request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approved_token",
            status=AccountLinkRequestStatus.APPROVED.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve already approved request
        with pytest.raises(ValidationError, match="cannot verify"):
            identity_provider_service.approve_account_link_request(
                request_token="approved_token", password=password, user_id=None
            )

    def test_approve_account_link_request_wrong_authenticated_user(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request with wrong authenticated user raises UnauthorizedError."""
        # Create two users
        user1 = create_test_user(email="user1@example.com", name="User 1", is_active=True)
        user2 = create_test_user(email="user2@example.com", name="User 2", is_active=True)
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Create an identity for user1 and request
        identity = create_test_user_identity(user_id=user1.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve with wrong user
        with pytest.raises(UnauthorizedError, match="Authenticated user does not match"):
            identity_provider_service.approve_account_link_request(
                request_token="approve_token", password=None, user_id=user2.id
            )

    def test_approve_account_link_request_not_found(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving a non-existent account link request raises NotFoundError."""
        from app.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="Account link request not found"):
            identity_provider_service.approve_account_link_request(
                request_token="nonexistent_token", password="pass123", user_id=None
            )

    def test_approve_account_link_request_no_password_when_not_authenticated(
        self, identity_provider_service: IdentityProviderService, db_session: Session
    ):
        """Test approving an account link request without password when not authenticated raises ValidationError."""
        # Create a user
        user = create_test_user(email="test@example.com", name="Test User", is_active=True)
        db_session.add(user)
        db_session.commit()

        # Create an identity and request
        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ms_123")
        db_session.add(identity)
        db_session.commit()

        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approve_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db_session.add(request)
        db_session.commit()

        # Try to approve without password and without authenticated user
        with pytest.raises(ValidationError, match="Password is required when not authenticated"):
            identity_provider_service.approve_account_link_request(
                request_token="approve_token", password=None, user_id=None
            )
