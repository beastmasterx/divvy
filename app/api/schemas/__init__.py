"""
Pydantic schemas (DTOs) for API requests and responses.
"""

from .category import CategoryResponse
from .member import (
    MemberCreate,
    MemberMessageResponse,
    MemberResponse,
    MemberUpdate,
)
from .period import (
    MemberBalance,
    PeriodCreate,
    PeriodResponse,
    PeriodSettleRequest,
    PeriodSettleResponse,
    PeriodSummaryResponse,
    PeriodTotalsResponse,
)
from .settlement import (
    SettlementBalanceResponse,
    SettlementPlanResponse,
    SettlementTransaction,
)
from .system import (
    SystemMemberInfo,
    SystemStatusResponse,
    TransactionCounts,
)
from .transaction import (
    DepositCreate,
    ExpenseCreate,
    RefundCreate,
    TransactionMessageResponse,
    TransactionResponse,
)

__all__ = [
    # Category schemas
    "CategoryResponse",
    # Member schemas
    "MemberCreate",
    "MemberResponse",
    "MemberUpdate",
    "MemberMessageResponse",
    # Transaction schemas
    "ExpenseCreate",
    "DepositCreate",
    "RefundCreate",
    "TransactionResponse",
    "TransactionMessageResponse",
    # Period schemas
    "PeriodCreate",
    "PeriodResponse",
    "PeriodSummaryResponse",
    "PeriodSettleRequest",
    "PeriodSettleResponse",
    "MemberBalance",
    "PeriodTotalsResponse",
    # Settlement schemas
    "SettlementBalanceResponse",
    "SettlementPlanResponse",
    "SettlementTransaction",
    # System schemas
    "SystemStatusResponse",
    "SystemMemberInfo",
    "TransactionCounts",
]
