"""
Unit tests for RefreshTokenRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken, User
from app.repositories import RefreshTokenRepository


@pytest.mark.unit
class TestRefreshTokenRepository:
    """Test suite for RefreshTokenRepository."""

    @pytest.fixture
    def refresh_token_repository(self, db_session: AsyncSession) -> RefreshTokenRepository:
        return RefreshTokenRepository(db_session)

    async def test_create_refresh_token(
        self, refresh_token_repository: RefreshTokenRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test creating a new refresh token."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token
        token_id = "test_token_123"
        device_info = "Test Device"
        created = await refresh_token_repository.create(id=token_id, user_id=user.id, device_info=device_info)

        assert created.id == token_id
        assert created.user_id == user.id
        assert created.device_info == device_info
        assert created.is_revoked is False

        # Verify it's in the database
        retrieved = await refresh_token_repository.get_by_id(token_id)

        assert retrieved is not None
        assert retrieved.id == token_id
        assert retrieved.user_id == user.id

    async def test_create_refresh_token_without_device_info(
        self, refresh_token_repository: RefreshTokenRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test creating a refresh token without device info."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token without device info
        token_id = "test_token_456"
        created = await refresh_token_repository.create(id=token_id, user_id=user.id, device_info=None)

        assert created.id == token_id
        assert created.user_id == user.id
        assert created.device_info is None
        assert created.is_revoked is False

    async def test_get_by_id_exists(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test retrieving a refresh token by ID when it exists."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token
        token = await refresh_token_factory(id="existing_token_123", user_id=user.id, device_info="Device 1")

        retrieved = await refresh_token_repository.get_by_id(token.id)

        assert retrieved is not None
        assert retrieved.id == token.id
        assert retrieved.user_id == user.id
        assert retrieved.device_info == token.device_info
        assert retrieved.is_revoked == token.is_revoked

    async def test_get_by_id_not_exists(self, refresh_token_repository: RefreshTokenRepository):
        """Test retrieving a refresh token by ID when it doesn't exist."""
        result = await refresh_token_repository.get_by_id("nonexistent_token")

        assert result is None

    async def test_revoke_by_id_exists(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test revoking a refresh token by ID when it exists."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token (not revoked)
        token = await refresh_token_factory(id="token_to_revoke", user_id=user.id, is_revoked=False)

        # Verify it's not revoked initially
        assert token.is_revoked is False

        # Revoke it
        revoked = await refresh_token_repository.revoke_by_id(token.id)

        assert revoked is not None
        assert revoked.id == token.id
        assert revoked.is_revoked is True

        # Verify the revocation persisted
        retrieved = await refresh_token_repository.get_by_id(token.id)

        assert retrieved is not None
        assert retrieved.is_revoked is True

    async def test_revoke_by_id_already_revoked(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test revoking a refresh token that is already revoked."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token (already revoked)
        token = await refresh_token_factory(id="already_revoked_token", user_id=user.id, is_revoked=True)

        # Revoke it again (should still be revoked)
        revoked = await refresh_token_repository.revoke_by_id(token.id)

        assert revoked is not None
        assert revoked.id == token.id
        assert revoked.is_revoked is True

    async def test_revoke_by_id_not_exists(self, refresh_token_repository: RefreshTokenRepository):
        """Test revoking a refresh token that doesn't exist."""
        result = await refresh_token_repository.revoke_by_id("nonexistent_token")

        assert result is None

    async def test_revoke_all_single_token(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test revoking all refresh tokens for a user with a single token."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create a refresh token
        token = await refresh_token_factory(id="token_1", user_id=user.id, is_revoked=False)

        # Revoke all tokens for the user
        await refresh_token_repository.revoke_all(user.id)

        # Verify the token is revoked
        retrieved = await refresh_token_repository.get_by_id(token.id)

        assert retrieved is not None
        assert retrieved.is_revoked is True

    async def test_revoke_all_multiple_tokens(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test revoking all refresh tokens for a user with multiple tokens."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create multiple refresh tokens
        token1 = await refresh_token_factory(id="token_1", user_id=user.id, is_revoked=False)
        token2 = await refresh_token_factory(id="token_2", user_id=user.id, is_revoked=False)
        token3 = await refresh_token_factory(id="token_3", user_id=user.id, is_revoked=False)

        # Revoke all tokens for the user
        await refresh_token_repository.revoke_all(user.id)

        # Verify all tokens are revoked
        retrieved1 = await refresh_token_repository.get_by_id(token1.id)
        retrieved2 = await refresh_token_repository.get_by_id(token2.id)
        retrieved3 = await refresh_token_repository.get_by_id(token3.id)

        assert retrieved1 is not None
        assert retrieved1.is_revoked is True
        assert retrieved2 is not None
        assert retrieved2.is_revoked is True
        assert retrieved3 is not None
        assert retrieved3.is_revoked is True

    async def test_revoke_all_skips_already_revoked(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test that revoke_all only revokes non-revoked tokens."""
        # Create a user first
        user = await user_factory(email="test@example.com", name="Test User")

        # Create tokens with different revocation statuses
        token1 = await refresh_token_factory(id="token_1", user_id=user.id, is_revoked=False)
        token2 = await refresh_token_factory(id="token_2", user_id=user.id, is_revoked=True)  # Already revoked
        token3 = await refresh_token_factory(id="token_3", user_id=user.id, is_revoked=False)

        # Revoke all tokens for the user
        await refresh_token_repository.revoke_all(user.id)

        # Verify all non-revoked tokens are now revoked
        retrieved1 = await refresh_token_repository.get_by_id(token1.id)
        retrieved2 = await refresh_token_repository.get_by_id(token2.id)
        retrieved3 = await refresh_token_repository.get_by_id(token3.id)

        assert retrieved1 is not None
        assert retrieved1.is_revoked is True  # Was revoked
        assert retrieved2 is not None
        assert retrieved2.is_revoked is True  # Was already revoked, still revoked
        assert retrieved3 is not None
        assert retrieved3.is_revoked is True  # Was revoked

    async def test_revoke_all_only_affects_specific_user(
        self,
        refresh_token_repository: RefreshTokenRepository,
        user_factory: Callable[..., Awaitable[User]],
        refresh_token_factory: Callable[..., Awaitable[RefreshToken]],
    ):
        """Test that revoke_all only affects tokens for the specified user."""
        # Create two users
        user1 = await user_factory(email="user1@example.com", name="User 1")
        user2 = await user_factory(email="user2@example.com", name="User 2")

        # Create tokens for both users
        token1 = await refresh_token_factory(id="token_user1", user_id=user1.id, is_revoked=False)
        token2 = await refresh_token_factory(id="token_user2", user_id=user2.id, is_revoked=False)

        # Revoke all tokens for user1 only
        await refresh_token_repository.revoke_all(user1.id)

        # Verify only user1's token is revoked
        retrieved1 = await refresh_token_repository.get_by_id(token1.id)
        retrieved2 = await refresh_token_repository.get_by_id(token2.id)

        assert retrieved1 is not None
        assert retrieved1.is_revoked is True  # Revoked
        assert retrieved2 is not None
        assert retrieved2.is_revoked is False  # Not revoked (different user)

    async def test_revoke_all_no_tokens(
        self, refresh_token_repository: RefreshTokenRepository, user_factory: Callable[..., Awaitable[User]]
    ):
        """Test revoking all tokens for a user with no tokens (should not raise error)."""
        # Create a user with no tokens
        user = await user_factory(email="test@example.com", name="Test User")

        # Should not raise an exception
        await refresh_token_repository.revoke_all(user.id)
