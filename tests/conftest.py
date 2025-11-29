"""
Core pytest configuration and fixtures for testing.

Key features:
- Alembic migration support for test database
- Temporary file-based SQLite database for tests
- Automatic schema setup/teardown
- Test data factories
- Test-specific environment variables (no external .env files)
"""

import pytest

pytest_plugins = [
    "tests.fixtures.factories",
    "tests.fixtures.entities",
    "tests.fixtures.services",
    "tests.fixtures.database",
    "tests.fixtures.api",
]


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called at test session start."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(autouse=True)
def test_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Set test-specific environment variables.

    Tests should not depend on external .env files for isolation and reproducibility.
    This fixture automatically sets required environment variables for all tests.
    """
    # JWT Configuration (required - must be at least 32 characters)
    monkeypatch.setenv("DIVVY_JWT_SECRET_KEY", "2SZCrD1OkZ9mmzpXeCwITRiLiIblMFa96l4-jyArzRE")
    monkeypatch.setenv("DIVVY_STATE_TOKEN_SECRET_KEY", "2SZCrD1OkZ9mmzpXeCwITRiLiIblMFa96l4-jyArzRE")

    # Application URLs (with safe test defaults)
    monkeypatch.setenv("DIVVY_FRONTEND_URL", "http://localhost:3000")

    # Logging (suppress verbose logging in tests)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DIVVY_LOG_LEVEL", "WARNING")

    # Cleanup: restore original environment (monkeypatch handles this automatically)
    return
