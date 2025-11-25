"""
Database connection factory supporting multiple database backends.
Supports SQLite, PostgreSQL, MySQL, and MSSQL with async SQLAlchemy.
"""

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Determine the absolute path to the project root and the database file
# From app/db/connection.py: go up 2 levels to reach project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "expenses.db")


def get_database_url() -> str:
    """
    Get async database connection URL from environment variable or default to SQLite.

    Expected async URL formats:
    - SQLite: sqlite+aiosqlite:///path/to/file.db
    - PostgreSQL: postgresql+asyncpg://user:password@host:port/database
    - MySQL: mysql+aiomysql://user:password@host:port/database
    - MSSQL: mssql+aioodbc://user:password@host:port/database?driver=...

    Returns:
        Async database connection URL string
    """
    database_url = os.getenv("DIVVY_DATABASE_URL")

    if database_url:
        return database_url

    # Default to async SQLite
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    return f"sqlite+aiosqlite:///{DB_FILE}"


def _create_engine_from_url(url: str | None = None) -> AsyncEngine:
    """
    Create async SQLAlchemy engine from database URL.

    Args:
        url: Database URL. If None, uses get_database_url() to determine URL.

    Returns:
        Async SQLAlchemy Engine instance

    Raises:
        ImportError: If required database driver is not installed
    """
    if url is None:
        url = get_database_url()

    print(url)

    # Create async engine with appropriate settings
    # For SQLite, use check_same_thread=False to allow connection sharing
    # For other databases, connection pooling is handled automatically
    connect_args = {}
    if url.startswith("sqlite+aiosqlite"):
        connect_args = {"check_same_thread": False}

    try:
        engine = create_async_engine(
            url,
            connect_args=connect_args,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )
        return engine
    except ImportError as e:
        # Provide helpful error messages for missing drivers
        error_msg = str(e).lower()
        if "postgresql" in url.lower() or "asyncpg" in error_msg:
            raise ImportError(
                "PostgreSQL async driver not installed.\n"
                "Install with: pip install asyncpg\n"
                "Or: pip install -e .[postgresql-async]"
            ) from e
        elif "mysql" in url.lower() or "aiomysql" in error_msg:
            raise ImportError(
                "MySQL async driver not installed.\n"
                "Install with: pip install aiomysql\n"
                "Or: pip install -e .[mysql-async]"
            ) from e
        elif "sqlite" in url.lower() or "aiosqlite" in error_msg:
            raise ImportError(
                "SQLite async driver not installed.\n"
                "Install with: pip install aiosqlite\n"
                "Or: pip install -e .[sqlite-async]"
            ) from e
        raise


# Global async engine instance (lazy initialization)
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async database engine instance.

    Returns:
        Async SQLAlchemy Engine instance
    """
    global _engine
    if _engine is None:
        _engine = _create_engine_from_url()
    return _engine


async def reset_engine() -> None:
    """
    Reset the global async engine (useful for testing or switching databases).

    Note: This is now async because AsyncEngine.dispose() is async.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
    _engine = None


_serializable_engine: AsyncEngine | None = None


def get_serializable_engine() -> AsyncEngine:
    """
    Get or create engine with SERIALIZABLE isolation level.

    Used for critical financial operations that require highest isolation.
    """
    global _serializable_engine
    if _serializable_engine is None:
        _serializable_engine = _create_engine_from_url().execution_options(isolation_level="SERIALIZABLE")
    return _serializable_engine


async def reset_serializable_engine() -> None:
    """
    Reset the global async engine with SERIALIZABLE isolation level.
    """
    global _serializable_engine
    if _serializable_engine is not None:
        await _serializable_engine.dispose()
    _serializable_engine = None
