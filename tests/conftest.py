"""
Core pytest configuration and fixtures for testing.

Key features:
- Alembic migration support for test database
- Temporary file-based SQLite database for tests
- Automatic schema setup/teardown
- Test data factories
- Test-specific environment variables (no external .env files)
"""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.connection import reset_engine
from app.models import Base


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called at test session start."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


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
def test_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set test-specific environment variables.

    Tests should not depend on external .env files for isolation and reproducibility.
    This fixture automatically sets required environment variables for all tests.
    """
    # JWT Configuration (required - must be at least 32 characters)
    monkeypatch.setenv("DIVVY_JWT_SECRET_KEY", "2SZCrD1OkZ9mmzpXeCwITRiLiIblMFa96l4-jyArzRE")

    # Application URLs (with safe test defaults)
    monkeypatch.setenv("DIVVY_FRONTEND_URL", "http://localhost:3000")

    # Logging (suppress verbose logging in tests)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DIVVY_LOG_LEVEL", "WARNING")

    # Cleanup: restore original environment (monkeypatch handles this automatically)
    return


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
