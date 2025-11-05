"""
API v1 router for System endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.system import SystemStatusResponse
from app.services import system as system_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    db: Session = Depends(get_db),
):
    """
    Get comprehensive system status.
    
    Includes:
    - Member information (active/inactive, remainder flags)
    - Settlement balances
    - Transaction statistics
    - Current period information
    
    Returns:
        Complete system status
    """
    status = system_service.get_system_status()
    return SystemStatusResponse(**status)

