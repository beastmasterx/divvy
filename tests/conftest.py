"""
Pytest configuration and shared fixtures for database tests.
Provides SQLAlchemy-based test database setup.
"""
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import load_env_files
from app.db import Base, Member, Period, Category, PUBLIC_FUND_MEMBER_INTERNAL_NAME
from app.db.connection import reset_engine

# Load .env files before tests run
# This ensures DIVVY_LANG and other config from .env files are available during tests
_load_env_called = False

def pytest_configure(config):
    """Pytest hook called at test session start."""
    global _load_env_called
    if not _load_env_called:
        # Load .env files from project root
        project_root = Path(__file__).parent.parent
        load_env_files(project_root=project_root)
        _load_env_called = True


@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create an in-memory SQLite database engine for testing.
    Each test gets a fresh database.
    """
    # Create in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Pre-populate default categories
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    default_categories = [
        "Utilities (Water & Electricity & Gas)",
        "Groceries",
        "Daily Necessities",
        "Rent",
        "Other",
    ]
    
    for cat_name in default_categories:
        if not session.query(Category).filter_by(name=cat_name).first():
            session.add(Category(name=cat_name))
    
    # Ensure there's an initial period
    if not session.query(Period).filter_by(is_settled=False).first():
        session.add(Period(name="Initial Period", is_settled=False))
    
    # Ensure public fund member exists
    if not session.query(Member).filter_by(name=PUBLIC_FUND_MEMBER_INTERNAL_NAME).first():
        session.add(Member(
            email=f"{PUBLIC_FUND_MEMBER_INTERNAL_NAME}@system.local",
            name=PUBLIC_FUND_MEMBER_INTERNAL_NAME,
            is_active=False
        ))
    
    session.commit()
    session.close()
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def mock_database_engine(test_db_engine):
    """
    Mock the database engine to use the test in-memory database.
    This fixture runs automatically for all tests.
    """
    from sqlalchemy.orm import sessionmaker
    
    # Reset any existing engine
    reset_engine()
    
    # Create new session factory with test engine
    TestSessionLocal = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)
    
    # Patch get_engine to return our test engine
    with patch("app.db.connection.get_engine", return_value=test_db_engine):
        with patch("app.db.session.get_engine", return_value=test_db_engine):
            with patch("app.db.get_engine", return_value=test_db_engine):
                # Patch _get_session_factory to return our test session factory
                with patch("app.db.session._get_session_factory", return_value=TestSessionLocal):
                    # Reset the module-level _SessionLocal to force reinitialization
                    import app.db.session as session_module
                    session_module._SessionLocal = None
                    yield
    
    # Reset after test
    reset_engine()

