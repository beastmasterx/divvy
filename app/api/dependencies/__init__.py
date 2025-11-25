"""
FastAPI dependencies for dependency injection.

This module provides a unified interface for all dependencies.
Individual dependencies are organized in submodules:
- db: Database session dependencies
- services: Service dependencies
- auth: Authentication dependencies
- authorization: Authorization and permission dependencies
"""

from app.api.dependencies.authentication import (
    get_current_user,
    get_current_user_optional,
)
from app.api.dependencies.authorization import (
    require_all_permissions,
    require_any_permission,
    require_permission,
    require_permission_in_group,
)
from app.api.dependencies.db import get_db
from app.api.dependencies.services import (
    get_authentication_service,
    get_authorization_service,
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
    "get_authentication_service",
    "get_authorization_service",
    "get_category_service",
    "get_period_service",
    "get_transaction_service",
    "get_group_service",
    "get_settlement_service",
    "get_identity_provider_service",
    # Auth
    "get_current_user",
    "get_current_user_optional",
    # Authorization
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_permission_in_group",
]
