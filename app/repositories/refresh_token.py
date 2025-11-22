"""Repository for managing refresh token entities."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RefreshToken


class RefreshTokenRepository:
    """Repository for managing refresh token entities."""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        hashed_token: str,
        user_id: int,
        expires_at: datetime,
        device_info: str | None = None,
    ) -> RefreshToken:
        """Create a new refresh token and persist it to the database."""
        refresh_token = RefreshToken(
            token=hashed_token,
            user_id=user_id,
            expires_at=expires_at,
            device_info=device_info,
            is_revoked=False,
        )
        self.session.add(refresh_token)
        self.session.commit()
        return refresh_token

    def lookup(self, hashed_token: str) -> RefreshToken | None:
        """Retrieve a refresh token by its hashed token."""
        stmt = select(RefreshToken).where(RefreshToken.token == hashed_token)
        return self.session.execute(stmt).scalar_one_or_none()

    def revoke_by_id(self, id: int) -> RefreshToken | None:
        """Revoke a refresh token by its ID and return the revoked token."""
        refresh_token = self.session.get(RefreshToken, id)
        if refresh_token:
            refresh_token.is_revoked = True
            self.session.commit()
        return refresh_token

    def revoke(self, hashed_token: str) -> RefreshToken | None:
        """Revoke a refresh token by its token and return the revoked token."""
        refresh_token = self.lookup(hashed_token)
        if refresh_token:
            refresh_token.is_revoked = True
            self.session.commit()
        return refresh_token

    def revoke_all(self, user_id: int) -> None:
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
