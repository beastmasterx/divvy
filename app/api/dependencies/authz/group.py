"""
API Authorization Policies and Policy Enforcement Points (PEPs) 🛡️

This module defines FastAPI dependencies that act as Policy Enforcement Points (PEPs).
These functions enforce security rules and business logic constraints before a
request reaches the final API endpoint handler.

---
ARCHITECTURE PRINCIPLES:

1.  **Policy Enforcement Point (PEP):** This module's functions are the PEPs. They are
    designed to halt execution immediately by raising HTTP exceptions (like 403 Forbidden
    or BusinessRuleError) if a condition is not met.

2.  **Policy Decision Point (PDP) Delegation:** Complex authorization logic (the PDP)
    that requires fetching specific resource data (e.g., "is the user the owner of this group?")
    is delegated to the `GroupService` methods. The PEP here only coordinates and enforces
    the decision returned by the service layer.

3.  **Vocabulary:** Names use the `requires_...` prefix to indicate a mandatory precondition
    for the endpoint to execute successfully.

---
USAGE:

Use these functions as dependencies in your FastAPI router definitions:

```python
@router.delete("/{group_id}", dependencies=[Depends(requires_group_membership)])
async def delete_group(group_id: int, ...):
    # This code only runs if requires_group_membership passed successfully
    await service.delete_group(group_id)
"""

from fastapi import Depends

from app.api.dependencies.services import get_group_service
from app.core.i18n import _
from app.exceptions import BusinessRuleError, ForbiddenError
from app.models import GroupRole
from app.services import GroupService


async def verifies_target_user_membership(
    group_id: int,
    user_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Policy Enforcement Point (PEP): Verifies that a specific target user is a member of the specified group.

    This check is typically used when an admin/owner is performing an action on another user's status within a group.
    """
    if not await group_service.is_member(group_id, user_id):
        raise BusinessRuleError(_("The target user is not a member of this group"))


async def requires_non_owner_role_assignment(
    role: GroupRole,
) -> None:
    """
    Policy Enforcement Point (PEP): Prevents the assignment of the OWNER role via this endpoint.
    """
    if role == GroupRole.OWNER:
        raise ForbiddenError(_("You are not allowed to assign this role"))


async def requires_settled_active_period(
    group_id: int,
    group_service: GroupService = Depends(get_group_service),
) -> None:
    """
    Policy Enforcement Point (PEP): Requires that the group's active period has no unsettled transactions.
    """
    if await group_service.has_active_period_with_transactions(group_id):
        raise BusinessRuleError(_("The active period has transactions and is not settled."))
