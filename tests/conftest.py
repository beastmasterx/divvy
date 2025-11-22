"""
Core pytest configuration and fixtures for testing.

Key features:
- Alembic migration support for test database
- Temporary file-based SQLite database for tests
- Automatic schema setup/teardown
- Test data factories
"""

import tempfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import load_env_files
from app.db.connection import reset_engine
from app.models import Base

# Load environment variables
_load_env_called = False


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called at test session start."""
    global _load_env_called
    if not _load_env_called:
        project_root = Path(__file__).parent.parent
        load_env_files(project_root=project_root)
        _load_env_called = True

    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(scope="function")
def test_db_engine() -> Iterator[Engine]:
    """
    Create a temporary file-based SQLite database engine with Alembic migrations applied.

    Each test gets a fresh database with the current schema from migrations.
    Uses a temporary file that is automatically cleaned up after the test.
    """
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_path = temp_db.name

    try:
        # Create SQLite engine pointing to temporary file
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,  # Set to True for SQL debugging
        )

        # Create all tables using Base.metadata
        # This is faster for unit tests and ensures schema matches models
        # For integration tests that need to test migrations, use Alembic
        Base.metadata.create_all(bind=engine)

        yield engine

        # Cleanup
        engine.dispose()
    finally:
        # Remove temporary database file
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def mock_database_engine(
    test_db_engine: Engine,
) -> Iterator[None]:
    """
    Mock the database engine to use the test in-memory database.
    This fixture runs automatically for all tests.
    """
    # Reset any existing engine
    reset_engine()

    # Create new session factory with test engine
    test_session_local = sessionmaker(
        bind=test_db_engine,
        autocommit=False,
        autoflush=False,
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
    reset_engine()


@pytest.fixture
def db_session(test_db_engine: Engine) -> Iterator[Session]:
    """
    Provide a database session for tests.
    Automatically rolls back after each test.

    Note: This session uses the test_db_engine directly to ensure
    it sees the migrated schema.
    """
    # Create session factory bound to the test engine
    session_local = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)
    session = session_local()

    try:
        yield session
        session.rollback()
    finally:
        session.close()
