"""
API v1 router for Category endpoints.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.dependencies.services import get_category_service
from app.schemas.category import CategoryResponse
from app.services import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[CategoryResponse])
async def get_all_categories(
    category_service: CategoryService = Depends(get_category_service),
) -> Sequence[CategoryResponse]:
    """
    List all categories.

    Returns:
        List of all categories, ordered by ID
    """
    return await category_service.get_all_categories()
