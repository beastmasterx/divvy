"""
API v1 routers.
"""
from fastapi import APIRouter

from .members import router as members_router
from .transactions import router as transactions_router
from .periods import router as periods_router
from .settlement import router as settlement_router
from .system import router as system_router

# Create API v1 router
api_router = APIRouter(prefix="/v1")

# Include all v1 routers
api_router.include_router(members_router)
api_router.include_router(transactions_router)
api_router.include_router(periods_router)
api_router.include_router(settlement_router)
api_router.include_router(system_router)

__all__ = ["api_router"]
