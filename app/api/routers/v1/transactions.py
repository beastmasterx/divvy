"""
API v1 router for Transaction endpoints.
"""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_transaction_service
from app.api.schemas import TransactionRequest, TransactionResponse
from app.core.i18n import _
from app.exceptions import NotFoundError
from app.services import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionResponse])
def list_transactions(
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> Sequence[TransactionResponse]:
    """
    List all transactions.
    """
    return transaction_service.get_all_transactions()


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Get a specific transaction by its ID.
    """
    transaction = transaction_service.get_transaction_by_id(transaction_id)
    if not transaction:
        raise NotFoundError(_("Transaction %s not found") % transaction_id)

    return transaction


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Create a new transaction.
    """
    return transaction_service.create_transaction(request)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> TransactionResponse:
    """
    Update an existing transaction.
    """
    return transaction_service.update_transaction(transaction_id, request)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> None:
    """
    Delete a transaction by its ID.
    """
    transaction_service.delete_transaction(transaction_id)


@router.get("/periods/{period_id}", response_model=list[TransactionResponse])
def get_transactions_by_period_id(
    period_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> Sequence[TransactionResponse]:
    """
    Get transactions by period ID.
    """
    return transaction_service.get_transactions_by_period_id(period_id)


@router.get("/users/{user_id}/shared-transactions", response_model=list[TransactionResponse])
def get_shared_transactions_by_user_id(
    user_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> Sequence[TransactionResponse]:
    """
    Get shared transactions by user ID.
    """
    return transaction_service.get_shared_transactions_by_user_id(user_id)
