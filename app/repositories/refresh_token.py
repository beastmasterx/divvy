"""Repository for managing refresh token entities."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken


class RefreshTokenRepository:
    """Repository for managing refresh token entities."""

    def __init__(self, session: Session):
        self.session = session

    def create_refresh_token(
        self,
        token_lookup: str,
        token_hash: str,
        user_id: int,
        expires_at: datetime,
        device_info: str | None = None,
    ) -> RefreshToken:
        """Create a new refresh token and persist it to the database."""
        refresh_token = RefreshToken(
            token_lookup=token_lookup,
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
            is_revoked=False,
        )
        self.session.add(refresh_token)
        self.session.commit()
        return refresh_token

    def get_refresh_token_by_lookup(self, token_lookup: str) -> RefreshToken | None:
        """Retrieve a refresh token by its lookup key (SHA256 hash) for fast O(1) lookup."""
        stmt = select(RefreshToken).where(RefreshToken.token_lookup == token_lookup)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Retrieve a refresh token by its hash (legacy method, prefer get_refresh_token_by_lookup)."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_refresh_tokens_by_user_id(self, user_id: int) -> Sequence[RefreshToken]:
        """Retrieve all refresh tokens for a specific user."""
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def get_active_refresh_tokens_by_user_id(self, user_id: int) -> Sequence[RefreshToken]:
        """Retrieve all active (non-revoked, non-expired) refresh tokens for a user."""
        now = datetime.now(UTC)
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(~RefreshToken.is_revoked)
            .where(RefreshToken.expires_at > now)
        )
        return self.session.execute(stmt).scalars().all()

    def get_all_active_tokens(self) -> Sequence[RefreshToken]:
        """Retrieve all active (non-revoked, non-expired) refresh tokens across all users."""
        now = datetime.now(UTC)
        stmt = select(RefreshToken).where(~RefreshToken.is_revoked).where(RefreshToken.expires_at > now)
        return self.session.execute(stmt).scalars().all()

    def revoke_refresh_token(self, token_id: int) -> None:
        """Revoke a refresh token by marking it as revoked."""
        refresh_token = self.session.get(RefreshToken, token_id)
        if refresh_token:
            refresh_token.is_revoked = True
            self.session.commit()

    def revoke_refresh_token_by_hash(self, token_hash: str) -> None:
        """Revoke a refresh token by its hash."""
        refresh_token = self.get_refresh_token_by_hash(token_hash)
        if refresh_token:
            refresh_token.is_revoked = True
            self.session.commit()

    def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all refresh tokens for a specific user."""
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id).where(~RefreshToken.is_revoked)
        tokens = self.session.execute(stmt).scalars().all()
        for token in tokens:
            token.is_revoked = True
        self.session.commit()

    def update_last_used(self, token_id: int, last_used_at: datetime) -> None:
        """Update the last used timestamp for a refresh token."""
        refresh_token = self.session.get(RefreshToken, token_id)
        if refresh_token:
            refresh_token.last_used_at = last_used_at
            self.session.commit()

    def delete_expired_tokens(self) -> int:
        """Delete expired refresh tokens from the database. Returns count of deleted tokens."""
        now = datetime.now(UTC)
        stmt = select(RefreshToken).where(RefreshToken.expires_at < now)
        expired_tokens = self.session.execute(stmt).scalars().all()
        count = len(expired_tokens)
        for token in expired_tokens:
            self.session.delete(token)
        self.session.commit()
        return count

    def delete_refresh_token(self, token_id: int) -> None:
        """Delete a refresh token by its ID."""
        refresh_token = self.session.get(RefreshToken, token_id)
        if refresh_token:
            self.session.delete(refresh_token)
            self.session.commit()
