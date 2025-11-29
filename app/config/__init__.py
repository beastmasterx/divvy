"""
Configuration Initialization and Loading 🛠️

This module serves as the entry point for the application's configuration.
It manages loading environment variables from .env files, setting up logging,
and re-exporting all specific configuration getters for clean access.
"""

import os
from logging import Logger, getLogger
from pathlib import Path

from dotenv import load_dotenv

# Import settings helpers from sub-modules
from .app import get_frontend_url, get_google_redirect_uri, get_microsoft_redirect_uri
from .auth import (
    get_access_token_expire_delta,
    get_access_token_secret_key,
    get_account_link_request_expiration_delta,
    get_core_jwt_secret_key,
    get_google_client_id,
    get_google_client_secret,
    get_jwt_algorithm,
    get_microsoft_client_id,
    get_microsoft_client_secret,
    get_microsoft_tenant_id,
    get_refresh_token_expire_delta,
    get_refresh_token_secret_key,
    get_state_token_algorithm,
    get_state_token_expire_delta,
    get_state_token_secret_key,
)
from .log import setup_logging

# Module-level logger (used before or during main app logging setup)
logger: Logger = getLogger(__name__)


def load_env_files(project_root: Path | None = None) -> None:
    """
    Load environment variables from .env files and configure logging.

    This function should be called once at application startup.

    Priority order (later files override earlier ones):
    1. Base .env file from project root
    2. Environment-specific .env.{ENV} file from project root
    3. Shell environment variables (always highest priority)

    Args:
        project_root: Path to project root directory. If None, auto-detects.
    """
    if project_root is None:
        # Auto-detect project root (2 levels up from app/config/__init__.py)
        project_root = Path(__file__).parent.parent.parent

    cwd = Path.cwd()

    # Determine environment from environment variable (before loading .env files)
    env_name = os.getenv("DIVVY_ENV")

    env_files_to_load: list[Path] = []

    # 1. Base .env file from project root
    base_env = project_root / ".env"
    if base_env.exists():
        env_files_to_load.append(base_env)

    # 2. Environment-specific .env file from project root (if set)
    if env_name:
        env_specific = project_root / f".env.{env_name}"
        if env_specific.exists():
            env_files_to_load.append(env_specific)

    # 3. Handle base .env file from current working directory (if different)
    cwd_base_env = cwd / ".env"
    if cwd_base_env.exists() and cwd_base_env not in env_files_to_load:
        env_files_to_load.append(cwd_base_env)

    # Load all .env files in order (later files override earlier ones)
    # override=False ensures shell env vars take precedence over .env file contents
    for env_file in env_files_to_load:
        load_dotenv(env_file, override=False)

    # Configure logging after .env files are loaded (so LOG_LEVEL is available)
    setup_logging()

    # Log loaded configuration files
    if env_name:
        logger.info(f"Environment: {env_name}")
    else:
        logger.info("Environment: (not set)")

    for env_file in env_files_to_load:
        # Use relative path if possible for cleaner logging
        try:
            log_path = env_file.relative_to(project_root)
        except ValueError:
            log_path = env_file.name

        logger.info(f"Loaded config: {log_path}")


# --- Re-export all necessary configuration getters for simple consumption ---
# This list is the public interface for configuration.

__all__ = [
    # Initialization
    "load_env_files",
    # Core JWT (Access/Refresh Tokens)
    "get_jwt_algorithm",
    "get_core_jwt_secret_key",
    "get_access_token_secret_key",
    "get_refresh_token_secret_key",
    "get_access_token_expire_delta",
    "get_refresh_token_expire_delta",
    # State Token (OAuth Flow Security)
    "get_state_token_algorithm",
    "get_state_token_secret_key",
    "get_state_token_expire_delta",
    # Other Auth / Account Management
    "get_account_link_request_expiration_delta",
    # Application Configuration (URLs)
    "get_frontend_url",
    "get_google_redirect_uri",
    "get_microsoft_redirect_uri",
    # Identity Providers (Credentials)
    "get_google_client_id",
    "get_google_client_secret",
    "get_microsoft_client_id",
    "get_microsoft_client_secret",
    "get_microsoft_tenant_id",
]
