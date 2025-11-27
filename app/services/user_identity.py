"""
Service for managing user identities linked to external identity providers.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models import UserIdentity
from app.repositories import UserIdentityRepository
from app.schemas import UserIdentityRequest, UserIdentityResponse, UserIdentityUpdateRequest
from app.services.user import UserService


class UserIdentityService:
    """Service for managing user identities."""

    def __init__(
        self,
        session: AsyncSession,
        user_service: UserService,
    ):
        """
        Initialize UserIdentityService with dependencies.

        Args:
            session: Database session for repository operations
            user_service: User service for user operations
        """
        self._session = session
        self._user_service = user_service
        self._user_identity_repository = UserIdentityRepository(session)

    async def get_identity_by_id(self, identity_id: int) -> UserIdentityResponse | None:
        """
        Get a user identity by its ID.

        Args:
            identity_id: ID of the user identity

        Returns:
            UserIdentityResponse if found, None otherwise
        """
        identity = await self._user_identity_repository.get_identity_by_id(identity_id)
        if identity is None:
            return None
        return UserIdentityResponse.model_validate(identity)

    async def get_identity_by_provider_and_external_id(
        self, provider_name: str, external_id: str
    ) -> UserIdentityResponse | None:
        """
        Get a user identity by provider and external ID.

        Args:
            provider_name: Name of the identity provider (e.g., 'microsoft', 'google')
            external_id: External ID from the provider

        Returns:
            UserIdentityResponse if found, None otherwise
        """
        identity = await self._user_identity_repository.get_identity_by_provider_and_external_id(
            provider_name, external_id
        )
        if identity is None:
            return None
        return UserIdentityResponse.model_validate(identity)

    async def get_identities_by_user_id(self, user_id: int) -> list[UserIdentityResponse]:
        """
        Get all identities for a specific user.

        Args:
            user_id: ID of the user

        Returns:
            List of UserIdentityResponse objects
        """
        identities = await self._user_identity_repository.get_identities_by_user_id(user_id)
        return [UserIdentityResponse.model_validate(identity) for identity in identities]

    async def create_identity(self, request: UserIdentityRequest) -> UserIdentityResponse:
        """
        Create a new user identity.

        Args:
            request: UserIdentityRequest containing identity information

        Returns:
            Created UserIdentityResponse

        Raises:
            NotFoundError: If user does not exist
            ConflictError: If identity already exists for this provider/external_id combination
        """
        # Verify user exists
        user = await self._user_service.get_user_by_id(request.user_id)
        if user is None:
            raise NotFoundError(f"User {request.user_id} not found")

        # Check if identity already exists
        existing = await self._user_identity_repository.get_identity_by_provider_and_external_id(
            request.identity_provider, request.external_id
        )
        if existing:
            raise ConflictError(
                f"Identity already exists for provider '{request.identity_provider}' "
                f"with external_id '{request.external_id}'"
            )

        identity = UserIdentity(
            user_id=request.user_id,
            identity_provider=request.identity_provider,
            external_id=request.external_id,
            external_email=request.external_email,
            external_username=request.external_username,
        )

        identity = await self._user_identity_repository.create_identity(identity)

        return UserIdentityResponse.model_validate(identity)

    async def update_identity(self, identity_id: int, request: UserIdentityUpdateRequest) -> UserIdentityResponse:
        """
        Update an existing user identity.

        Args:
            identity_id: ID of the identity to update
            request: UserIdentityUpdateRequest containing fields to update

        Returns:
            Updated UserIdentityResponse

        Raises:
            NotFoundError: If identity does not exist
        """
        identity = await self._user_identity_repository.get_identity_by_id(identity_id)
        if identity is None:
            raise NotFoundError(f"User identity {identity_id} not found")

        # Update only mutable fields
        if request.external_email is not None:
            identity.external_email = request.external_email
        if request.external_username is not None:
            identity.external_username = request.external_username

        identity = await self._user_identity_repository.update_identity(identity)

        return UserIdentityResponse.model_validate(identity)

    async def delete_identity(self, identity_id: int) -> None:
        """
        Delete a user identity.

        Args:
            identity_id: ID of the identity to delete

        Raises:
            NotFoundError: If identity does not exist
        """
        identity = await self._user_identity_repository.get_identity_by_id(identity_id)
        if identity is None:
            raise NotFoundError(f"User identity {identity_id} not found")

        await self._user_identity_repository.delete_identity(identity_id)
