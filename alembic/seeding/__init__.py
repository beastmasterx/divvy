"""
Database seeding functions for Alembic migrations.
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from app.models.default import categories


def seed_categories() -> None:
    """Seed default categories into the database."""
    categories_table = sa.table(
        "categories",
        sa.column("name", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        categories_table,
        [
            {
                "name": cat_name,
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            }
            for cat_name in categories
        ],
    )
