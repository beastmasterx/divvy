"""
API v1 routers.
"""

from fastapi import APIRouter

from .auth import router as auth
from .categories import router as categories
from .groups import router as groups
from .periods import router as periods
from .transactions import router as transactions
from .user import router as user

# Create API v1 router
api_router = APIRouter(prefix="/v1")

# Include all v1 routers
api_router.include_router(auth)
api_router.include_router(categories)
api_router.include_router(groups)
api_router.include_router(transactions)
api_router.include_router(periods)
api_router.include_router(user)

__all__ = ["api_router"]
