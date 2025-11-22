"""
Utilities for working with Alembic migrations in tests.
"""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine

from alembic import command


def run_migrations(engine: Engine, alembic_ini_path: Path | None = None) -> None:
    """
    Run Alembic migrations on the given engine.

    Args:
        engine: SQLAlchemy engine to run migrations on
        alembic_ini_path: Path to alembic.ini (defaults to project root)
    """
    if alembic_ini_path is None:
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini_path))
    # Set the target metadata (required for Alembic)
    from app.models import Base

    alembic_cfg.attributes["target_metadata"] = Base.metadata
    # Override the database URL to use our test engine's URL
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    # Apply migrations using the engine's connection
    # Use begin() to ensure transaction is committed
    connection = engine.connect()
    try:
        alembic_cfg.attributes["connection"] = connection
        with connection.begin():
            command.upgrade(alembic_cfg, "head")
    finally:
        connection.close()


def downgrade_migrations(engine: Engine, revision: str = "base", alembic_ini_path: Path | None = None) -> None:
    """
    Downgrade Alembic migrations on the given engine.

    Args:
        engine: SQLAlchemy engine to run migrations on
        revision: Target revision (default: "base" for all)
        alembic_ini_path: Path to alembic.ini (defaults to project root)
    """
    if alembic_ini_path is None:
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    with engine.connect() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.downgrade(alembic_cfg, revision)
