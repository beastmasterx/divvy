"""
Repository for managing user identity entities.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UserIdentity


class UserIdentityRepository:
    """Repository for managing user identity entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_identity_by_id(self, identity_id: int) -> UserIdentity | None:
        """Retrieve a specific user identity by its ID."""
        stmt = select(UserIdentity).where(UserIdentity.id == identity_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_identity_by_provider_and_external_id(
        self, identity_provider: str, external_id: str
    ) -> UserIdentity | None:
        """Retrieve a user identity by provider and external ID."""
        stmt = select(UserIdentity).where(
            UserIdentity.identity_provider == identity_provider,
            UserIdentity.external_id == external_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_identities_by_user_id(self, user_id: int) -> Sequence[UserIdentity]:
        """Retrieve all identities for a specific user."""
        stmt = select(UserIdentity).where(UserIdentity.user_id == user_id)
        return self.session.execute(stmt).scalars().all()

    def get_identities_by_provider(self, identity_provider: str) -> Sequence[UserIdentity]:
        """Retrieve all identities for a specific provider."""
        stmt = select(UserIdentity).where(UserIdentity.identity_provider == identity_provider)
        return self.session.execute(stmt).scalars().all()

    def create_identity(self, identity: UserIdentity) -> UserIdentity:
        """Create a new user identity and persist it to the database."""
        self.session.add(identity)
        self.session.commit()
        return identity

    def update_identity(self, identity: UserIdentity) -> UserIdentity:
        """Update an existing user identity and commit changes to the database."""
        self.session.commit()
        return identity

    def delete_identity(self, identity_id: int) -> None:
        """Delete a user identity by its ID if it exists."""
        identity = self.get_identity_by_id(identity_id)
        if identity:
            self.session.delete(identity)
            self.session.commit()

