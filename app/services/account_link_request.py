"""
Service for managing account link requests.
"""

import logging
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_account_link_request_expiration_hours
from app.core.datetime import utc, utc_now
from app.core.i18n import _
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.models import AccountLinkRequest, AccountLinkRequestStatus, UserIdentity
from app.repositories import AccountLinkRequestRepository, UserIdentityRepository
from app.schemas import AccountLinkRequestCreateRequest, AccountLinkRequestResponse
from app.services.user import UserService

logger = logging.getLogger(__name__)


class AccountLinkRequestService:
    """Service for managing account link requests."""

    def __init__(self, session: AsyncSession, user_service: UserService):
        """
        Initialize AccountLinkRequestService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for user operations
        """
        self._session = session
        self._account_link_request_repository = AccountLinkRequestRepository(session)
        self._user_identity_repository = UserIdentityRepository(session)
        self._user_service = user_service
        self._account_link_request_expiration_hours = get_account_link_request_expiration_hours()

    async def get_request_by_id(self, request_id: int) -> AccountLinkRequestResponse | None:
        """
        Get an account link request by its ID.

        Args:
            request_id: ID of the account link request

        Returns:
            AccountLinkRequestResponse if found, None otherwise
        """
        request = await self._account_link_request_repository.get_request_by_id(request_id)
        if request is None:
            return None
        return AccountLinkRequestResponse.model_validate(request)

    async def get_request_by_token(self, request_token: str) -> AccountLinkRequestResponse | None:
        """
        Get an account link request by its token.

        Args:
            request_token: Token of the account link request

        Returns:
            AccountLinkRequestResponse if found, None otherwise
        """
        request = await self._account_link_request_repository.get_request_by_token(request_token)
        if request is None:
            return None
        return AccountLinkRequestResponse.model_validate(request)

    async def get_pending_requests_by_user_id(self, user_id: int) -> list[AccountLinkRequestResponse]:
        """
        Get all pending requests for a specific user.

        Args:
            user_id: ID of the user

        Returns:
            List of AccountLinkRequestResponse objects with pending status
        """
        requests = await self._account_link_request_repository.get_pending_requests_by_user_id(user_id)
        return [AccountLinkRequestResponse.model_validate(request) for request in requests]

    async def get_expired_requests(self) -> list[AccountLinkRequestResponse]:
        """
        Get all expired pending requests.

        Returns:
            List of AccountLinkRequestResponse objects that are expired
        """
        requests = await self._account_link_request_repository.get_expired_requests()
        return [AccountLinkRequestResponse.model_validate(request) for request in requests]

    async def create_request(self, request: AccountLinkRequestCreateRequest) -> AccountLinkRequestResponse:
        """
        Create a new account link request.

        Generates a secure request token and sets expiration to 24 hours from now.

        Args:
            request: AccountLinkRequestCreateRequest containing user and provider information

        Returns:
            Created AccountLinkRequestResponse

        Raises:
            ConflictError: If a pending request already exists for this provider/external_id combination
        """
        # Check if a pending request already exists for this provider/external_id
        existing = await self._account_link_request_repository.get_pending_request_by_provider_and_external_id(
            request.identity_provider, request.external_id
        )
        if existing:
            raise ConflictError(
                f"Pending account link request already exists for provider '{request.identity_provider}' "
                f"with external_id '{request.external_id}'"
            )

        # Generate secure request token
        request_token = secrets.token_urlsafe(32)

        # Set expiration to 24 hours from now
        expires_at = utc_now() + timedelta(hours=self._account_link_request_expiration_hours)

        link_request = AccountLinkRequest(
            user_id=request.user_id,
            identity_provider=request.identity_provider,
            external_id=request.external_id,
            external_email=request.external_email,
            external_username=request.external_username,
            request_token=request_token,
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=expires_at,
        )
        link_request = await self._account_link_request_repository.create_request(link_request)

        return AccountLinkRequestResponse.model_validate(link_request)

    async def approve_request(self, request_token: str, current_user_id: int) -> None:
        """
        Approve an account link request for an authenticated user.

        Creates the UserIdentity entry when the request is approved.

        Args:
            request_token: Account link request token
            current_user_id: ID of authenticated user (required)

        Raises:
            NotFoundError: If request not found or user not found
            ValidationError: If request is expired or already processed
            UnauthorizedError: If user is inactive or authenticated user doesn't match request
            ConflictError: If identity already exists for this provider/external_id combination
        """
        link_request = await self._account_link_request_repository.get_request_by_token(request_token)
        if not link_request:
            raise NotFoundError(_("Account link request not found"))

        # Check if request is already processed
        if link_request.status == AccountLinkRequestStatus.APPROVED.value:
            raise ValidationError(_("Account link request is already approved"))

        # Check if request has expired
        if utc(link_request.expires_at) < utc_now():
            raise ValidationError(_("Account link request has expired"))

        # Verify authenticated user matches the request
        if current_user_id != link_request.user_id:
            raise UnauthorizedError(_("Authenticated user does not match account link request"))

        # Verify user exists and is active
        user = await self._user_service.get_user_by_id(link_request.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError(_("User account not found or inactive"))

        # Check if identity already exists for this provider/external_id
        existing_identity = await self._user_identity_repository.get_identity_by_provider_and_external_id(
            link_request.identity_provider, link_request.external_id
        )
        if existing_identity:
            raise ConflictError(
                f"Identity already exists for provider '{link_request.identity_provider}' "
                f"with external_id '{link_request.external_id}'"
            )

        # Create the UserIdentity entry
        user_identity = UserIdentity(
            user_id=link_request.user_id,
            identity_provider=link_request.identity_provider,
            external_id=link_request.external_id,
            external_email=link_request.external_email,
            external_username=link_request.external_username,
        )
        user_identity = await self._user_identity_repository.create_identity(user_identity)

        # Approve the request
        link_request.status = AccountLinkRequestStatus.APPROVED.value
        await self._account_link_request_repository.update_request(link_request)

        logger.info(
            f"Account link approved: identity {user_identity.id} "
            f"linked to user {user_identity.user_id} for provider {link_request.identity_provider}"
        )
