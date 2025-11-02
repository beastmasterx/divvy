"""
Database connection factory supporting multiple database backends.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Determine the absolute path to the project root and the database file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "expenses.db")


def get_database_url() -> str:
    """
    Get database connection URL from environment variable or default to SQLite.
    
    Supported formats:
    - SQLite: sqlite:///path/to/file.db
    - PostgreSQL: postgresql://user:password@host:port/database
    - MySQL: mysql://user:password@host:port/database
    - MSSQL: mssql+pyodbc://user:password@host:port/database?driver=ODBC+Driver+17+for+SQL+Server
    
    Returns:
        Database connection URL string
    """
    database_url = os.getenv("DIVVY_DATABASE_URL")
    
    if database_url:
        return database_url
    
    # Default to SQLite
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    return f"sqlite:///{DB_FILE}"


def create_engine_from_url(url: str | None = None) -> Engine:
    """
    Create SQLAlchemy engine from database URL.
    
    Args:
        url: Database URL. If None, uses get_database_url() to determine URL.
    
    Returns:
        SQLAlchemy Engine instance
    
    Raises:
        ImportError: If required database driver is not installed
    """
    if url is None:
        url = get_database_url()
    
    # Create engine with appropriate settings
    # For SQLite, use check_same_thread=False to allow connection sharing
    # For other databases, connection pooling is handled automatically
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    
    try:
        engine = create_engine(
            url,
            connect_args=connect_args,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
        )
        return engine
    except ImportError as e:
        # Provide helpful error messages for missing drivers
        error_msg = str(e).lower()
        if "postgresql" in url.lower() or "psycopg" in error_msg:
            raise ImportError(
                "PostgreSQL driver not installed.\n"
                "Install with: pip install -e .[postgresql]\n"
                "Or: pip install psycopg2-binary"
            ) from e
        elif "mysql" in url.lower() or "pymysql" in error_msg:
            raise ImportError(
                "MySQL driver not installed.\n"
                "Install with: pip install -e .[mysql]\n"
                "Or: pip install pymysql"
            ) from e
        elif "mssql" in url.lower() or "pyodbc" in error_msg:
            raise ImportError(
                "MSSQL driver not installed.\n"
                "Install with: pip install -e .[mssql]\n"
                "Or: pip install pyodbc"
            ) from e
        raise


# Global engine instance (lazy initialization)
_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Get or create the global database engine instance.
    
    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    if _engine is None:
        _engine = create_engine_from_url()
    return _engine


def reset_engine():
    """Reset the global engine (useful for testing or switching databases)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None

