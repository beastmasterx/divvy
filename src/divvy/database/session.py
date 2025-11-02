"""
Session management for SQLAlchemy.
Provides session context managers and session factory.
"""
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from .connection import get_engine

# Create session factory
SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


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
    session = SessionLocal()
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
    return SessionLocal()

