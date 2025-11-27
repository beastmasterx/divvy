"""
Unit tests for CategoryService.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category
from app.schemas.category import CategoryRequest
from app.services import CategoryService


@pytest.mark.unit
class TestCategoryService:
    """Test suite for CategoryService."""

    @pytest.fixture
    def category_service(self, db_session: AsyncSession) -> CategoryService:
        return CategoryService(db_session)

    async def test_get_all_categories(self, category_service: CategoryService):
        """Test retrieving all categories."""
        categories = await category_service.get_all_categories()

        assert isinstance(categories, list)
        # Database starts empty (no default categories seeded in unit tests)
        assert len(categories) == 0

    async def test_get_category_by_id_exists(
        self, category_service: CategoryService, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test retrieving a category by ID when it exists."""
        category = await category_factory(name="Test Category")

        retrieved = await category_service.get_category_by_id(category.id)

        assert retrieved is not None
        assert retrieved.id == category.id
        assert retrieved.name == "Test Category"

    async def test_get_category_by_id_not_exists(self, category_service: CategoryService):
        """Test retrieving a category by ID when it doesn't exist."""
        result = await category_service.get_category_by_id(99999)

        assert result is None

    async def test_get_category_by_name_exists(
        self, category_service: CategoryService, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test retrieving a category by name when it exists."""
        category = await category_factory(name="Unique Category Name")

        retrieved = await category_service.get_category_by_name(category.name)

        assert retrieved is not None
        assert retrieved.name == "Unique Category Name"

    async def test_get_category_by_name_not_exists(self, category_service: CategoryService):
        """Test retrieving a category by name when it doesn't exist."""
        result = await category_service.get_category_by_name("Non-existent Category")

        assert result is None

    async def test_create_category(self, category_service: CategoryService):
        """Test creating a new category."""

        created = await category_service.create_category(CategoryRequest(name="New Category"))

        assert created.id is not None
        assert created.name == "New Category"
        assert created.is_default is False

        # Verify it's in the database
        retrieved = await category_service.get_category_by_id(created.id)

        assert retrieved is not None
        assert retrieved.name == "New Category"

    async def test_update_category(
        self, category_service: CategoryService, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test updating an existing category."""
        category = await category_factory(name="Original Name")

        # Update it
        updated = await category_service.update_category(category.id, CategoryRequest(name="Updated Name"))

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await category_service.get_category_by_id(category.id)

        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_delete_category(
        self, category_service: CategoryService, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test deleting a category."""
        category = await category_factory(name="To Delete")

        category_id = category.id

        # Delete it
        await category_service.delete_category(category_id)

        # Verify it's gone
        retrieved = await category_service.get_category_by_id(category_id)

        assert retrieved is None

    async def test_delete_category_not_exists(self, category_service: CategoryService):
        """Test deleting a category that doesn't exist."""
        await category_service.delete_category(99999)
