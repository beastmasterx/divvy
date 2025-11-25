"""
Session management for SQLAlchemy.
Provides async session context managers and session factory.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from . import (
    audit,  # noqa: F401  # pyright: ignore[reportUnusedImport]  # Import side effect registers SQLAlchemy event listeners
)
from .connection import get_engine, get_serializable_engine

# Lazy async session factory - only creates engine when first used
# This allows .env files to be loaded before engine creation
_session_local: async_sessionmaker[AsyncSession] | None = None


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory (lazy initialization)."""
    global _session_local
    if _session_local is None:
        _session_local = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Important for async - prevents lazy loading issues
        )
    return _session_local


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Async context manager for database sessions.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            # Session commits automatically on success
            # Rolls back on exception
    """
    async_session = _get_session_factory()()
    try:
        yield async_session
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    finally:
        await async_session.close()


async def create_session() -> AsyncSession:
    """
    Create a new async database session (manual management).

    Note: You must call await session.commit() and await session.close() manually.
    Prefer using get_session() context manager for automatic management.

    Returns:
        Async SQLAlchemy Session instance
    """
    return _get_session_factory()()


_serializable_session_local: async_sessionmaker[AsyncSession] | None = None


def _get_serializable_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory with SERIALIZABLE isolation level (lazy initialization)."""
    global _serializable_session_local
    if _serializable_session_local is None:
        _serializable_session_local = async_sessionmaker(
            bind=get_serializable_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _serializable_session_local


@asynccontextmanager
async def get_serializable_session() -> AsyncIterator[AsyncSession]:
    """
    Async context manager for database sessions with SERIALIZABLE isolation level.
    """
    async_session = _get_serializable_session_factory()()
    try:
        yield async_session
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    finally:
        await async_session.close()


async def create_serializable_session() -> AsyncSession:
    """
    Create a new async database session with SERIALIZABLE isolation level (manual management).
    """
    return _get_serializable_session_factory()()
