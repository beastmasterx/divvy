"""
Configuration utilities for loading environment variables from .env files.
Supports environment-specific configuration files.
"""
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - provide a no-op function if not installed
    def load_dotenv(*args, **kwargs):
        pass

# Logging level mapping
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Module-level logger
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """
    Configure logging from environment variables.
    
    Uses two environment variables:
    - LOG_LEVEL: Controls root Python logging (all libraries). Default: WARNING
    - DIVVY_LOG_LEVEL: Controls only Divvy logging. If not set, inherits LOG_LEVEL.
    
    Silences noisy third-party loggers (SQLAlchemy, etc.) to WARNING level.
    """
    # Root log level (for all Python logging)
    root_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
    root_log_level = log_levels.get(root_level_str, logging.WARNING)
    
    # Divvy log level (inherits root if not set)
    divvy_level_str = os.getenv("DIVVY_LOG_LEVEL")
    if divvy_level_str:
        divvy_log_level = log_levels.get(divvy_level_str.upper(), root_log_level)
    else:
        divvy_log_level = root_log_level
    
    # Configure root logger
    logging.basicConfig(
        level=root_log_level,
        format="%(message)s",
    )
    
    # Configure Divvy loggers (support both 'divvy' and 'src.divvy' import styles)
    # This allows modules to use __name__ directly without normalization
    for logger_name in ["divvy", "src.divvy"]:
        divvy_logger = logging.getLogger(logger_name)
        divvy_logger.setLevel(divvy_log_level)
        divvy_logger.propagate = False  # Don't propagate to root logger to avoid duplicates
        
        # Add handler for Divvy logger
        if not divvy_logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(divvy_log_level)
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            divvy_logger.addHandler(handler)
    
    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)


def load_env_files(project_root: Path | None = None) -> None:
    """
    Load environment variables from .env files.
    
    Supports environment-specific files like .env.dev, .env.production, etc.
    Set DIVVY_ENV environment variable to specify the environment.
    Example: DIVVY_ENV=dev will load .env.dev
    
    Priority order (later files override earlier ones):
    1. Base .env file from project root
    2. Base .env file from current working directory (if different)
    3. Environment-specific .env.{ENV} file from project root
    4. Environment-specific .env.{ENV} file from current working directory (if different)
    5. Shell environment variables (always highest priority)
    
    After loading .env files, automatically sets up logging based on LOG_LEVEL
    and DIVVY_LOG_LEVEL environment variables, then logs the environment name
    and loaded configuration files.
    
    Args:
        project_root: Path to project root directory. If None, auto-detects from
                     the location of this file (3 levels up from src/divvy/config.py).
    """
    if project_root is None:
        # Auto-detect project root (3 levels up from src/divvy/config.py)
        project_root = Path(__file__).parent.parent.parent
    
    cwd = Path.cwd()
    
    # Determine environment from environment variable (before loading .env files)
    env_name = os.getenv("DIVVY_ENV")
    
    # Collect files to load (don't log yet - logging not configured)
    env_files_to_load = []
    
    # Base .env file from project root
    base_env = project_root / ".env"
    if base_env.exists():
        env_files_to_load.append(base_env)
    
    # Base .env file from current working directory
    cwd_base_env = cwd / ".env"
    if cwd_base_env.exists() and cwd_base_env != base_env:
        env_files_to_load.append(cwd_base_env)
    
    # Load environment-specific .env file (higher priority, overrides base)
    if env_name:
        env_specific = project_root / f".env.{env_name}"
        if env_specific.exists():
            env_files_to_load.append(env_specific)
        
        cwd_env_specific = cwd / f".env.{env_name}"
        if cwd_env_specific.exists() and cwd_env_specific != env_specific:
            env_files_to_load.append(cwd_env_specific)
    
    # Load all .env files in order (later files override earlier ones)
    # override=False ensures shell env vars always take precedence
    for env_file in env_files_to_load:
        load_dotenv(env_file, override=False)
    
    # Configure logging after .env files are loaded (so LOG_LEVEL and DIVVY_LOG_LEVEL are available)
    setup_logging()
    
    # Now log the environment and loaded files (logging is configured)
    # Log environment name (like ASP.NET Core)
    if env_name:
        logger.info(f"Environment: {env_name}")
    else:
        logger.info("Environment: (not set)")
    
    # Log loaded configuration files
    for env_file in env_files_to_load:
        if env_file == base_env:
            logger.info(f"Loaded base config: .env")
        else:
            logger.info(f"Loaded environment-specific config: {env_file.relative_to(project_root)}")

