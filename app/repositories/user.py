from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    """Repository for managing user entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> Sequence[User]:
        """Retrieve all users from the database."""
        stmt = select(User)
        return (await self.session.execute(stmt)).scalars().all()

    async def get_user_by_id(self, id: int) -> User | None:
        """Retrieve a specific user by their ID."""
        return await self.session.get(User, id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Retrieve a specific user by their email address."""
        stmt = select(User).where(User.email == email)
        return (await self.session.scalars(stmt)).one_or_none()

    async def create_user(self, user: User) -> User:
        """Create a new user and persist them to the database."""
        self.session.add(user)
        await self.session.commit()
        return user

    async def update_user(self, user: User) -> User:
        """Update an existing user and commit changes to the database."""
        await self.session.commit()
        return user

    async def delete_user(self, id: int) -> None:
        """Delete a user by their ID if they exist."""
        stmt = delete(User).where(User.id == id)
        await self.session.execute(stmt)
        await self.session.commit()
