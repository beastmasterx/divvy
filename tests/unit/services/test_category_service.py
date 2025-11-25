"""
Unit tests for CategoryService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.category import CategoryRequest
from app.services import CategoryService
from tests.fixtures.factories import create_test_category


@pytest.mark.unit
class TestCategoryService:
    """Test suite for CategoryService."""

    async def test_get_all_categories(self, db_session: AsyncSession):
        """Test retrieving all categories."""
        service = CategoryService(db_session)

        categories = await service.get_all_categories()
        assert isinstance(categories, list)
        # Database starts empty (no default categories seeded in unit tests)
        assert len(categories) == 0

    async def test_get_category_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a category by ID when it exists."""
        service = CategoryService(db_session)

        category = create_test_category(name="Test Category")
        db_session.add(category)
        await db_session.commit()

        retrieved = await service.get_category_by_id(category.id)
        assert retrieved is not None
        assert retrieved.id == category.id
        assert retrieved.name == "Test Category"

    async def test_get_category_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a category by ID when it doesn't exist."""
        service = CategoryService(db_session)
        result = await service.get_category_by_id(99999)
        assert result is None

    async def test_get_category_by_name_exists(self, db_session: AsyncSession):
        """Test retrieving a category by name when it exists."""
        service = CategoryService(db_session)

        category = create_test_category(name="Unique Category Name")
        db_session.add(category)
        await db_session.commit()

        retrieved = await service.get_category_by_name("Unique Category Name")
        assert retrieved is not None
        assert retrieved.name == "Unique Category Name"

    async def test_get_category_by_name_not_exists(self, db_session: AsyncSession):
        """Test retrieving a category by name when it doesn't exist."""
        service = CategoryService(db_session)
        result = await service.get_category_by_name("Non-existent Category")
        assert result is None

    async def test_create_category(self, db_session: AsyncSession):
        """Test creating a new category."""
        service = CategoryService(db_session)

        created = await service.create_category(CategoryRequest(name="New Category"))

        assert created.id is not None
        assert created.name == "New Category"
        assert created.is_default is False

        # Verify it's in the database
        retrieved = await service.get_category_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Category"

    async def test_update_category(self, db_session: AsyncSession):
        """Test updating an existing category."""
        service = CategoryService(db_session)

        # Create a category
        category = create_test_category(name="Original Name")
        db_session.add(category)
        await db_session.commit()

        # Update it
        updated = await service.update_category(category.id, CategoryRequest(name="Updated Name"))

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await service.get_category_by_id(category.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_delete_category(self, db_session: AsyncSession):
        """Test deleting a category."""
        service = CategoryService(db_session)

        # Create a category
        category = create_test_category(name="To Delete")
        db_session.add(category)
        await db_session.commit()
        category_id = category.id

        # Delete it
        await service.delete_category(category_id)

        # Verify it's gone
        retrieved = await service.get_category_by_id(category_id)
        assert retrieved is None
