"""
API v1 routers.
"""

from fastapi import APIRouter

from .categories import router as categories
from .members import router as members
from .periods import router as periods
from .settlement import router as settlement
from .system import router as system
from .transactions import router as transactions

# Create API v1 router
api_router = APIRouter(prefix="/v1")

# Include all v1 routers
api_router.include_router(members)
api_router.include_router(transactions)
api_router.include_router(periods)
api_router.include_router(settlement)
api_router.include_router(system)
api_router.include_router(categories)

__all__ = ["api_router"]
