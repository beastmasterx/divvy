"""
Service for managing identity provider OAuth flows and account linking.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.api.schemas import LinkingRequiredResponse, TokenResponse, UserRequest
from app.core.security import check_password
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
        session: Session,
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
        1. Exchange authorization code for access token
        2. Get user info from provider
        3. Check if identity already exists (by provider + external_id)
           - If exists: return tokens for existing user
        4. If identity doesn't exist:
           - Check if email exists in our system
           - If email exists: create account link request (return link request info)
           - If email doesn't exist: create new user + identity (return tokens)

        Args:
            provider_name: Name of the identity provider
            code: Authorization code from OAuth callback
            state: Optional state parameter from OAuth callback (for CSRF protection)
            device_info: Optional device information (e.g., User-Agent string)

        Returns:
            TokenResponse if user is authenticated, or LinkingRequiredResponse if linking required

        Raises:
            ValueError: If provider is not registered
            UnauthorizedError: If OAuth flow fails
            ValidationError: If state validation fails (when state is provided)
        """
        provider = IdentityProviderRegistry.get_provider(provider_name)

        # TODO: Implement state validation for CSRF protection
        # For now, state is accepted but not validated. In production, you should:
        # 1. Generate a signed state token in get_authorization_url() when state is provided
        # 2. Validate the state token signature and expiration in handle_oauth_callback()
        # 3. Reject the callback if state validation fails
        if state:
            logger.debug(f"OAuth state parameter received: {state} (validation not yet implemented)")

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
        existing_identity = self._user_identity_repository.get_identity_by_provider_and_external_id(
            provider_name, external_id
        )

        if existing_identity:
            # Identity exists, user is already linked - return tokens
            user = self._user_repository.get_user_by_id(existing_identity.user_id)
            if not user or not user.is_active:
                raise UnauthorizedError("User account not found or inactive")

            return self._auth_service.generate_tokens(user.id, device_info)

        # Identity doesn't exist - check if email exists
        existing_user = self._user_repository.get_user_by_email(email) if email else None

        if existing_user:
            # Email exists - create account link request
            logger.info(f"Email {email} exists, creating account link request for provider {provider_name}")
            link_request = self._create_account_link_request(
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
        user = self._create_user_from_provider(email, name)
        self._create_user_identity(
            user_id=user.id,
            provider_name=provider_name,
            external_id=external_id,
            external_email=email,
            external_username=name,
        )

        return self._auth_service.generate_tokens(user.id, device_info)

    def verify_account_link_request(
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
        request = self._account_link_request_repository.get_request_by_token(request_token)
        if not request:
            raise NotFoundError("Account link request not found")

        if request.status != AccountLinkRequestStatus.PENDING.value:
            raise ValidationError(f"Account link request is {request.status}, cannot verify")

        if request.expires_at < datetime.now(UTC):
            request.status = AccountLinkRequestStatus.EXPIRED.value
            self._account_link_request_repository.update_request(request)
            raise ValidationError("Account link request has expired")

        user = self._user_repository.get_user_by_id(request.user_identity.user_id)
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

    def approve_account_link_request(
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
        request = self.verify_account_link_request(request_token, password, user_id)

        # Link the identity to the user
        identity = request.user_identity
        identity.user_id = request.user_identity.user_id  # Already linked, but ensure consistency

        # Update request status
        request.status = AccountLinkRequestStatus.APPROVED.value
        request.verified_at = datetime.now(UTC)
        self._account_link_request_repository.update_request(request)

        # Get user and return tokens
        user = self._user_repository.get_user_by_id(identity.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User account not found or inactive")

        logger.info(f"Account link approved: identity {identity.id} linked to user {user.id}")
        return self._auth_service.generate_tokens(user.id, None)

    def _create_user_from_provider(self, email: str, name: str | None) -> User:
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
        user_response = self._user_service.create_user(user_request)
        # Get ORM object for relationships
        return self._user_repository.get_user_by_id(user_response.id)  # type: ignore[return-value]

    def _create_user_identity(
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
        return self._user_identity_repository.create_identity(identity)

    def _create_account_link_request(
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
        identity = self._user_identity_repository.create_identity(identity)

        # Generate secure request token
        request_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(hours=self.LINK_REQUEST_EXPIRATION_HOURS)

        link_request = AccountLinkRequest(
            request_token=request_token,
            user_identity_id=identity.id,
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=expires_at,
        )
        return self._account_link_request_repository.create_request(link_request)
