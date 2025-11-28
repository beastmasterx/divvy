"""
ABAC policies for group-related business rules.

This module contains declarative policies that enforce group business rules
using Attribute-Based Access Control (ABAC). Policies evaluate subject,
resource, action, and environment attributes to make authorization decisions.

Policies are automatically registered when this module is imported.
Ensure this module is imported at application startup (e.g., in main.py).
"""

from typing import Annotated

from fastapi import Depends, Path

from app.api.dependencies.authentication import get_active_user
from app.api.dependencies.services import get_group_service, get_period_service
from app.core.i18n import _
from app.core.policies import register
from app.exceptions import BusinessRuleError, ForbiddenError
from app.schemas import UserResponse
from app.services import GroupService, PeriodService


@register("only_owner_can_delete_group")
async def policy_only_owner_can_delete_group(
    group_service: Annotated[GroupService, Depends(get_group_service)],
    group_id: Annotated[int, Path(...)],
    current_user: Annotated[UserResponse, Depends(get_active_user)],
) -> None:
    """Policy: Only the group owner can delete a group.

    Subject attributes:
        - current_user: The authenticated user attempting to delete

    Resource attributes:
        - group_id: ID of the group being deleted

    Raises:
        ForbiddenError: If current user is not the group owner
    """
    owner_id = await group_service.get_group_owner(group_id)
    if owner_id != current_user.id:
        raise ForbiddenError(_("Only the group owner can delete the group"))


@register("only_owner_can_transfer_ownership")
async def policy_only_owner_can_transfer_ownership(
    group_service: Annotated[GroupService, Depends(get_group_service)],
    group_id: Annotated[int, Path(...)],
    current_user: Annotated[UserResponse, Depends(get_active_user)],
) -> None:
    """Policy: Only the current owner can transfer group ownership.

    Subject attributes:
        - current_user: The authenticated user attempting to transfer ownership

    Resource attributes:
        - group_id: ID of the group

    Raises:
        ForbiddenError: If current user is not the current owner
    """
    current_owner_id = await group_service.get_group_owner(group_id)
    if current_owner_id != current_user.id:
        raise ForbiddenError(_("Only the current owner can transfer group ownership"))


@register("cannot_delete_group_with_unsettled_period")
async def policy_cannot_delete_group_with_unsettled_period(
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    group_id: Annotated[int, Path(...)],
    group_name: str,
) -> None:
    """Policy: Cannot delete a group if the active period has transactions and is not settled.

    Resource attributes:
        - group_id: ID of the group being deleted
        - group_name: Name of the group (for error messages)

    Environment attributes:
        - Active period state: Whether there's an active period with transactions

    Raises:
        BusinessRuleError: If active period with transactions exists and is not settled
    """
    # Get active period for the group
    active_period = await period_service.get_current_period_by_group_id(group_id)

    # Check if active period exists with transactions and is not closed
    if active_period and active_period.transactions and not active_period.is_closed:
        raise BusinessRuleError(
            _(
                "Cannot delete group '%(group_name)s': the active period '%(period_name)s' "
                "has transactions and is not settled. Please settle the period first."
            )
            % {
                "group_name": group_name,
                "period_name": active_period.name,
            }
        )


@register("cannot_remove_user_with_unsettled_period")
async def policy_cannot_remove_user_with_unsettled_period(
    period_service: Annotated[PeriodService, Depends(get_period_service)],
    group_id: Annotated[int, Path(...)],
    user_name: str,
    group_name: str,
) -> None:
    """Policy: Cannot remove a user from a group if the active period has transactions and is not settled.

    Resource attributes:
        - group_id: ID of the group
        - user_name: Name of the user being removed (for error messages)
        - group_name: Name of the group (for error messages)

    Environment attributes:
        - Active period state: Whether there's an active period with transactions

    Raises:
        BusinessRuleError: If active period with transactions exists and is not settled
    """
    # Get active period for the group
    active_period = await period_service.get_current_period_by_group_id(group_id)

    # Check if active period exists with transactions and is not closed
    if active_period and active_period.transactions and not active_period.is_closed:
        raise BusinessRuleError(
            _(
                "Cannot remove user '%(user_name)s' from group '%(group_name)s': "
                "the active period '%(period_name)s' has transactions and is not settled. "
                "Please settle the period first."
            )
            % {
                "user_name": user_name,
                "group_name": group_name,
                "period_name": active_period.name,
            }
        )
