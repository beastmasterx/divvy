"""
API v1 routers.
"""

from fastapi import APIRouter

from .auth import router as auth
from .categories import router as categories
from .group import router as groups
from .period import router as periods
from .transaction import router as transactions

# Create API v1 router
api_router = APIRouter(prefix="/v1")

# Include all v1 routers
api_router.include_router(auth)
api_router.include_router(categories)
api_router.include_router(groups)
api_router.include_router(transactions)
api_router.include_router(periods)

__all__ = ["api_router"]
