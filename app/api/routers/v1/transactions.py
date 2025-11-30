"""
API v1 router for Transaction endpoints.
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies.services import get_transaction_service
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.models import TransactionStatus
from app.schemas import TransactionRequest, TransactionResponse
from app.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Get a specific transaction by its ID.
    """
    transaction = await transaction_service.get_transaction_by_id(transaction_id)
    if not transaction:
        raise NotFoundError(_("Transaction %s not found") % transaction_id)

    return transaction


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Create a new transaction.
    """
    return await transaction_service.create_transaction(request)


@router.put("/{transaction_id}/approve", response_model=TransactionResponse)
async def approve_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Approve a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.APPROVED)


@router.put("/{transaction_id}/reject", response_model=TransactionResponse)
async def reject_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Reject a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.REJECTED)


@router.put("/{transaction_id}/submit", response_model=TransactionResponse)
async def submit_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Submit a draft transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.PENDING)


@router.put("/{transaction_id}/draft", response_model=TransactionResponse)
async def draft_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Draft a pending transaction.
    """
    return await transaction_service.update_transaction_status(transaction_id, TransactionStatus.DRAFT)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Update an existing transaction.
    """
    return await transaction_service.update_transaction(transaction_id, request)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> None:
    """
    Delete a transaction by its ID.
    """
    await transaction_service.delete_transaction(transaction_id)
