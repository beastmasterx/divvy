"""
Pytest configuration and shared fixtures for database tests.
Provides SQLAlchemy-based test database setup.
"""
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.divvy.database import Base, Member, Period, Category, PUBLIC_FUND_MEMBER_INTERNAL_NAME
from src.divvy.database.connection import reset_engine


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
        session.add(Member(name=PUBLIC_FUND_MEMBER_INTERNAL_NAME, is_active=False))
    
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
    with patch("src.divvy.database.connection.get_engine", return_value=test_db_engine):
        with patch("src.divvy.database.session.get_engine", return_value=test_db_engine):
            with patch("src.divvy.database.get_engine", return_value=test_db_engine):
                # Patch _get_session_factory to return our test session factory
                with patch("src.divvy.database.session._get_session_factory", return_value=TestSessionLocal):
                    # Reset the module-level _SessionLocal to force reinitialization
                    import src.divvy.database.session as session_module
                    session_module._SessionLocal = None
                    yield
    
    # Reset after test
    reset_engine()

