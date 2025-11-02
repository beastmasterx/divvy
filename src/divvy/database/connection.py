"""
Database connection factory supporting multiple database backends.
Supports SQLite, PostgreSQL, MySQL, and MSSQL.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.exc import OperationalError

# Determine the absolute path to the project root and the database file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "data", "expenses.db")


def ensure_database_exists(database_url: str) -> None:
    """
    Ensure the database exists before connecting to it.
    Creates the database if it doesn't exist (for PostgreSQL, MySQL, MSSQL).
    SQLite databases are created automatically, so this is a no-op for SQLite.
    
    Args:
        database_url: Full database connection URL (string or URL object)
    """
    # Parse URL using SQLAlchemy's URL builder
    url = make_url(database_url)
    
    # SQLite databases are created automatically
    if url.drivername and "sqlite" in url.drivername.lower():
        return
    
    # No database name specified
    if not url.database:
        return
    
    database_name = url.database
    
    # Build admin connection URL using SQLAlchemy's URL builder
    # Connect to system/admin database to create the target database
    admin_url: URL | None = None
    
    if "mysql" in (url.drivername or "").lower():
        # For MySQL, connect to 'mysql' system database
        admin_url = url.set(database="mysql")
    elif "postgresql" in (url.drivername or "").lower():
        # For PostgreSQL, connect to 'postgres' system database
        admin_url = url.set(database="postgres")
    elif "mssql" in (url.drivername or "").lower():
        # For MSSQL, connect without database (uses default)
        admin_url = url.set(database=None)
    else:
        # Unknown database type, skip
        return
    
    if not admin_url:
        return
    
    try:
        # Connect to admin database and create target database if it doesn't exist
        if "postgresql" in (url.drivername or "").lower():
            # PostgreSQL: Need autocommit mode for CREATE DATABASE
            admin_engine = create_engine(admin_url, echo=False, isolation_level="AUTOCOMMIT")
        else:
            admin_engine = create_engine(admin_url, echo=False)
        
        with admin_engine.connect() as conn:
            if "mysql" in (url.drivername or "").lower():
                # MySQL: CREATE DATABASE IF NOT EXISTS
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}`"))
                conn.commit()
            elif "postgresql" in (url.drivername or "").lower():
                # PostgreSQL: Check if exists first, then create
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": database_name}
                )
                if not result.fetchone():
                    conn.execute(text(f'CREATE DATABASE "{database_name}"'))
            elif "mssql" in (url.drivername or "").lower():
                # MSSQL: CREATE DATABASE IF NOT EXISTS
                conn.execute(text(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{database_name}') CREATE DATABASE [{database_name}]"))
                conn.commit()
        admin_engine.dispose()
    except OperationalError:
        # Database already exists or insufficient permissions - continue anyway
        # The actual connection will fail later if there's a real problem
        pass
    except Exception:
        # Any other error - continue anyway, connection attempt will show proper error
        pass


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
        # Ensure database exists before returning URL
        ensure_database_exists(database_url)
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

