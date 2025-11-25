"""
Database session dependencies.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_serializable_session, get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_session() as session:
        yield session


async def get_serializable_db() -> AsyncIterator[AsyncSession]:
    """
    Dependency that provides a database session with SERIALIZABLE isolation level.
    Automatically closes the session after the request.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_serializable_db)):
            # This session will use SERIALIZABLE isolation level
            ...
    """
    async with get_serializable_session() as session:
        yield session
