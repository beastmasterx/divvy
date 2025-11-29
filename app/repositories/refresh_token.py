"""Repository for managing refresh token entities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


class RefreshTokenRepository:
    """Repository for managing refresh token entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        id: str,
        user_id: int,
        device_info: str | None = None,
    ) -> RefreshToken:
        """Create a new refresh token and persist it to the database."""
        refresh_token = RefreshToken(
            id=id,
            user_id=user_id,
            device_info=device_info,
            is_revoked=False,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_by_id(self, id: str) -> RefreshToken | None:
        """Retrieve a refresh token by its ID."""
        stmt = select(RefreshToken).where(RefreshToken.id == id)
        return (await self.session.scalars(stmt)).one_or_none()

    async def revoke_by_id(self, id: str) -> RefreshToken | None:
        """Revoke a refresh token by its ID and return the revoked token."""
        refresh_token = await self.get_by_id(id)
        if refresh_token:
            refresh_token.is_revoked = True
            await self.session.flush()
        return refresh_token

    async def revoke_all(self, user_id: int) -> None:
        """Revoke all refresh tokens for a specific user."""
        stmt = select(RefreshToken).where(RefreshToken.user_id == user_id).where(~RefreshToken.is_revoked)
        tokens = (await self.session.scalars(stmt)).all()
        for token in tokens:
            token.is_revoked = True
        await self.session.flush()
