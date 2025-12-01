"""
Database fixtures for testing.
"""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db import reset_engine, reset_serializable_engine
from app.models import Base


@pytest.fixture
def test_database_url(tmp_path: Path) -> str:
    """
    Provide the database URL for the test database.

    This fixture centralizes the database URL construction to ensure consistency
    across all test database engines. Both test_db_engine and test_serializable_db_engine
    use the same database file for schema consistency.
    """
    db_path = tmp_path / "test.db"
    return f"sqlite+aiosqlite:///{db_path}"


@pytest.fixture
async def test_db_engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    """
    Create a temporary file-based SQLite async database engine with Alembic migrations applied.

    Each test gets a fresh database with the current schema from migrations.
    Uses pytest's tmp_path fixture for automatic cleanup.
    """
    # Create async SQLite engine pointing to temporary file
    engine = create_async_engine(
        test_database_url,
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


@pytest.fixture
async def test_serializable_db_engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    """
    Create a temporary file-based SQLite async database engine with SERIALIZABLE isolation level.

    Uses the same database file as test_db_engine to ensure schema consistency.
    This engine is used for testing critical financial operations that require highest isolation.
    """
    # Create async SQLite engine with SERIALIZABLE isolation level
    engine = create_async_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    ).execution_options(isolation_level="SERIALIZABLE")

    # Note: Tables are already created by test_db_engine fixture
    # Both engines share the same database file

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(autouse=True)
async def mock_database_engine(test_db_engine: AsyncEngine) -> AsyncIterator[None]:
    """
    Mock the regular database engine to use the test database.

    This fixture runs automatically for all tests and ensures regular operations
    use test_db_engine instead of the production database.
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

    # Patch database connection functions for regular engine
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


@pytest.fixture(autouse=True)
async def mock_serializable_database_engine(
    test_serializable_db_engine: AsyncEngine,
) -> AsyncIterator[None]:
    """
    Mock the serializable database engine to use the test database.

    This fixture runs automatically for all tests and ensures serializable operations
    use test_serializable_db_engine (with SERIALIZABLE isolation) instead of the production database.
    """
    # Reset any existing serializable engine (async)
    await reset_serializable_engine()

    # Create serializable session factory with serializable engine
    test_serializable_session_local = async_sessionmaker(
        bind=test_serializable_db_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # Patch database connection functions for serializable engine
    with (
        patch("app.db.connection.get_serializable_engine", return_value=test_serializable_db_engine),
        patch("app.db.session.get_serializable_engine", return_value=test_serializable_db_engine),
        patch(
            "app.db.session._get_serializable_session_factory",
            return_value=test_serializable_session_local,
        ),
    ):
        yield

    # Reset after test
    await reset_serializable_engine()


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


@pytest.fixture
async def db_serializable_session(test_serializable_db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """
    Provide an async database session with SERIALIZABLE isolation level for tests.
    Automatically rolls back after each test.

    Use this fixture when testing critical financial operations that require
    highest isolation level, such as settlement plan application.

    Note: This session uses the test_serializable_db_engine directly to ensure
    it sees the migrated schema and uses SERIALIZABLE isolation.
    """
    # Create async session factory bound to the serializable test engine
    session_local = async_sessionmaker(
        bind=test_serializable_db_engine,
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
