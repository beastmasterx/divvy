"""
Unit tests for UserIdentityRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IdentityProviderName, User, UserIdentity
from app.repositories import UserIdentityRepository
from tests.fixtures.factories import create_test_user_identity


@pytest.mark.unit
class TestUserIdentityRepository:
    """Test suite for UserIdentityRepository."""

    @pytest.fixture
    def user_identity_repository(self, db_session: AsyncSession) -> UserIdentityRepository:
        return UserIdentityRepository(db_session)

    async def test_get_identity_by_id_exists(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving a user identity by ID when it exists."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create an identity
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ext_123",
        )

        retrieved = await user_identity_repository.get_identity_by_id(identity.id)

        assert retrieved is not None
        assert retrieved.id == identity.id
        assert retrieved.identity_provider == identity.identity_provider
        assert retrieved.external_id == "ext_123"
        assert retrieved.user_id == user.id

    async def test_get_identity_by_id_not_exists(self, user_identity_repository: UserIdentityRepository):
        """Test retrieving a user identity by ID when it doesn't exist."""
        result = await user_identity_repository.get_identity_by_id(99999)

        assert result is None

    async def test_get_identity_by_provider_and_external_id_exists(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving a user identity by provider and external ID when it exists."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")
        # Create an identity
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="google_456",
            external_email="google@example.com",
        )

        retrieved = await user_identity_repository.get_identity_by_provider_and_external_id(
            identity.identity_provider, identity.external_id
        )

        assert retrieved is not None
        assert retrieved.identity_provider == identity.identity_provider
        assert retrieved.external_id == identity.external_id
        assert retrieved.external_email == identity.external_email
        assert retrieved.user_id == user.id

    async def test_get_identity_by_provider_and_external_id_not_exists(
        self, user_identity_repository: UserIdentityRepository
    ):
        """Test retrieving a user identity by provider and external ID when it doesn't exist."""
        result = await user_identity_repository.get_identity_by_provider_and_external_id("microsoft", "nonexistent")
        assert result is None

    async def test_get_identities_by_user_id_empty(
        self, user_identity_repository: UserIdentityRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test retrieving identities for a user when none exist."""
        # Create a user
        user = await user_factory(email="test@example.com", name="Test User")

        identities = await user_identity_repository.get_identities_by_user_id(user.id)

        assert isinstance(identities, list)
        assert len(identities) == 0

    async def test_get_identities_by_user_id_multiple(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving all identities for a user when multiple exist."""
        # Create a user
        user = await user_factory(email="test@example.com", name="Test User")

        # Create multiple identities
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

        identities = await user_identity_repository.get_identities_by_user_id(user.id)

        assert len(identities) == 2

        providers = {id.identity_provider for id in identities}

        assert identity1.identity_provider in providers
        assert identity2.identity_provider in providers

    async def test_get_identities_by_provider_empty(self, user_identity_repository: UserIdentityRepository):
        """Test retrieving identities for a provider when none exist."""
        identities = await user_identity_repository.get_identities_by_provider(IdentityProviderName.MICROSOFT)

        assert isinstance(identities, list)
        assert len(identities) == 0

    async def test_get_identities_by_provider_multiple(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test retrieving all identities for a provider when multiple exist."""
        # Create multiple users
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")

        # Create multiple identities for the same provider
        identity1 = await user_identity_factory(
            user_id=user1.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_123",
        )
        identity2 = await user_identity_factory(
            user_id=user2.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_456",
        )
        # Create one for a different provider
        identity3 = await user_identity_factory(
            user_id=user1.id,
            identity_provider=IdentityProviderName.GOOGLE,
            external_id="go_789",
        )

        identities = await user_identity_repository.get_identities_by_provider("microsoft")

        assert len(identities) == 2

        external_ids = {id.external_id for id in identities}

        assert identity1.external_id in external_ids
        assert identity2.external_id in external_ids
        assert identity3.external_id not in external_ids

    async def test_create_identity(
        self, user_identity_repository: UserIdentityRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test creating a new user identity."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")
        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider=IdentityProviderName.FACEBOOK,
            external_id="fb_789",
            external_email="fb@example.com",
            external_username="fb_user",
        )
        created = await user_identity_repository.create_identity(identity)

        assert created.id is not None
        assert created.identity_provider == identity.identity_provider
        assert created.external_id == identity.external_id
        assert created.external_email == identity.external_email
        assert created.external_username == identity.external_username
        assert created.user_id == user.id

        # Verify it's in the database
        retrieved = await user_identity_repository.get_identity_by_id(created.id)

        assert retrieved is not None
        assert retrieved.external_id == identity.external_id

    async def test_update_identity(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test updating an existing user identity."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")
        # Create an identity
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_original",
            external_email="original@example.com",
        )

        # Update it
        identity.external_email = "updated@example.com"
        identity.external_username = "updated_user"

        updated = await user_identity_repository.update_identity(identity)

        assert updated.external_email == "updated@example.com"
        assert updated.external_username == "updated_user"

        # Verify the update persisted
        retrieved = await user_identity_repository.get_identity_by_id(identity.id)

        assert retrieved is not None
        assert retrieved.external_email == "updated@example.com"
        assert retrieved.external_username == "updated_user"

    async def test_delete_identity_exists(
        self,
        user_identity_repository: UserIdentityRepository,
        user_factory: Callable[..., Awaitable[User]],
        user_identity_factory: Callable[..., Awaitable[UserIdentity]],
    ):
        """Test deleting a user identity that exists."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create an identity
        identity = await user_identity_factory(
            user_id=user.id,
            identity_provider=IdentityProviderName.MICROSOFT,
            external_id="ms_to_delete",
        )

        # Delete it
        await user_identity_repository.delete_identity(identity.id)

        # Verify it's gone
        retrieved = await user_identity_repository.get_identity_by_id(identity.id)

        assert retrieved is None

    async def test_delete_identity_not_exists(self, user_identity_repository: UserIdentityRepository):
        """Test deleting a user identity that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await user_identity_repository.delete_identity(99999)
