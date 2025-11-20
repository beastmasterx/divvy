"""
API v1 router for Transaction endpoints.
"""

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
):
    """
    List all transactions.
    """
    transactions = transaction_service.get_all_transactions()
    return [TransactionResponse.model_validate(transaction) for transaction in transactions]


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Get a specific transaction by its ID.
    """
    transaction = transaction_service.get_transaction_by_id(transaction_id)
    if not transaction:
        raise NotFoundError(_("Transaction %s not found") % transaction_id)

    return TransactionResponse.model_validate(transaction)


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Create a new transaction.
    """
    created_transaction = transaction_service.create_transaction(request)
    return TransactionResponse.model_validate(created_transaction)


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    request: TransactionRequest,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Update an existing transaction.
    """
    updated_transaction = transaction_service.update_transaction(transaction_id, request)
    return TransactionResponse.model_validate(updated_transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Delete a transaction by its ID.
    """
    transaction_service.delete_transaction(transaction_id)


@router.get("/periods/{period_id}", response_model=list[TransactionResponse])
def get_transactions_by_period_id(
    period_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Get transactions by period ID.
    """
    transactions = transaction_service.get_transactions_by_period_id(period_id)
    return [TransactionResponse.model_validate(transaction) for transaction in transactions]


@router.get("/users/{user_id}/shared-transactions", response_model=list[TransactionResponse])
def get_shared_transactions_by_user_id(
    user_id: int,
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Get shared transactions by user ID.
    """
    transactions = transaction_service.get_shared_transactions_by_user_id(user_id)
    return [TransactionResponse.model_validate(transaction) for transaction in transactions]
