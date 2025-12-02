"""
Logging Configuration Setup 🪵

This module defines the logic for configuring Python's logging system based
on environment variables.
"""

import logging
import os
from collections.abc import Mapping

# Logging level mapping
log_levels: Mapping[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging() -> None:
    """
    Configure logging from environment variables.

    Uses two environment variables:
    - LOG_LEVEL: Controls root Python logging (all libraries). Default: WARNING
    - DIVVY_LOG_LEVEL: Controls only Divvy logging. If not set, inherits LOG_LEVEL.

    Also silences noisy third-party loggers (e.g., SQLAlchemy) to the WARNING level.
    """
    # 1. Determine Log Levels

    # Root log level (for all Python logging)
    root_level_str = os.getenv("LOG_LEVEL", "WARNING").upper()
    root_log_level = log_levels.get(root_level_str, logging.WARNING)

    # Divvy log level (inherits root if not set)
    divvy_level_str = os.getenv("DIVVY_LOG_LEVEL")
    divvy_log_level = root_log_level
    if divvy_level_str:
        divvy_log_level = log_levels.get(divvy_level_str.upper(), root_log_level)

    # 2. Configure Root Logger

    # Basic configuration applies to the root logger
    logging.basicConfig(
        level=root_log_level,
        format="%(message)s",
    )

    # 3. Configure Application Loggers (Specific formatting for our app logs)

    for logger_name in ["divvy", "app"]:
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(divvy_log_level)
        app_logger.propagate = False  # Critical: Stop propagation to root to prevent duplicates

        # Add StreamHandler only if the logger doesn't have one
        if not app_logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(divvy_log_level)
            # Use Uvicorn-style formatter for app logs to match FastAPI output
            formatter = logging.Formatter("%(levelname)-4s:     %(message)s")
            handler.setFormatter(formatter)
            app_logger.addHandler(handler)

    # 4. Silence Noisy Third-Party Loggers

    # Set noisy libraries to WARNING or higher to keep logs clean
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
