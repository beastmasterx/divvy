"""
Session management for SQLAlchemy.
Provides session context managers and session factory.
"""

from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from . import audit  # noqa: F401 - Import side effect registers SQLAlchemy events
from .connection import get_engine

# Lazy session factory - only creates engine when first used
# This allows .env files to be loaded before engine creation
_session_local = None


def _get_session_factory():
    """Get or create the session factory (lazy initialization)."""
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(), autocommit=False, autoflush=False
        )
    return _session_local


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
