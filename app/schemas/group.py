from pydantic import BaseModel, Field

from app.models import GroupRole


class GroupRequest(BaseModel):
    """Schema for group request."""

    name: str = Field(..., description="Group name")


class GroupRoleAssignmentRequest(BaseModel):
    """Schema for assigning a role to a group member or removing them from the group."""

    role: GroupRole | None = Field(None, description="Role to assign to the user, or null to remove user from group")


class GroupResponse(BaseModel):
    """Schema for group response."""

    model_config = {"from_attributes": True}
    id: int = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")
