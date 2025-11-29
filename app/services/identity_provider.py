"""
Service for managing identity provider OAuth flows and account linking.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import _
from app.core.identity_providers import IdentityProviderRegistry
from app.core.security import StateTokenPayload, create_state_token, is_signed_state_token, validate_state_token
from app.exceptions import UnauthorizedError
from app.models import IdentityProviderName
from app.schemas import (
    AccountLinkRequestCreateRequest,
    LinkingRequiredResponse,
    TokenResponse,
    UserIdentityRequest,
    UserRequest,
)
from app.services.account_link_request import AccountLinkRequestService
from app.services.authentication import AuthenticationService
from app.services.user import UserService
from app.services.user_identity import UserIdentityService

logger = logging.getLogger(__name__)


class IdentityProviderService:
    """Service for managing identity provider OAuth flows and account linking."""

    # Account link request expiration: 24 hours
    LINK_REQUEST_EXPIRATION_HOURS = 24

    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
        user_identity_service: UserIdentityService,
        account_link_request_service: AccountLinkRequestService,
        authentication_service: AuthenticationService,
    ):
        """
        Initialize IdentityProviderService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for user operations
            authentication_service: Authentication service for token generation
        """
        self._session = session
        self._user_service = user_service
        self._authentication_service = authentication_service
        self._user_identity_service = user_identity_service
        self._account_link_request_service = account_link_request_service

    def get_authorization_url(self, provider_name: IdentityProviderName, state: str | None = None) -> str:
        """Get OAuth authorization URL for a provider.

        Args:
            provider_name: Name of the identity provider (e.g., 'microsoft', 'google')
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for redirecting user to provider login

        Raises:
            ValueError: If provider is not registered
        """
        provider = IdentityProviderRegistry.get_provider(provider_name.value)
        return provider.get_authorization_url(state)

    def get_link_authorization_url(self, provider_name: IdentityProviderName, user_id: int) -> str:
        """
        Get OAuth authorization URL for authenticated account linking.

        Creates a signed state token with the user's ID and operation context,
        then returns the authorization URL for redirecting to the provider.

        Args:
            provider_name: Name of the identity provider (e.g., 'microsoft', 'google')
            user_id: ID of the authenticated user requesting the link

        Returns:
            Authorization URL with signed state token for account linking

        Raises:
            ValueError: If provider is not registered
        """

        # Create signed state token for authenticated account linking
        state_token = create_state_token(operation="link", user_id=user_id)
        return self.get_authorization_url(provider_name, state_token)

    async def handle_oauth_callback(
        self,
        provider_name: IdentityProviderName,
        code: str,
        state: str | None = None,
        device_info: str | None = None,
    ) -> TokenResponse | LinkingRequiredResponse:
        """
        Handle OAuth callback: exchange code for tokens and create/link account.

        Flow:
        1. Validate state parameter (if provided) - see State Parameter Handling below
        2. Exchange authorization code for access token
        3. Get user info from provider
        4. Check if identity already exists (by provider + external_id)
           - If exists: return tokens for existing user
        5. If identity doesn't exist:
           - If state indicates authenticated link operation: directly link account
           - Otherwise, check if email exists in our system
             - If email exists: create account link request (return link request info)
             - If email doesn't exist: create new user + identity (return tokens)

        State Parameter Handling:
        ========================
        The state parameter can be one of two types:

        1. Frontend-Generated State (Login Flow):
           - Created by frontend: random string (e.g., crypto.randomUUID())
           - Purpose: CSRF protection for login flows
           - Verification: Frontend verifies state_sent === state_received
           - Backend behavior: Passes through without verification
           - Example: "550e8400-e29b-41d4-a716-446655440000"

        2. Backend-Generated Signed State Token (Link Flow):
           - Created by backend: signed JWT token via create_state_token()
           - Purpose: Encodes operation context (link/login) and user identification
           - Verification: Backend verifies signature, expiration, and extracts context
           - Backend behavior: Verifies token and uses payload.operation and payload.user_id
           - Format: JWT with 3 parts separated by dots (header.payload.signature)
           - Example: "eyJhbGciOiJIUzI1NiJ9.eyJvcGVyYXRpb24iOiJsaW5rIiwidXNlcl9pZCI6MTIzfQ.signature"

        State Token Payload Structure (for signed tokens):
        - operation: "link" or "login"
        - user_id: User ID (only present for "link" operation)
        - nonce: Cryptographically secure nonce for one-time use tracking
        - exp: Token expiration timestamp
        - iat: Token issued at timestamp

        Args:
            provider_name: Name of the identity provider
            code: Authorization code from OAuth callback
            state: Optional state parameter from OAuth callback
                - Frontend-generated random string (login flow): passed through
                - Backend-generated signed JWT token (link flow): verified and used for context
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            TokenResponse if user is authenticated, or LinkingRequiredResponse if linking required

        Raises:
            ValueError: If provider is not registered
            UnauthorizedError: If OAuth flow fails (includes InvalidStateTokenError for invalid/expired state tokens)
        """
        provider = IdentityProviderRegistry.get_provider(provider_name.value)

        # State parameter handling
        state_payload: StateTokenPayload | None = None
        # Check if state is a backend-generated signed JWT token
        if state and is_signed_state_token(state):
            state_payload = validate_state_token(state)

        # Exchange code for tokens
        tokens = await provider.exchange_code_for_tokens(code)
        if not tokens.access_token:
            raise UnauthorizedError(_("No access token received from provider"))

        # Get user info from provider
        user_info = await provider.get_user_info(tokens.access_token)
        external_id = user_info.external_id
        email = user_info.email
        name = user_info.name or email.split("@")[0]  # Use email prefix as fallback name

        # Check if identity already exists
        existing_identity = await self._user_identity_service.get_identity_by_provider_and_external_id(
            provider_name, external_id
        )

        if existing_identity:
            # Identity exists, user is already linked - return tokens
            user = await self._user_service.get_user_by_id(existing_identity.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError(_("User account not found or inactive"))

            return await self._authentication_service.issues_tokens(user.email, device_info)

        # Identity doesn't exist - check if this is an authenticated link operation
        if state_payload and state_payload.operation == "link" and state_payload.user_id:
            # Authenticated user initiated link - directly link the account
            user = await self._user_service.get_user_by_id(state_payload.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError(_("User account not found or inactive"))

            # Create and link the identity
            logger.info(f"Authenticated link: linking provider {provider_name.value} identity to user {user.id}")
            user_identity_request = UserIdentityRequest(
                user_id=user.id,
                identity_provider=provider_name,
                external_id=external_id,
                external_email=email,
                external_username=name,
            )
            await self._user_identity_service.create_identity(user_identity_request)

            return await self._authentication_service.issues_tokens(user.email, device_info)

        # Not an authenticated link - check if email exists
        existing_user = await self._user_service.get_user_by_email(email) if email else None

        if existing_user:
            # Email exists - create account link request (identity will be created on approval)
            logger.info(f"Email {email} exists, creating account link request for provider {provider_name.value}")

            # Create account link request with provider information
            account_link_request_request = AccountLinkRequestCreateRequest(
                user_id=existing_user.id,
                identity_provider=provider_name,
                external_id=external_id,
                external_email=email,
                external_username=name,
            )
            link_request = await self._account_link_request_service.create_request(account_link_request_request)

            # TODO: Send email notification (placeholder: log for now)

            logger.info(f"Account link request created: {link_request.request_token}")

            return LinkingRequiredResponse(
                response_type="linking_required",
                requires_linking=True,
                request_token=link_request.request_token,
                email=email,
                message="An account with this email already exists. Please log in to link this account.",
            )

        # Email doesn't exist - create new user and identity
        logger.info(f"Creating new user for provider {provider_name.value}, email: {email}")

        user_request = UserRequest(
            email=email,
            name=name,
            is_active=True,
            avatar=None,
        )
        user = await self._user_service.create_user(user_request)

        user_identity_request = UserIdentityRequest(
            user_id=user.id,
            identity_provider=provider_name,
            external_id=external_id,
            external_email=email,
            external_username=name,
        )
        await self._user_identity_service.create_identity(user_identity_request)

        return await self._authentication_service.issues_tokens(user.email, device_info)
