"""
Database session dependencies.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    async with get_session() as session:
        yield session

