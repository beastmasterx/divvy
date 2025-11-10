"""
Session management for SQLAlchemy.
Provides session context managers and session factory.
"""

from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from .connection import get_engine

# Lazy session factory - only creates engine when first used
# This allows .env files to be loaded before engine creation
_SessionLocal = None


def _get_session_factory():
    """Get or create the session factory (lazy initialization)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)
    return _SessionLocal


# For backwards compatibility, expose SessionLocal as a callable
def SessionLocal():
    """Create a new session using the lazy-initialized factory."""
    return _get_session_factory()()


@contextmanager
def get_session():
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            member = session.query(Member).first()
            # Session commits automatically on success
            # Rolls back on exception
    """
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_session() -> Session:
    """
    Create a new database session (manual management).

    Note: You must call session.commit() and session.close() manually.
    Prefer using get_session() context manager for automatic management.

    Returns:
        SQLAlchemy Session instance
    """
    return _get_session_factory()()
