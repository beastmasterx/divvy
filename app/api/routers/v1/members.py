"""
API v1 router for Member endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.member import (
    MemberCreate,
    MemberResponse,
    MemberMessageResponse,
)
from app.services import member as member_service
import app.db as database

router = APIRouter(prefix="/members", tags=["members"])


@router.post("/", response_model=MemberMessageResponse, status_code=201)
def create_member(
    member_data: MemberCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new member.
    
    Returns:
        Success or error message
    """
    result = member_service.add_new_member(member_data.email, member_data.name)
    
    # Check if it's an error message
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return MemberMessageResponse(message=result)


@router.get("/", response_model=list[MemberResponse])
def list_members(
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    List all members.
    
    Args:
        active_only: If True, only return active members
    
    Returns:
        List of members
    """
    if active_only:
        members = database.get_active_members()
    else:
        members = database.get_all_members()
    
    return [MemberResponse(**member) for member in members]


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a member by ID.
    
    Args:
        member_id: ID of the member
    
    Returns:
        Member details
    """
    member = database.get_member_by_id(member_id)
    if not member:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found")
    
    return MemberResponse(**member)


@router.delete("/{member_id}", response_model=MemberMessageResponse)
def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
):
    """
    Remove (deactivate) a member.
    
    Args:
        member_id: ID of the member to remove
    
    Returns:
        Success or error message
    """
    result = member_service.remove_member_by_id(member_id)
    
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return MemberMessageResponse(message=result)


@router.post("/{member_id}/rejoin", response_model=MemberMessageResponse)
def rejoin_member(
    member_id: int,
    db: Session = Depends(get_db),
):
    """
    Rejoin (reactivate) an inactive member.
    
    Args:
        member_id: ID of the member to rejoin
    
    Returns:
        Success or error message
    """
    result = member_service.rejoin_member_by_id(member_id)
    
    if result.startswith("Error:"):
        raise HTTPException(status_code=400, detail=result)
    
    return MemberMessageResponse(message=result)

