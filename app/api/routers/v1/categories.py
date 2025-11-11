"""
API v1 router for Category endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.db as database
from app.api.dependencies import get_db
from app.api.schemas.category import CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
):
    """
    List all categories.

    Returns:
        List of all categories, ordered by name
    """
    categories = database.get_all_categories()
    return [
        CategoryResponse.model_validate(category) for category in categories
    ]
