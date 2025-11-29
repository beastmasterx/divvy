"""
FastAPI dependencies for dependency injection.

This module provides a unified interface for all dependencies.
Individual dependencies are organized in sub-packages:
- authn: Authentication dependencies (identity provision)
- authz: Authorization dependencies (permission enforcement)
- db: Database session dependencies
- services: Service dependencies

Common dependencies are re-exported here for convenience.
For advanced use cases, import directly from sub-packages:
    from app.api.dependencies.authz import requires_group_role
    from app.api.dependencies.services import get_user_service
"""

# Re-export most commonly used dependencies
from app.api.dependencies.authn import get_current_user
from app.api.dependencies.db import get_db

# Expose sub-packages for direct access
from . import authn, authz, db, services

__all__ = [
    # Common dependencies (re-exported for convenience)
    "get_current_user",
    "get_db",
    # Sub-packages (for direct access to all dependencies)
    "authn",
    "authz",
    "db",
    "services",
]
