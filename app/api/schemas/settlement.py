"""
Pydantic schemas for Settlement API endpoints.
"""
from pydantic import BaseModel


class SettlementBalanceResponse(BaseModel):
    """Schema for settlement balance response."""
    balances: dict[str, str]  # Member name -> balance description


class SettlementTransaction(BaseModel):
    """Schema for a settlement transaction."""
    date: str
    transaction_type: str
    amount: int  # Amount in cents (negative for refunds)
    description: str | None
    payer_id: int
    payer_name: str
    from_to: str  # "From" or "To"


class SettlementPlanResponse(BaseModel):
    """Schema for settlement plan response."""
    transactions: list[SettlementTransaction]

