"""
Unit tests for UserIdentityRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import UserIdentityRepository
from tests.fixtures.factories import create_test_user, create_test_user_identity


@pytest.mark.unit
class TestUserIdentityRepository:
    """Test suite for UserIdentityRepository."""

    async def test_get_identity_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a user identity by ID when it exists."""
        repo = UserIdentityRepository(db_session)

        # Create a user first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ext_123",
        )
        db_session.add(identity)
        await db_session.commit()
        identity_id = identity.id

        retrieved = await repo.get_identity_by_id(identity_id)
        assert retrieved is not None
        assert retrieved.id == identity_id
        assert retrieved.identity_provider == "microsoft"
        assert retrieved.external_id == "ext_123"
        assert retrieved.user_id == user.id

    async def test_get_identity_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user identity by ID when it doesn't exist."""
        repo = UserIdentityRepository(db_session)
        result = await repo.get_identity_by_id(99999)
        assert result is None

    async def test_get_identity_by_provider_and_external_id_exists(self, db_session: AsyncSession):
        """Test retrieving a user identity by provider and external ID when it exists."""
        repo = UserIdentityRepository(db_session)

        # Create a user first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="google",
            external_id="google_456",
            external_email="google@example.com",
        )
        db_session.add(identity)
        await db_session.commit()

        retrieved = await repo.get_identity_by_provider_and_external_id("google", "google_456")
        assert retrieved is not None
        assert retrieved.identity_provider == "google"
        assert retrieved.external_id == "google_456"
        assert retrieved.external_email == "google@example.com"
        assert retrieved.user_id == user.id

    async def test_get_identity_by_provider_and_external_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a user identity by provider and external ID when it doesn't exist."""
        repo = UserIdentityRepository(db_session)
        result = await repo.get_identity_by_provider_and_external_id("microsoft", "nonexistent")
        assert result is None

    async def test_get_identities_by_user_id_empty(self, db_session: AsyncSession):
        """Test retrieving identities for a user when none exist."""
        repo = UserIdentityRepository(db_session)

        # Create a user
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        identities = await repo.get_identities_by_user_id(user.id)
        assert isinstance(identities, list)
        assert len(identities) == 0

    async def test_get_identities_by_user_id_multiple(self, db_session: AsyncSession):
        """Test retrieving all identities for a user when multiple exist."""
        repo = UserIdentityRepository(db_session)

        # Create a user
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create multiple identities
        identity1 = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ms_123",
        )
        identity2 = create_test_user_identity(
            user_id=user.id,
            identity_provider="google",
            external_id="go_456",
        )
        db_session.add(identity1)
        db_session.add(identity2)
        await db_session.commit()

        identities = await repo.get_identities_by_user_id(user.id)
        assert len(identities) == 2
        providers = {id.identity_provider for id in identities}
        assert "microsoft" in providers
        assert "google" in providers

    async def test_get_identities_by_provider_empty(self, db_session: AsyncSession):
        """Test retrieving identities for a provider when none exist."""
        repo = UserIdentityRepository(db_session)
        identities = await repo.get_identities_by_provider("microsoft")
        assert isinstance(identities, list)
        assert len(identities) == 0

    async def test_get_identities_by_provider_multiple(self, db_session: AsyncSession):
        """Test retrieving all identities for a provider when multiple exist."""
        repo = UserIdentityRepository(db_session)

        # Create multiple users
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        # Create multiple identities for the same provider
        identity1 = create_test_user_identity(
            user_id=user1.id,
            identity_provider="microsoft",
            external_id="ms_123",
        )
        identity2 = create_test_user_identity(
            user_id=user2.id,
            identity_provider="microsoft",
            external_id="ms_456",
        )
        # Create one for a different provider
        identity3 = create_test_user_identity(
            user_id=user1.id,
            identity_provider="google",
            external_id="go_789",
        )
        db_session.add(identity1)
        db_session.add(identity2)
        db_session.add(identity3)
        await db_session.commit()

        identities = await repo.get_identities_by_provider("microsoft")
        assert len(identities) == 2
        external_ids = {id.external_id for id in identities}
        assert "ms_123" in external_ids
        assert "ms_456" in external_ids

    async def test_create_identity(self, db_session: AsyncSession):
        """Test creating a new user identity."""
        repo = UserIdentityRepository(db_session)

        # Create a user first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="facebook",
            external_id="fb_789",
            external_email="fb@example.com",
            external_username="fb_user",
        )
        created = await repo.create_identity(identity)

        assert created.id is not None
        assert created.identity_provider == "facebook"
        assert created.external_id == "fb_789"
        assert created.external_email == "fb@example.com"
        assert created.external_username == "fb_user"
        assert created.user_id == user.id

        # Verify it's in the database
        retrieved = await repo.get_identity_by_id(created.id)
        assert retrieved is not None
        assert retrieved.external_id == "fb_789"

    async def test_update_identity(self, db_session: AsyncSession):
        """Test updating an existing user identity."""
        repo = UserIdentityRepository(db_session)

        # Create a user first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ms_original",
            external_email="original@example.com",
        )
        db_session.add(identity)
        await db_session.commit()

        # Update it
        identity.external_email = "updated@example.com"
        identity.external_username = "updated_user"
        updated = await repo.update_identity(identity)

        assert updated.external_email == "updated@example.com"
        assert updated.external_username == "updated_user"

        # Verify the update persisted
        retrieved = await repo.get_identity_by_id(identity.id)
        assert retrieved is not None
        assert retrieved.external_email == "updated@example.com"
        assert retrieved.external_username == "updated_user"

    async def test_delete_identity_exists(self, db_session: AsyncSession):
        """Test deleting a user identity that exists."""
        repo = UserIdentityRepository(db_session)

        # Create a user first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()

        # Create an identity
        identity = create_test_user_identity(
            user_id=user.id,
            identity_provider="microsoft",
            external_id="ms_to_delete",
        )
        db_session.add(identity)
        await db_session.commit()
        identity_id = identity.id

        # Delete it
        await repo.delete_identity(identity_id)

        # Verify it's gone
        retrieved = await repo.get_identity_by_id(identity_id)
        assert retrieved is None

    async def test_delete_identity_not_exists(self, db_session: AsyncSession):
        """Test deleting a user identity that doesn't exist (should not raise error)."""
        repo = UserIdentityRepository(db_session)
        # Should not raise an exception
        await repo.delete_identity(99999)
