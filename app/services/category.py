from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.models import Category
from app.repositories import CategoryRepository


class CategoryService:
    """Service layer for category-related business logic and operations."""

    def __init__(self, session: Session):
        self.category_repository = CategoryRepository(session)

    def get_all_categories(self) -> Sequence[Category]:
        """Retrieve all categories."""
        return self.category_repository.get_all_categories()

    def get_category_by_id(self, category_id: int) -> Category | None:
        """Retrieve a specific category by its ID."""
        return self.category_repository.get_category_by_id(category_id)

    def get_category_by_name(self, name: str) -> Category | None:
        """Retrieve a specific category by its name."""
        return self.category_repository.get_category_by_name(name)

    def create_category(self, category: Category) -> Category:
        """Create a new category."""
        return self.category_repository.create_category(category)

    def update_category(self, category: Category) -> Category:
        """Update an existing category."""
        return self.category_repository.update_category(category)

    def delete_category(self, category_id: int) -> None:
        """Delete a category by its ID."""
        return self.category_repository.delete_category(category_id)
