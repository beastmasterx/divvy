"""
Database seeding functions for Alembic migrations.
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from app.models.default import categories, role_permissions


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


def seed_role_permissions() -> None:
    """Seed default role-permission mappings into the database."""
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role", sa.String),
        sa.column("permission", sa.String),
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "role": role,
                "permission": permission,
            }
            for role, permission in role_permissions
        ],
    )
