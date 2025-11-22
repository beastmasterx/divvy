from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Category


class CategoryRepository:
    """Repository for managing category entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_categories(self) -> Sequence[Category]:
        """Retrieve all categories ordered by ID from the database."""
        stmt = select(Category).order_by(Category.id)
        return self.session.execute(stmt).scalars().all()

    def get_category_by_id(self, category_id: int) -> Category | None:
        """Retrieve a specific category by its ID."""
        stmt = select(Category).where(Category.id == category_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_category_by_name(self, name: str) -> Category | None:
        """Retrieve a specific category by its name."""
        stmt = select(Category).where(Category.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_category(self, category: Category) -> Category:
        """Create a new category and persist it to the database."""
        self.session.add(category)
        self.session.commit()
        return category

    def update_category(self, category: Category) -> Category:
        """Update an existing category and commit changes to the database."""
        self.session.commit()
        return category

    def delete_category(self, category_id: int) -> None:
        """Delete a category by its ID if it exists."""
        category = self.get_category_by_id(category_id)
        if category:
            self.session.delete(category)
            self.session.commit()
