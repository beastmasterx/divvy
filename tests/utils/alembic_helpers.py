"""
Utilities for working with Alembic migrations in tests.
"""

import asyncio
from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from app.models import Base


def _do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given sync connection (called from async context)."""
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations(engine: AsyncEngine, alembic_cfg: Config) -> None:
    """Run migrations with async engine."""
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)


async def _downgrade_async_migrations(engine: AsyncEngine, alembic_cfg: Config, revision: str) -> None:
    """Downgrade migrations with async engine."""

    def _do_downgrade(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations(downgrade=True)
            # Get the current revision and downgrade to target
            from alembic import command

            command.downgrade(alembic_cfg, revision)

    async with engine.connect() as connection:
        await connection.run_sync(_do_downgrade)


def run_migrations(engine: AsyncEngine, alembic_ini_path: Path | None = None) -> None:
    """
    Run Alembic migrations on the given async engine.

    Args:
        engine: SQLAlchemy async engine to run migrations on
        alembic_ini_path: Path to alembic.ini (defaults to project root)
    """
    if alembic_ini_path is None:
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini_path))
    # Set the target metadata (required for Alembic)
    alembic_cfg.attributes["target_metadata"] = Base.metadata
    # Override the database URL to use our test engine's URL
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    # Set config in context for migration functions
    context.config = alembic_cfg

    # Run async migrations
    asyncio.run(_run_async_migrations(engine, alembic_cfg))


def downgrade_migrations(engine: AsyncEngine, revision: str = "base", alembic_ini_path: Path | None = None) -> None:
    """
    Downgrade Alembic migrations on the given async engine.

    Args:
        engine: SQLAlchemy async engine to run migrations on
        revision: Target revision (default: "base" for all)
        alembic_ini_path: Path to alembic.ini (defaults to project root)
    """
    if alembic_ini_path is None:
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    alembic_cfg.attributes["target_metadata"] = Base.metadata

    # Set config in context for migration functions
    context.config = alembic_cfg

    # Run async downgrade
    asyncio.run(_downgrade_async_migrations(engine, alembic_cfg, revision))
