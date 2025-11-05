"""
FastAPI dependencies for dependency injection.
Provides common dependencies like database sessions, authentication, etc.
"""
from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    with get_session() as session:
        yield session


# Example: Add authentication dependency when needed
# def get_current_user(db: Session = Depends(get_db)) -> User:
#     """Get current authenticated user."""
#     ...

