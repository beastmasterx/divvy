"""
Database fixtures for testing.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.connection import reset_engine
from app.models import Base


@pytest.fixture
async def test_db_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """
    Create a temporary file-based SQLite async database engine with Alembic migrations applied.

    Each test gets a fresh database with the current schema from migrations.
    Uses pytest's tmp_path fixture for automatic cleanup.
    """
    # Create a temporary database file using pytest's tmp_path fixture
    db_path = tmp_path / "test.db"

    # Create async SQLite engine pointing to temporary file
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables using Base.metadata
    # This is faster for unit tests and ensures schema matches models
    # For integration tests that need to test migrations, use Alembic
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()
    # pytest's tmp_path automatically cleans up the directory and all files


@pytest.fixture(autouse=True)
async def mock_database_engine(
    test_db_engine: AsyncEngine,
) -> AsyncIterator[None]:
    """
    Mock the database engine to use the test in-memory database.
    This fixture runs automatically for all tests.
    """
    # Reset any existing engine (async)
    await reset_engine()

    # Create new async session factory with test engine
    test_session_local = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # Patch database connection functions
    with (
        patch("app.db.connection.get_engine", return_value=test_db_engine),
        patch("app.db.session.get_engine", return_value=test_db_engine),
        patch(
            "app.db.session._get_session_factory",
            return_value=test_session_local,
        ),
    ):
        yield

    # Reset after test
    await reset_engine()


@pytest.fixture
async def db_session(test_db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """
    Provide an async database session for tests.
    Automatically rolls back after each test.

    Note: This session uses the test_db_engine directly to ensure
    it sees the migrated schema.
    """
    # Create async session factory bound to the test engine
    session_local = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_local()

    try:
        yield session
        await session.rollback()
    finally:
        await session.close()
