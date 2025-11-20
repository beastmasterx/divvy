"""
API v1 router for Category endpoints.
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_category_service
from app.api.schemas.category import CategoryResponse
from app.services import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    category_service: CategoryService = Depends(get_category_service),
):
    """
    List all categories.

    Returns:
        List of all categories, ordered by name
    """
    categories = category_service.get_all_categories()
    return [CategoryResponse.model_validate(category) for category in categories]
