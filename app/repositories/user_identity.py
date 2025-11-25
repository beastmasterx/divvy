"""
Repository for managing user identity entities.
"""

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserIdentity


class UserIdentityRepository:
    """Repository for managing user identity entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_identity_by_id(self, id: int) -> UserIdentity | None:
        """Retrieve a specific user identity by its ID."""
        return await self.session.get(UserIdentity, id)

    async def get_identity_by_provider_and_external_id(
        self, identity_provider: str, external_id: str
    ) -> UserIdentity | None:
        """Retrieve a user identity by provider and external ID."""
        stmt = select(UserIdentity).where(
            UserIdentity.identity_provider == identity_provider,
            UserIdentity.external_id == external_id,
        )
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_identities_by_user_id(self, user_id: int) -> Sequence[UserIdentity]:
        """Retrieve all identities for a specific user."""
        stmt = select(UserIdentity).where(UserIdentity.user_id == user_id)
        return (await self.session.scalars(stmt)).all()

    async def get_identities_by_provider(self, identity_provider: str) -> Sequence[UserIdentity]:
        """Retrieve all identities for a specific provider."""
        stmt = select(UserIdentity).where(UserIdentity.identity_provider == identity_provider)
        return (await self.session.scalars(stmt)).all()

    async def create_identity(self, identity: UserIdentity) -> UserIdentity:
        """Create a new user identity and persist it to the database."""
        self.session.add(identity)
        await self.session.flush()
        return identity

    async def update_identity(self, identity: UserIdentity) -> UserIdentity:
        """Update an existing user identity and commit changes to the database."""
        await self.session.flush()
        return identity

    async def delete_identity(self, id: int) -> None:
        """Delete a user identity by its ID if it exists."""
        stmt = delete(UserIdentity).where(UserIdentity.id == id)
        await self.session.execute(stmt)
        await self.session.flush()
