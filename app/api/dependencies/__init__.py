"""
FastAPI dependencies for dependency injection.

This module provides a unified interface for all dependencies.
Individual dependencies are organized in submodules:
- db: Database session dependencies
- services: Service dependencies
- auth: Authentication dependencies
"""
from app.api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
)
from app.api.dependencies.db import get_db
from app.api.dependencies.services import (
    get_auth_service,
    get_category_service,
    get_group_service,
    get_identity_provider_service,
    get_period_service,
    get_settlement_service,
    get_transaction_service,
    get_user_service,
)

__all__ = [
    # Database
    "get_db",
    # Services
    "get_user_service",
    "get_auth_service",
    "get_category_service",
    "get_period_service",
    "get_transaction_service",
    "get_group_service",
    "get_settlement_service",
    "get_identity_provider_service",
    # Auth
    "get_current_user",
    "get_current_user_optional",
]

