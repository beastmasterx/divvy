"""
Pydantic schemas for System API endpoints.
"""
from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    """Schema for system status response."""
    current_period: dict | None
    period_summary: dict
    total_members: int
    active_members_count: int
    inactive_members_count: int
    members: list[dict]
    transaction_counts: dict

