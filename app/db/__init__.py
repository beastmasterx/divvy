"""
Database module for Divvy application.
Refactored to use SQLAlchemy ORM while maintaining backwards compatibility.
Supports SQLite, PostgreSQL, MySQL, and MSSQL via environment variable DIVVY_DATABASE_URL.
"""

import logging

from app.db.connection import get_engine
from app.db.session import get_session
from app.models import Base, Category

logger = logging.getLogger(__name__)


def initialize_database():
    """
    Initializes the database by creating tables.
    Uses SQLAlchemy to create tables, which works across all database types.
    """
    engine = get_engine()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Pre-populate default categories
    with get_session() as session:
        default_categories = [
            "Utilities (Water & Electricity & Gas)",
            "Groceries",
            "Daily Necessities",
            "Rent",
            "Other",
        ]

        for cat_name in default_categories:
            # Check if category already exists
            existing = session.query(Category).filter_by(name=cat_name).first()
            if not existing:
                session.add(Category(name=cat_name))
        session.commit()

    logger.info("Database initialized successfully.")
