"""
Unit tests for CategoryRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CategoryRepository
from tests.fixtures.factories import create_test_category


@pytest.mark.unit
class TestCategoryRepository:
    """Test suite for CategoryRepository."""

    async def test_get_all_categories_empty(self, db_session: AsyncSession):
        """Test retrieving all categories when database is empty."""
        repo = CategoryRepository(db_session)
        categories = await repo.get_all_categories()
        assert isinstance(categories, list)
        # Database starts empty (no default categories seeded in unit tests)
        # Default categories are seeded via Alembic migrations in production
        assert len(categories) == 0

    async def test_get_all_categories_ordered_by_id(self, db_session: AsyncSession):
        """Test that categories are returned ordered by ID."""
        repo = CategoryRepository(db_session)

        # Create additional categories
        cat1 = create_test_category(name="Zebra Category")
        cat2 = create_test_category(name="Alpha Category")
        db_session.add(cat1)
        db_session.add(cat2)
        await db_session.commit()

        categories = await repo.get_all_categories()
        category_ids = [cat.id for cat in categories]

        # Check that IDs are in ascending order
        assert category_ids == sorted(category_ids)

    async def test_get_category_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a category by ID when it exists."""
        repo = CategoryRepository(db_session)

        # Create a category
        category = create_test_category(name="Test Category")
        db_session.add(category)
        await db_session.commit()
        category_id = category.id

        # Retrieve it
        retrieved = await repo.get_category_by_id(category_id)
        assert retrieved is not None
        assert retrieved.id == category_id
        assert retrieved.name == "Test Category"

    async def test_get_category_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a category by ID when it doesn't exist."""
        repo = CategoryRepository(db_session)
        result = await repo.get_category_by_id(99999)
        assert result is None

    async def test_get_category_by_name_exists(self, db_session: AsyncSession):
        """Test retrieving a category by name when it exists."""
        repo = CategoryRepository(db_session)

        category = create_test_category(name="Unique Category Name")
        db_session.add(category)
        await db_session.commit()

        retrieved = await repo.get_category_by_name("Unique Category Name")
        assert retrieved is not None
        assert retrieved.name == "Unique Category Name"

    async def test_get_category_by_name_not_exists(self, db_session: AsyncSession):
        """Test retrieving a category by name when it doesn't exist."""
        repo = CategoryRepository(db_session)
        result = await repo.get_category_by_name("Non-existent Category")
        assert result is None

    async def test_create_category(self, db_session: AsyncSession):
        """Test creating a new category."""
        repo = CategoryRepository(db_session)

        category = create_test_category(name="New Category", is_default=False)
        created = await repo.create_category(category)

        assert created.id is not None
        assert created.name == "New Category"
        assert created.is_default is False

        # Verify it's in the database
        retrieved = await repo.get_category_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Category"

    async def test_update_category(self, db_session: AsyncSession):
        """Test updating an existing category."""
        repo = CategoryRepository(db_session)

        # Create a category
        category = create_test_category(name="Original Name")
        db_session.add(category)
        await db_session.commit()

        # Update it
        category.name = "Updated Name"
        updated = await repo.update_category(category)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await repo.get_category_by_id(category.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_delete_category_exists(self, db_session: AsyncSession):
        """Test deleting a category that exists."""
        repo = CategoryRepository(db_session)

        # Create a category
        category = create_test_category(name="To Delete")
        db_session.add(category)
        await db_session.commit()
        category_id = category.id

        # Delete it
        await repo.delete_category(category_id)

        # Verify it's gone
        retrieved = await repo.get_category_by_id(category_id)
        assert retrieved is None

    async def test_delete_category_not_exists(self, db_session: AsyncSession):
        """Test deleting a category that doesn't exist (should not raise error)."""
        repo = CategoryRepository(db_session)
        # Should not raise an exception
        await repo.delete_category(99999)
