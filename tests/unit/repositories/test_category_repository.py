"""
Unit tests for CategoryRepository.
"""

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category
from app.repositories import CategoryRepository
from tests.fixtures.factories import create_test_category


@pytest.mark.unit
class TestCategoryRepository:
    """Test suite for CategoryRepository."""

    @pytest.fixture
    def category_repository(self, db_session: AsyncSession) -> CategoryRepository:
        return CategoryRepository(db_session)

    async def test_get_all_categories_empty(self, category_repository: CategoryRepository):
        """Test retrieving all categories when database is empty."""
        categories = await category_repository.get_all_categories()

        assert isinstance(categories, list)
        # Database starts empty (no default categories seeded in unit tests)
        # Default categories are seeded via Alembic migrations in production
        assert len(categories) == 0

    async def test_get_all_categories_ordered_by_id(
        self, category_repository: CategoryRepository, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test that categories are returned ordered by ID."""
        # Create additional categories
        await category_factory(name="Zebra Category")
        await category_factory(name="Alpha Category")

        categories = await category_repository.get_all_categories()
        category_ids = [cat.id for cat in categories]

        # Check that IDs are in ascending order
        assert category_ids == sorted(category_ids)

    async def test_get_category_by_id_exists(
        self, category_repository: CategoryRepository, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test retrieving a category by ID when it exists."""
        # Create a category
        category = await category_factory(name="Test Category")

        # Retrieve it
        retrieved = await category_repository.get_category_by_id(category.id)
        assert retrieved is not None
        assert retrieved.id == category.id
        assert retrieved.name == "Test Category"

    async def test_get_category_by_id_not_exists(self, category_repository: CategoryRepository):
        """Test retrieving a category by ID when it doesn't exist."""
        result = await category_repository.get_category_by_id(99999)
        assert result is None

    async def test_get_category_by_name_exists(
        self, category_repository: CategoryRepository, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test retrieving a category by name when it exists."""
        category = await category_factory(name="Unique Category Name")

        retrieved = await category_repository.get_category_by_name(category.name)

        assert retrieved is not None
        assert retrieved.name == category.name

    async def test_get_category_by_name_not_exists(self, category_repository: CategoryRepository):
        """Test retrieving a category by name when it doesn't exist."""
        result = await category_repository.get_category_by_name("Non-existent Category")
        assert result is None

    async def test_create_category(self, category_repository: CategoryRepository):
        """Test creating a new category."""
        category = create_test_category(name="New Category", is_default=False)
        created = await category_repository.create_category(category)

        assert created.id is not None
        assert created.name == "New Category"
        assert created.is_default is False

        # Verify it's in the database
        retrieved = await category_repository.get_category_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Category"

    async def test_update_category(
        self, category_repository: CategoryRepository, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test updating an existing category."""
        # Create a category
        category = await category_factory(name="Original Name")

        # Update it
        category.name = "Updated Name"

        updated = await category_repository.update_category(category)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await category_repository.get_category_by_id(category.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_delete_category_exists(
        self, category_repository: CategoryRepository, category_factory: Callable[..., Awaitable[Category]]
    ):
        """Test deleting a category that exists."""
        # Create a category
        category = await category_factory(name="To Delete")

        # Delete it
        await category_repository.delete_category(category.id)

        # Verify it's gone
        retrieved = await category_repository.get_category_by_id(category.id)
        assert retrieved is None

    async def test_delete_category_not_exists(self, category_repository: CategoryRepository):
        """Test deleting a category that doesn't exist (should not raise error)."""
        # Should not raise an exception
        await category_repository.delete_category(99999)
