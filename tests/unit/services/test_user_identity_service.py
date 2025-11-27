"""
Unit tests for UserIdentityService.
"""

from collections.abc import Awaitable, Callable

import pytest

from app.exceptions import ConflictError, NotFoundError
from app.models import IdentityProviderName, User, UserIdentity
from app.schemas import UserIdentityRequest, UserIdentityResponse, UserIdentityUpdateRequest
from app.services import UserIdentityService


@pytest.mark.unit
class TestUserIdentityService:
    """Test suite for UserIdentityService."""

    async def test_get_identity_by_id_exists(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving a user identity by ID when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email="ms@example.com",
        )

        result = await user_identity_service.get_identity_by_id(identity.id)

        assert result is not None
        assert isinstance(result, UserIdentityResponse)
        assert result.id == identity.id
        assert result.user_id == user.id
        assert result.identity_provider == identity.identity_provider
        assert result.external_id == identity.external_id
        assert result.external_email == identity.external_email

    async def test_get_identity_by_id_not_exists(self, user_identity_service: UserIdentityService):
        """Test retrieving a user identity by ID when it doesn't exist."""
        result = await user_identity_service.get_identity_by_id(99999)

        assert result is None

    async def test_get_identity_by_provider_and_external_id_exists(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving a user identity by provider and external ID when it exists."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
            external_email="google@example.com",
        )

        result = await user_identity_service.get_identity_by_provider_and_external_id(
            IdentityProviderName.GOOGLE, identity.external_id
        )

        assert result is not None
        assert isinstance(result, UserIdentityResponse)
        assert result.id == identity.id
        assert result.identity_provider == identity.identity_provider
        assert result.external_id == identity.external_id
        assert result.external_email == identity.external_email

    async def test_get_identity_by_provider_and_external_id_not_exists(
        self, user_identity_service: UserIdentityService
    ):
        """Test retrieving a user identity by provider and external ID when it doesn't exist."""
        result = await user_identity_service.get_identity_by_provider_and_external_id(
            IdentityProviderName.MICROSOFT, "nonexistent"
        )

        assert result is None

    async def test_get_identities_by_user_id_empty(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test retrieving identities for a user when none exist."""
        user = await user_factory(email="test@example.com", name="Test User")

        identities = await user_identity_service.get_identities_by_user_id(user.id)

        assert isinstance(identities, list)
        assert len(identities) == 0

    async def test_get_identities_by_user_id_multiple(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving all identities for a user when multiple exist."""
        user = await user_factory(email="test@example.com", name="Test User")
        user2 = await user_factory(email="test2@example.com", name="Test User 2")

        # Create multiple identities for user
        identity1 = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )
        identity2 = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_456",
        )
        # Create identity for different user (should not be included)
        identity3 = await user_identity_factory(
            user_id=user2.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_999",
        )

        identities = await user_identity_service.get_identities_by_user_id(user.id)

        assert len(identities) == 2
        identity_ids = {id.id for id in identities}
        assert identity1.id in identity_ids
        assert identity2.id in identity_ids
        assert identity3.id not in identity_ids

    async def test_create_identity_success(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test creating a new user identity successfully."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = UserIdentityRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_new_123",
            external_email="ms@example.com",
            external_username="ms_user",
        )

        result = await user_identity_service.create_identity(request)

        assert result is not None
        assert isinstance(result, UserIdentityResponse)
        assert result.user_id == user.id
        assert result.identity_provider == request.identity_provider
        assert result.external_id == request.external_id
        assert result.external_email == request.external_email
        assert result.external_username == request.external_username

    async def test_create_identity_user_not_found_raises_error(self, user_identity_service: UserIdentityService):
        """Test creating an identity for non-existent user raises NotFoundError."""
        request = UserIdentityRequest(
            user_id=99999,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        with pytest.raises(NotFoundError, match="User.*not found"):
            await user_identity_service.create_identity(request)

    async def test_create_identity_existing_raises_conflict(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test creating an identity when one already exists raises ConflictError."""
        user = await user_factory(email="test@example.com", name="Test User")

        # Create existing identity
        await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        request = UserIdentityRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",  # Same provider and external_id
        )

        with pytest.raises(ConflictError, match="Identity already exists"):
            await user_identity_service.create_identity(request)

    async def test_create_identity_same_provider_different_external_id_allows(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test creating identities with same provider but different external_id is allowed."""
        user = await user_factory(email="test@example.com", name="Test User")

        # Create existing identity
        await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        request = UserIdentityRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_456",  # Different external_id
        )

        # Should succeed
        result = await user_identity_service.create_identity(request)

        assert result is not None
        assert result.external_id == request.external_id

    async def test_update_identity_success(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test updating an existing user identity successfully."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email="original@example.com",
            external_username="original_user",
        )

        update_request = UserIdentityUpdateRequest(
            external_email="updated@example.com",
            external_username="updated_user",
        )

        result = await user_identity_service.update_identity(identity.id, update_request)

        assert result is not None
        assert isinstance(result, UserIdentityResponse)
        assert result.id == identity.id
        assert result.external_email == "updated@example.com"
        assert result.external_username == "updated_user"
        # Verify immutable fields unchanged
        assert result.user_id == user.id
        assert result.identity_provider == identity.identity_provider
        assert result.external_id == identity.external_id

    async def test_update_identity_partial_update(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test updating only some fields of an identity."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email="original@example.com",
            external_username="original_user",
        )

        # Update only email
        update_request = UserIdentityUpdateRequest(external_email="updated@example.com")

        result = await user_identity_service.update_identity(identity.id, update_request)

        assert result.external_email == "updated@example.com"
        assert result.external_username == identity.external_username  # Unchanged

    async def test_update_identity_not_found_raises_error(self, user_identity_service: UserIdentityService):
        """Test updating a non-existent identity raises NotFoundError."""
        update_request = UserIdentityUpdateRequest(external_email="updated@example.com")

        with pytest.raises(NotFoundError, match="User identity.*not found"):
            await user_identity_service.update_identity(99999, update_request)

    async def test_delete_identity_success(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test deleting a user identity successfully."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )

        await user_identity_service.delete_identity(identity.id)

        # Verify it's deleted
        deleted = await user_identity_service.get_identity_by_id(identity.id)

        assert deleted is None

    async def test_delete_identity_not_found_raises_error(self, user_identity_service: UserIdentityService):
        """Test deleting a non-existent identity raises NotFoundError."""
        with pytest.raises(NotFoundError, match="User identity.*not found"):
            await user_identity_service.delete_identity(99999)

    async def test_create_identity_with_optional_fields(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
    ):
        """Test creating an identity with optional fields set to None."""
        user = await user_factory(email="test@example.com", name="Test User")

        request = UserIdentityRequest(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email=None,
            external_username=None,
        )

        result = await user_identity_service.create_identity(request)

        assert result is not None
        assert result.external_email is None
        assert result.external_username is None

    async def test_update_identity_with_none_values(
        self,
        user_identity_service: UserIdentityService,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test updating an identity with None values (should not update)."""
        user = await user_factory(email="test@example.com", name="Test User")
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
            external_email="original@example.com",
            external_username="original_user",
        )

        # Update with None values (should not change)
        update_request = UserIdentityUpdateRequest(
            external_email=None,
            external_username=None,
        )

        result = await user_identity_service.update_identity(identity.id, update_request)

        # Fields should remain unchanged when None is provided
        assert result.external_email == identity.external_email
        assert result.external_username == identity.external_username
