from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.api.schemas import CategoryRequest, CategoryResponse
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models.models import Category
from app.repositories import CategoryRepository


class CategoryService:
    """Service layer for category-related business logic and operations."""

    def __init__(self, session: Session):
        self._category_repository = CategoryRepository(session)

    def get_all_categories(self) -> Sequence[CategoryResponse]:
        """Retrieve all categories ordered by ID."""
        categories = self._category_repository.get_all_categories()
        return [CategoryResponse.model_validate(category) for category in categories]

    def get_category_by_id(self, category_id: int) -> CategoryResponse | None:
        """Retrieve a specific category by its ID."""
        category = self._category_repository.get_category_by_id(category_id)
        return CategoryResponse.model_validate(category) if category else None

    def get_category_by_name(self, name: str) -> CategoryResponse | None:
        """Retrieve a specific category by its name."""
        category = self._category_repository.get_category_by_name(name)
        return CategoryResponse.model_validate(category) if category else None

    def create_category(self, request: CategoryRequest) -> CategoryResponse:
        """Create a new category."""
        category = Category(
            name=request.name,
            is_default=False,
        )
        self._category_repository.create_category(category)
        return CategoryResponse.model_validate(category)

    def update_category(self, id: int, request: CategoryRequest) -> CategoryResponse:
        """Update an existing category."""
        category = self._category_repository.get_category_by_id(id)
        if not category:
            raise NotFoundError(_("Category %s not found") % id)
        category.name = request.name
        self._category_repository.update_category(category)
        return CategoryResponse.model_validate(category)

    def delete_category(self, id: int) -> None:
        """Delete a category by its ID."""
        return self._category_repository.delete_category(id)
