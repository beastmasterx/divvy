"""
Policy Enforcement Points (PEPs) for Transaction resources 🛡️
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends

from app.api.dependencies.authn import get_current_user
from app.api.dependencies.services import get_transaction_service
from app.core.i18n import _
from app.exceptions import ForbiddenError, NotFoundError
from app.models import TransactionStatus
from app.schemas import TransactionResponse, UserResponse
from app.services import TransactionService


def requires_transaction_status(*statuses: TransactionStatus) -> Callable[..., Awaitable[Any]]:
    """
    Policy Enforcement Point (PEP): Requires a specific transaction status for the transaction identified by 'transaction_id' in the path.
    """
    # Create a comma-separated list of required status names for the error message
    display_statuses = ", ".join([s.name for s in statuses])

    async def _requires_transaction_status(
        transaction_id: int,
        transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    ) -> TransactionResponse:
        """
        Internal PEP check: Retrieves transaction and verifies its status against the requirements.
        """
        transaction = await transaction_service.get_transaction_by_id(transaction_id)

        if not transaction:
            raise NotFoundError(_("Transaction %s not found") % transaction_id)

        if transaction.status not in statuses:
            raise ForbiddenError(
                _("Transaction %s must be in one of the following statuses: %(statuses)s")
                % {"transaction_id": transaction_id, "statuses": display_statuses}
            )

        return transaction

    return _requires_transaction_status


def requires_transaction_status_and_creator(*statuses: TransactionStatus) -> Callable[..., Awaitable[Any]]:
    """
    Policy Enforcement Point (PEP): Requires the authenticated user to be the creator of the transaction and that the transaction is in one of the required statuses.
    """
    # Create a comma-separated list of required status names for the error message
    display_statuses = ", ".join([s.name for s in statuses])

    async def _requires_transaction_status_and_creator(
        transaction_id: int,
        transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
        current_user: Annotated[UserResponse, Depends(get_current_user)],
    ) -> TransactionResponse:
        """
        Internal PEP check: Retrieves transaction and verifies its status and the creator's ID.
        """
        transaction = await transaction_service.get_transaction_by_id(transaction_id)

        if not transaction:
            raise NotFoundError(_("Transaction %s not found") % transaction_id)

        # 1. Status Check
        if transaction.status not in statuses:
            raise ForbiddenError(
                _("Transaction %s must be in one of the following statuses: %(statuses)s")
                % {"transaction_id": transaction_id, "statuses": display_statuses}
            )

        # 2. Creator (Ownership) Check
        if transaction.created_by != current_user.id:
            raise ForbiddenError(_("Transaction %s is not created by the current user") % transaction_id)

        return transaction

    return _requires_transaction_status_and_creator
