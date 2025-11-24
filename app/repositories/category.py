from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Category


class CategoryRepository:
    """Repository for managing category entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories(self) -> Sequence[Category]:
        """Retrieve all categories ordered by ID from the database."""
        stmt = select(Category).order_by(Category.id)
        return (await self.session.scalars(stmt)).all()

    async def get_category_by_id(self, id: int) -> Category | None:
        """Retrieve a specific category by its ID."""
        return await self.session.get(Category, id)

    async def get_category_by_name(self, name: str) -> Category | None:
        """Retrieve a specific category by its name."""
        stmt = select(Category).where(Category.name == name)
        return (await self.session.scalars(stmt)).one_or_none()

    async def create_category(self, category: Category) -> Category:
        """Create a new category and persist it to the database."""
        self.session.add(category)
        await self.session.commit()
        return category

    async def update_category(self, category: Category) -> Category:
        """Update an existing category and commit changes to the database."""
        await self.session.commit()
        return category

    async def delete_category(self, id: int) -> None:
        """Delete a category by its ID if it exists."""
        stmt = delete(Category).where(Category.id == id)
        await self.session.execute(stmt)
        await self.session.commit()
