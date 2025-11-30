"""
API v1 router for Transaction endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.api.dependencies.authz import requires_group_role_for_transaction
from app.api.dependencies.authz.transaction import requires_transaction_status, requires_transaction_status_and_creator
from app.api.dependencies.services import get_transaction_service
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import GroupRole, TransactionStatus
from app.schemas import TransactionRequest, TransactionResponse, UserResponse
from app.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"], dependencies=[Depends(get_current_user)])


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_by_id(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[UserResponse, Depends(requires_group_role_for_transaction(GroupRole.MEMBER))],
) -> TransactionResponse:
    """
    Get a specific transaction by its ID.
    """
    transaction = await transaction_service.get_transaction_by_id(transaction_id)
    if not transaction:
        raise NotFoundError(_("Transaction %s not found") % transaction_id)

    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    request: TransactionRequest,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[UserResponse, Depends(requires_group_role_for_transaction(GroupRole.MEMBER))],
    _status_check: Annotated[
        TransactionResponse, Depends(requires_transaction_status_and_creator(TransactionStatus.DRAFT))
    ],
) -> TransactionResponse:
    """Update an existing transaction."""
    return await transaction_service.update_transaction(transaction_id, request)


@router.put("/{transaction_id}/approve", response_model=TransactionResponse)
async def approve_transaction(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[
        UserResponse, Depends(requires_group_role_for_transaction(GroupRole.OWNER, GroupRole.ADMIN))
    ],
    _status_check: Annotated[TransactionResponse, Depends(requires_transaction_status(TransactionStatus.PENDING))],
) -> TransactionResponse:
    """
    Approve a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.APPROVED)


@router.put("/{transaction_id}/reject", response_model=TransactionResponse)
async def reject_transaction(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[
        UserResponse, Depends(requires_group_role_for_transaction(GroupRole.OWNER, GroupRole.ADMIN))
    ],
    _status_check: Annotated[TransactionResponse, Depends(requires_transaction_status(TransactionStatus.PENDING))],
) -> TransactionResponse:
    """
    Reject a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.REJECTED)


@router.put("/{transaction_id}/submit", response_model=TransactionResponse)
async def submit_transaction(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[
        UserResponse, Depends(requires_group_role_for_transaction(GroupRole.OWNER, GroupRole.ADMIN))
    ],
    _status_check: Annotated[
        TransactionResponse, Depends(requires_transaction_status_and_creator(TransactionStatus.DRAFT))
    ],
) -> TransactionResponse:
    """
    Submit a draft transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.PENDING)


@router.put("/{transaction_id}/draft", response_model=TransactionResponse)
async def draft_transaction(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[UserResponse, Depends(requires_group_role_for_transaction(GroupRole.MEMBER))],
    _status_check: Annotated[
        TransactionResponse,
        Depends(requires_transaction_status_and_creator(TransactionStatus.PENDING, TransactionStatus.REJECTED)),
    ],
) -> TransactionResponse:
    """
    Draft a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.DRAFT)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    _group_role_check: Annotated[
        UserResponse, Depends(requires_group_role_for_transaction(GroupRole.OWNER, GroupRole.ADMIN, GroupRole.MEMBER))
    ],
    _status_check: Annotated[
        TransactionResponse,
        Depends(requires_transaction_status_and_creator(TransactionStatus.DRAFT, TransactionStatus.REJECTED)),
    ],
) -> None:
    """
    Delete a transaction by its ID.
    """
    await transaction_service.delete_transaction(transaction_id)
