"""
System status service.
"""
import app.db as database
from app.services.period import get_period_summary


def get_system_status() -> dict:
    """
    Returns comprehensive system status including:
    - Member information (active/inactive, remainder flags)
    - Settlement balances
    - Transaction statistics
    - Current period information
    """
    all_members = database.get_all_members()
    active_members = database.get_active_members()
    all_transactions = database.get_all_transactions()
    current_period = database.get_current_period()
    period_summary = get_period_summary() if current_period else {}

    # Count transactions by type
    deposits = [tx for tx in all_transactions if tx["transaction_type"] == "deposit"]
    expenses = [tx for tx in all_transactions if tx["transaction_type"] == "expense"]

    # Prepare member details
    member_details = []
    period_balances = period_summary.get("balances", {})
    for member in all_members:
        member_info = {
            "name": member["name"],
            "id": member["id"],
            "is_active": bool(member["is_active"]),
            "paid_remainder_in_cycle": bool(member["paid_remainder_in_cycle"]),
            "period_balance": period_balances.get(member["name"], "N/A"),
        }
        member_details.append(member_info)

    return {
        "current_period": current_period,
        "period_summary": period_summary,
        "total_members": len(all_members),
        "active_members_count": len(active_members),
        "inactive_members_count": len(all_members) - len(active_members),
        "members": member_details,
        "transaction_counts": {
            "total": len(all_transactions),
            "deposits": len(deposits),
            "expenses": len(expenses),
        },
    }

