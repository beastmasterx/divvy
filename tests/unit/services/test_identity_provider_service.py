"""
Unit tests for IdentityProviderService.
"""

from collections.abc import Awaitable, Callable, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_state_token, is_signed_state_token, verify_state_token
from app.exceptions import UnauthorizedError, ValidationError
from app.models import AccountLinkRequestStatus, IdentityProviderName, User, UserIdentity
from app.repositories import AccountLinkRequestRepository, UserIdentityRepository
from app.schemas import TokenResponse as TokenResponseSchema
from app.services import IdentityProviderService, UserService
from app.services.identity_providers.base import IdentityProviderTokenResponse, IdentityProviderUserInfo
from app.services.identity_providers.registry import IdentityProviderRegistry


@pytest.mark.unit
class TestIdentityProviderService:
    """Test suite for IdentityProviderService."""

    @pytest.fixture(autouse=True)
    def clear_provider_registry(self) -> Iterator[None]:
        """Clear the provider registry before and after each test to ensure test isolation."""
        from app.services.identity_providers.registry import IdentityProviderRegistry

        # Clear before test
        IdentityProviderRegistry.clear()
        yield
        # Clear after test
        IdentityProviderRegistry.clear()

    async def test_handle_oauth_callback_new_user_creates_identity(
        self,
        identity_provider_service: IdentityProviderService,
        user_service: UserService,
        db_session: AsyncSession,
    ):
        """Test that handle_oauth_callback creates user and identity for new users."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
            provider_name=IdentityProviderName.MICROSOFT,
            code="test_code",
            state=None,
            device_info="test_device",
        )

        # Should return TokenResponse for new user
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None
        assert result.refresh_token is not None

        # Verify user was created
        user = await user_service.get_user_by_email("newuser@example.com")
        assert user is not None
        assert user.name == "New User"

        # Verify identity was created
        identity_repo = UserIdentityRepository(db_session)
        identity = await identity_repo.get_identity_by_provider_and_external_id(
            IdentityProviderName.MICROSOFT.value, "ms_123"
        )
        assert identity is not None
        assert identity.user_id == user.id
        assert identity.external_email == "newuser@example.com"
        assert identity.external_username == "New User"

    async def test_handle_oauth_callback_existing_email_creates_link_request(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that handle_oauth_callback creates account link request when email exists."""
        # Create existing user
        user = await user_factory(email="existing@example.com", name="Existing User", is_active=True)

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.GOOGLE.value
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
            provider_name=IdentityProviderName.GOOGLE,
            code="test_code",
            state=None,
            device_info=None,
        )

        # Should return LinkingRequiredResponse
        from app.schemas.authentication import LinkingRequiredResponse

        assert isinstance(result, LinkingRequiredResponse)
        assert result.response_type == "linking_required"
        assert result.requires_linking is True
        assert result.request_token is not None
        assert result.email == "existing@example.com"

        # Verify account link request was created
        request_repo = AccountLinkRequestRepository(db_session)
        request = await request_repo.get_request_by_token(result.request_token)
        assert request is not None
        assert request.status == AccountLinkRequestStatus.PENDING.value
        assert request.user_id == user.id
        assert request.identity_provider == IdentityProviderName.GOOGLE.value
        assert request.external_id == "go_456"
        assert request.external_email == "existing@example.com"
        assert request.external_username == "Google User"

        # Verify identity was NOT created yet (only created when request is approved)
        identity_repo = UserIdentityRepository(db_session)
        identity = await identity_repo.get_identity_by_provider_and_external_id(
            IdentityProviderName.GOOGLE.value, "go_456"
        )
        assert identity is None

    async def test_handle_oauth_callback_existing_identity_returns_tokens(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test that handle_oauth_callback returns tokens for existing linked identity."""
        # Create user and existing identity
        user = await user_factory(email="test@example.com", name="Test User", is_active=True)

        await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_existing",
        )

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
            provider_name=IdentityProviderName.MICROSOFT,
            code="test_code",
            state=None,
            device_info="test_device",
        )

        # Should return TokenResponse for existing identity
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None
        assert result.refresh_token is not None

    async def test_handle_oauth_callback_no_access_token_raises_error(
        self, identity_provider_service: IdentityProviderService
    ):
        """Test that handle_oauth_callback raises UnauthorizedError when no access token received."""
        # Create and register a mock OAuth provider returning no access token
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        mock_provider.exchange_code_for_tokens = AsyncMock(
            return_value=IdentityProviderTokenResponse(access_token="", token_type="Bearer")
        )

        IdentityProviderRegistry.register(mock_provider)

        with pytest.raises(UnauthorizedError, match="No access token received"):
            await identity_provider_service.handle_oauth_callback(
                provider_name=IdentityProviderName.MICROSOFT,
                code="test_code",
                state=None,
                device_info=None,
            )

    async def test_handle_oauth_callback_inactive_user_raises_error(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test that handle_oauth_callback raises UnauthorizedError for inactive user with existing identity."""
        # Create inactive user and existing identity
        user = await user_factory(email="test@example.com", name="Test User", is_active=False)

        await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_inactive",
        )

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
                provider_name=IdentityProviderName.MICROSOFT,
                code="test_code",
                state=None,
                device_info=None,
            )

    async def test_handle_oauth_callback_unregistered_provider_raises_error(
        self, identity_provider_service: IdentityProviderService, db_session: AsyncSession
    ):
        """Test that handle_oauth_callback raises ValueError for unregistered provider."""
        # Don't register any provider - registry should be empty due to clear_provider_registry fixture

        with pytest.raises(ValueError, match="Unknown identity provider"):
            await identity_provider_service.handle_oauth_callback(
                provider_name=IdentityProviderName.MICROSOFT,  # Use valid enum, but provider not registered
                code="test_code",
                state=None,
                device_info=None,
            )

    async def test_handle_oauth_callback_authenticated_link_with_signed_state_token(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that handle_oauth_callback directly links account when signed state token with operation=link is provided."""
        # Create an authenticated user
        user = await user_factory(email="user@example.com", name="Test User", is_active=True)

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
            provider_name=IdentityProviderName.MICROSOFT,
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
        identity = await identity_repo.get_identity_by_provider_and_external_id(
            IdentityProviderName.MICROSOFT.value, "ms_new_identity"
        )
        assert identity is not None
        assert identity.user_id == user.id
        assert identity.external_email == "user@example.com"

    async def test_handle_oauth_callback_authenticated_link_email_mismatch(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that handle_oauth_callback allows linking even if provider email differs from account email."""
        # Create an authenticated user
        user = await user_factory(email="user@example.com", name="Test User", is_active=True)

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider with different email
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
            provider_name=IdentityProviderName.MICROSOFT,
            code="test_code",
            state=state_token,
            device_info="test_device",
        )

        # Should still return TokenResponse (email mismatch is logged but allowed)
        assert isinstance(result, TokenResponseSchema)
        assert result.access_token is not None

        # Verify identity was created with provider email
        identity_repo = UserIdentityRepository(db_session)
        identity = await identity_repo.get_identity_by_provider_and_external_id(
            IdentityProviderName.MICROSOFT.value, "ms_new_identity"
        )
        assert identity is not None
        assert identity.external_email == "different@microsoft.com"
        assert identity.user_id == user.id

    async def test_handle_oauth_callback_authenticated_link_invalid_state_token(
        self, identity_provider_service: IdentityProviderService, db_session: AsyncSession
    ):
        """Test that handle_oauth_callback raises ValidationError for invalid signed state token."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth")
        IdentityProviderRegistry.register(mock_provider)

        # Use an invalid signed state token (expired or malformed)
        invalid_state_token = "invalid.jwt.token"

        with pytest.raises(ValidationError, match="Invalid or expired state token"):
            await identity_provider_service.handle_oauth_callback(
                provider_name=IdentityProviderName.MICROSOFT,
                code="test_code",
                state=invalid_state_token,
                device_info=None,
            )

    async def test_handle_oauth_callback_authenticated_link_user_id_mismatch(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that handle_oauth_callback raises ValidationError when user_id in state token doesn't match retrieved user."""
        # Create a user (not used but kept for clarity)
        await user_factory(email="user@example.com", name="Test User", is_active=True)

        # Create signed state token with different user_id (simulating tampering)
        # This shouldn't happen in practice, but we test the validation
        state_token = create_state_token(operation="link", user_id=99999)  # Non-existent user ID

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
                provider_name=IdentityProviderName.MICROSOFT,
                code="test_code",
                state=state_token,
                device_info=None,
            )

    async def test_handle_oauth_callback_authenticated_link_inactive_user(
        self,
        identity_provider_service: IdentityProviderService,
        db_session: AsyncSession,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test that handle_oauth_callback raises UnauthorizedError for inactive user in authenticated link flow."""
        # Create an inactive user
        user = await user_factory(email="user@example.com", name="Test User", is_active=False)

        # Create signed state token for authenticated link
        state_token = create_state_token(operation="link", user_id=user.id)

        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
                provider_name=IdentityProviderName.MICROSOFT,
                code="test_code",
                state=state_token,
                device_info=None,
            )

    async def test_handle_oauth_callback_frontend_generated_state_passed_through(
        self, identity_provider_service: IdentityProviderService
    ):
        """Test that handle_oauth_callback passes through frontend-generated state without verification."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
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
            provider_name=IdentityProviderName.MICROSOFT,
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
        mock_provider.name = IdentityProviderName.MICROSOFT.value
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth?state=test")
        IdentityProviderRegistry.register(mock_provider)

        url = identity_provider_service.get_authorization_url(IdentityProviderName.MICROSOFT, state="test")
        assert url == "https://example.com/auth?state=test"
        mock_provider.get_authorization_url.assert_called_once_with("test")

    def test_get_authorization_url_unregistered_provider_raises_error(
        self, identity_provider_service: IdentityProviderService, db_session: AsyncSession
    ):
        """Test that get_authorization_url raises ValueError for unregistered provider."""
        # Don't register any provider

        with pytest.raises(ValueError, match="Unknown identity provider"):
            identity_provider_service.get_authorization_url(IdentityProviderName.MICROSOFT, state=None)

    def test_get_link_authorization_url_registered_provider(self, identity_provider_service: IdentityProviderService):
        """Test that get_link_authorization_url creates signed state token and returns URL."""
        # Create and register a mock OAuth provider
        mock_provider = MagicMock()
        mock_provider.name = IdentityProviderName.MICROSOFT.value
        mock_provider.get_authorization_url = MagicMock(return_value="https://example.com/auth?state=token")
        IdentityProviderRegistry.register(mock_provider)

        user_id = 123
        url = identity_provider_service.get_link_authorization_url(IdentityProviderName.MICROSOFT, user_id)

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
            identity_provider_service.get_link_authorization_url(IdentityProviderName.MICROSOFT, user_id=123)
