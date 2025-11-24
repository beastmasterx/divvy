"""
Service for managing identity provider OAuth flows and account linking.
"""

import logging
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LinkingRequiredResponse, TokenResponse, UserRequest
from app.core.datetime import utc, utc_now
from app.core.security import check_password, is_signed_state_token, verify_state_token
from app.core.security.oauth import StateTokenPayload
from app.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.models import AccountLinkRequest, AccountLinkRequestStatus, User, UserIdentity
from app.repositories import AccountLinkRequestRepository, UserIdentityRepository, UserRepository
from app.services.auth import AuthService
from app.services.identity_providers.registry import IdentityProviderRegistry
from app.services.user import UserService

logger = logging.getLogger(__name__)


class IdentityProviderService:
    """Service for managing identity provider OAuth flows and account linking."""

    # Account link request expiration: 24 hours
    LINK_REQUEST_EXPIRATION_HOURS = 24

    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
        auth_service: AuthService,
    ):
        """
        Initialize IdentityProviderService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for user operations
            auth_service: Auth service for token generation
        """
        self._session = session
        self._user_service = user_service
        self._auth_service = auth_service
        self._user_identity_repository = UserIdentityRepository(session)
        self._account_link_request_repository = AccountLinkRequestRepository(session)
        self._user_repository = UserRepository(session)

    def get_authorization_url(self, provider_name: str, state: str | None = None) -> str:
        """Get OAuth authorization URL for a provider.

        Args:
            provider_name: Name of the identity provider (e.g., 'microsoft', 'google')
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for redirecting user to provider login

        Raises:
            ValueError: If provider is not registered
        """
        provider = IdentityProviderRegistry.get_provider(provider_name)
        return provider.get_authorization_url(state)

    def get_link_authorization_url(self, provider_name: str, user_id: int) -> str:
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
        from app.core.security import create_state_token

        # Create signed state token for authenticated account linking
        state_token = create_state_token(operation="link", user_id=user_id)
        return self.get_authorization_url(provider_name, state_token)

    async def handle_oauth_callback(
        self,
        provider_name: str,
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
            ValueError: If provider is not registered, or if signed state token is invalid/expired
            UnauthorizedError: If OAuth flow fails
            ValidationError: If signed state token validation fails
        """
        provider = IdentityProviderRegistry.get_provider(provider_name)

        # State parameter handling
        state_payload: StateTokenPayload | None = None
        if state:
            # Check if state is a backend-generated signed JWT token
            if is_signed_state_token(state):
                # Backend-generated signed token - verify it
                try:
                    state_payload = verify_state_token(state)
                    logger.debug(
                        f"Verified signed state token: operation={state_payload.operation}, "
                        f"user_id={state_payload.user_id}"
                    )
                except ValueError as e:
                    raise ValidationError(f"Invalid or expired state token: {e}") from e
            else:
                # Frontend-generated random string - pass through (frontend will verify)
                logger.debug(f"Frontend-generated state received: {state} (frontend will verify)")

        # Exchange code for tokens
        tokens = await provider.exchange_code_for_tokens(code)
        if not tokens.access_token:
            raise UnauthorizedError("No access token received from provider")

        # Get user info from provider
        user_info = await provider.get_user_info(tokens.access_token)
        external_id = user_info.external_id
        email = user_info.email
        name = user_info.name

        # Check if identity already exists
        existing_identity = await self._user_identity_repository.get_identity_by_provider_and_external_id(
            provider_name, external_id
        )

        if existing_identity:
            # Identity exists, user is already linked - return tokens
            user = await self._user_repository.get_user_by_id(existing_identity.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError("User account not found or inactive")

            return await self._auth_service.generate_tokens(user.id, device_info)

        # Identity doesn't exist - check if this is an authenticated link operation
        if state_payload and state_payload.operation == "link" and state_payload.user_id:
            # Authenticated user initiated link - directly link the account
            user = await self._user_repository.get_user_by_id(state_payload.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError("User account not found or inactive")

            # Verify user_id matches (security check)
            if user.id != state_payload.user_id:
                raise ValidationError(
                    f"User ID mismatch: state token user_id={state_payload.user_id}, " f"retrieved user_id={user.id}"
                )

            # Verify the email matches (security check - warn but allow if different)
            # Provider email might differ from account email (e.g., different email on Microsoft account)
            if email and user.email != email:
                logger.warning(
                    f"Email mismatch during authenticated link: "
                    f"user_id={state_payload.user_id}, account_email={user.email}, provider_email={email}"
                )
                # Still allow linking but log the mismatch (provider email might differ)

            # Create and link the identity
            logger.info(f"Authenticated link: linking provider {provider_name} identity to user {user.id}")
            await self._create_user_identity(
                user_id=user.id,
                provider_name=provider_name,
                external_id=external_id,
                external_email=email,
                external_username=name,
            )

            return await self._auth_service.generate_tokens(user.id, device_info)

        # Not an authenticated link - check if email exists
        existing_user = await self._user_repository.get_user_by_email(email) if email else None

        if existing_user:
            # Email exists - create account link request (requires password verification)
            logger.info(f"Email {email} exists, creating account link request for provider {provider_name}")
            link_request = await self._create_account_link_request(
                provider_name=provider_name,
                external_id=external_id,
                external_email=email,
                external_username=name,
                user_id=existing_user.id,
            )
            # TODO: Send email notification (placeholder: log for now)
            logger.info(f"Account link request created: {link_request.request_token}")
            return LinkingRequiredResponse(
                response_type="linking_required",
                requires_linking=True,
                request_token=link_request.request_token,
                email=email,
                message="An account with this email already exists. Please verify your password to link this account.",
            )

        # Email doesn't exist - create new user and identity
        logger.info(f"Creating new user for provider {provider_name}, email: {email}")
        user = await self._create_user_from_provider(email, name)
        await self._create_user_identity(
            user_id=user.id,
            provider_name=provider_name,
            external_id=external_id,
            external_email=email,
            external_username=name,
        )

        return await self._auth_service.generate_tokens(user.id, device_info)

    async def approve_account_link_request(
        self, request_token: str, password: str | None = None, user_id: int | None = None
    ) -> TokenResponse:
        """
        Approve an account link request by verifying password or authenticated user and linking the identity.

        Args:
            request_token: Account link request token
            password: User's password for verification (required if not authenticated)
            user_id: ID of authenticated user (if user is logged in)

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            NotFoundError: If request not found
            ValidationError: If request is expired or already processed, or if neither password nor authenticated_user_id provided
            UnauthorizedError: If password is incorrect or authenticated user doesn't match request
        """
        request = await self._verify_account_link_request(request_token, password, user_id)

        # Link the identity to the user
        identity = request.user_identity
        identity.user_id = request.user_identity.user_id  # Already linked, but ensure consistency

        # Update request status
        request.status = AccountLinkRequestStatus.APPROVED.value
        request.verified_at = utc_now()
        await self._account_link_request_repository.update_request(request)

        # Get user and return tokens
        user = await self._user_repository.get_user_by_id(identity.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User account not found or inactive")

        logger.info(f"Account link approved: identity {identity.id} linked to user {user.id}")
        return await self._auth_service.generate_tokens(user.id, None)

    async def _verify_account_link_request(
        self, request_token: str, password: str | None = None, user_id: int | None = None
    ) -> AccountLinkRequest:
        """
        Verify an account link request with password or authenticated user.

        Args:
            request_token: Account link request token
            password: User's password for verification (required if not authenticated)
            user_id: ID of authenticated user (if user is logged in)

        Returns:
            AccountLinkRequest object if verification succeeds

        Raises:
            NotFoundError: If request not found
            ValidationError: If request is expired or already processed, or if neither password nor authenticated_user_id provided
            UnauthorizedError: If password is incorrect or authenticated user doesn't match request
        """
        request = await self._account_link_request_repository.get_request_by_token(request_token)
        if not request:
            raise NotFoundError("Account link request not found")

        if request.status != AccountLinkRequestStatus.PENDING.value:
            raise ValidationError(f"Account link request is {request.status}, cannot verify")

        if utc(request.expires_at) < utc_now():
            request.status = AccountLinkRequestStatus.EXPIRED.value
            await self._account_link_request_repository.update_request(request)
            raise ValidationError("Account link request has expired")

        user = await self._user_repository.get_user_by_id(request.user_identity.user_id)
        if not user:
            raise NotFoundError("User associated with link request not found")

        # If user is authenticated, verify they match the request
        if user_id is not None:
            if user_id != user.id:
                raise UnauthorizedError("Authenticated user does not match account link request")
            # User is authenticated and matches - no password needed
            return request

        # If not authenticated, password is required
        if not password:
            raise ValidationError("Password is required when not authenticated")

        if not user.password:
            raise UnauthorizedError("User has no password set")

        if not check_password(password, user.password):
            raise UnauthorizedError("Incorrect password")

        return request

    async def _create_user_from_provider(self, email: str, name: str | None) -> User:
        """Create a new user from provider information.

        Args:
            email: User's email address
            name: User's display name (optional)

        Returns:
            Created User object
        """

        user_request = UserRequest(
            email=email,
            name=name or email.split("@")[0],  # Use email prefix as fallback name
            is_active=True,
            avatar=None,
        )
        user_response = await self._user_service.create_user(user_request)
        # Get ORM object for relationships
        return await self._user_repository.get_user_by_id(user_response.id)  # type: ignore[return-value]

    async def _create_user_identity(
        self,
        user_id: int,
        provider_name: str,
        external_id: str,
        external_email: str | None,
        external_username: str | None,
    ) -> UserIdentity:
        """Create a new user identity linking.

        Args:
            user_id: ID of the user to link
            provider_name: Name of the identity provider
            external_id: Provider's unique user ID
            external_email: Email from provider (optional)
            external_username: Username from provider (optional)

        Returns:
            Created UserIdentity object
        """
        identity = UserIdentity(
            user_id=user_id,
            identity_provider=provider_name,
            external_id=external_id,
            external_email=external_email,
            external_username=external_username,
        )
        return await self._user_identity_repository.create_identity(identity)

    async def _create_account_link_request(
        self,
        provider_name: str,
        external_id: str,
        external_email: str | None,
        external_username: str | None,
        user_id: int,
    ) -> AccountLinkRequest:
        """Create an account link request.

        Args:
            provider_name: Name of the identity provider
            external_id: Provider's unique user ID
            external_email: Email from provider
            external_username: Username from provider
            user_id: ID of the existing user to link to

        Returns:
            Created AccountLinkRequest object
        """
        # First create the identity (unlinked, will be linked when approved)
        identity = UserIdentity(
            user_id=user_id,  # Temporary link, will be confirmed on approval
            identity_provider=provider_name,
            external_id=external_id,
            external_email=external_email,
            external_username=external_username,
        )
        identity = await self._user_identity_repository.create_identity(identity)

        # Generate secure request token
        request_token = secrets.token_urlsafe(32)
        expires_at = utc_now() + timedelta(hours=self.LINK_REQUEST_EXPIRATION_HOURS)

        link_request = AccountLinkRequest(
            request_token=request_token,
            user_identity_id=identity.id,
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=expires_at,
        )
        return await self._account_link_request_repository.create_request(link_request)
