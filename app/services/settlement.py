"""
Settlement calculation service.
"""

from datetime import datetime
from typing import Any

import app.db as database
from app.core.i18n import _
from app.models import Member
from app.services.period import get_active_member_balances
from app.services.utils import cents_to_dollars


def get_settlement_balances() -> dict[str, str]:
    """
    Calculates and returns the final settlement balances for all members.
    - For each member, calculates total paid vs. total share.
    - Determines who owes money and who is owed money.
    """
    all_members = database.get_all_members()
    all_transactions = database.get_all_transactions()
    current_active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
    )

    member_balances = {member.id: 0 for member in all_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    # Calculate initial contributions and expenses
    # Process transactions in chronological order to track public fund correctly
    for tx in all_transactions:
        if tx.transaction_type == "deposit":
            # Credit deposits to payer (including virtual member for public fund)
            if tx.payer_id and tx.payer_id in member_balances:
                member_balances[tx.payer_id] += tx.amount
            # If virtual member deposits, add to public fund
            if (
                tx.payer_id
                and virtual_member
                and tx.payer_id == virtual_member.id
            ):
                public_fund_balance += tx.amount
        elif tx.transaction_type == "expense":
            payer = (
                database.get_member_by_id(tx.payer_id) if tx.payer_id else None
            )
            is_virtual = payer and database.is_virtual_member(payer)

            if is_virtual:
                # Shared expense: use public fund first, then split remainder
                expense_amount = tx.amount
                # Use public fund (can't go negative)
                fund_used = min(expense_amount, public_fund_balance)
                public_fund_balance -= fund_used
                remaining_to_split = expense_amount - fund_used

                # Split remaining amount among members
                if remaining_to_split > 0:
                    num_active = len(current_active_members)
                    if num_active > 0:
                        base_share = remaining_to_split // num_active
                        remainder = remaining_to_split % num_active

                        for i, member in enumerate(current_active_members):
                            member_balances[member.id] -= base_share
                            if i < remainder:
                                member_balances[member.id] -= 1
                continue

            # Handle personal expenses: only subtract from payer (NO credit for paying)
            if tx.is_personal:  # Check if this is a personal expense
                if tx.payer_id and tx.payer_id in member_balances:
                    member_balances[tx.payer_id] -= tx.amount
                continue

            # Individual expense: credit real member for paying (not personal)
            if payer and tx.payer_id in member_balances:
                member_balances[tx.payer_id] += tx.amount

            # Distribute expense cost among current active members (individual split)
            num_active = len(current_active_members)
            if (
                num_active == 0
            ):  # Should not happen if record_expense prevents it
                continue

            base_share = tx.amount // num_active
            remainder = tx.amount % num_active

            for i, member in enumerate(current_active_members):
                member_balances[member.id] -= base_share
                if (
                    i < remainder
                ):  # Distribute remainder sequentially for historical expenses
                    member_balances[member.id] -= 1

    # Format balances for display
    formatted_balances: dict[str, str] = {}
    for member_id, balance in member_balances.items():
        member = database.get_member_by_id(member_id)
        member_name = member.name if member else ""
        if balance > 0:
            formatted_balances[member_name] = _("Is owed {}").format(
                cents_to_dollars(balance)
            )
        elif balance < 0:
            formatted_balances[member_name] = _("Owes {}").format(
                cents_to_dollars(abs(balance))
            )
        else:
            formatted_balances[member_name] = _("Settled")

    return formatted_balances


def get_settlement_plan(period_id: int | None = None) -> list[dict[str, Any]]:
    """
    Calculates and returns the settlement plan without executing it.
    Returns a list of transaction-like dictionaries that would be created.
    Each dict has: date, transaction_type, amount, description, payer_id, payer_name, from_to_label
    """
    if period_id is None:
        current_period = database.get_current_period()
        if not current_period:
            return []
        period_id = current_period.id

    # Get balances before settlement
    member_balances_cents = get_active_member_balances(period_id)
    active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
    )

    # Calculate public fund balance
    transactions = database.get_transactions_by_period(period_id)
    public_fund_balance = 0
    for tx in transactions:
        if tx.transaction_type == "deposit":
            if (
                tx.payer_id
                and virtual_member
                and tx.payer_id == virtual_member.id
            ):
                public_fund_balance += tx.amount
        elif tx.transaction_type == "expense":
            payer = (
                database.get_member_by_id(tx.payer_id) if tx.payer_id else None
            )
            if payer and database.is_virtual_member(payer):
                expense_amount = tx.amount
                fund_used = min(expense_amount, public_fund_balance)
                public_fund_balance -= fund_used

    # Calculate settlement plan as transaction records
    settlement_date = datetime.now().strftime("%Y-%m-%d")
    settlement_transactions: list[dict[str, Any]] = []

    # Collect members who owe (negative balance) and who are owed (positive balance)
    debtors: list[tuple[Member, int]] = []  # Members who owe money
    creditors: list[tuple[Member, int]] = []  # Members who are owed money

    for member in active_members:
        balance = member_balances_cents.get(member.name, 0)
        if balance < 0:
            debtors.append((member, abs(balance)))
        elif balance > 0:
            creditors.append((member, balance))

    # Create working copies for planning (without modifying originals)
    working_debtors = [(debtor, debt_amt) for debtor, debt_amt in debtors]
    working_creditors = [
        (creditor, credit_amt) for creditor, credit_amt in creditors
    ]

    # Handle public fund - if there's remaining balance, distribute it
    if public_fund_balance > 0 and working_creditors:
        # Distribute public fund to first creditor
        creditor, creditor_balance = working_creditors[0]
        # Fund distribution creates a refund (negative deposit) to creditor
        settlement_transactions.append(
            {
                "date": settlement_date,
                "transaction_type": "deposit",  # Will be displayed as Refund due to negative amount
                "amount": -public_fund_balance,
                "description": _("Settlement: Public fund distribution"),
                "payer_id": creditor.id,
                "payer_name": creditor.name,
                "from_to": "To",
            }
        )
        # Update the creditor's balance after public fund distribution
        new_balance = creditor_balance - public_fund_balance
        if new_balance <= 0:
            # Balance is zero or negative, remove from creditors list
            working_creditors.pop(0)
        else:
            # Update the balance in the list
            working_creditors[0] = (creditor, new_balance)

    # Calculate debt settlements: debtors pay creditors
    # Match debtors with creditors to create settlement plan
    debtor_idx = 0
    creditor_idx = 0

    while debtor_idx < len(working_debtors) and creditor_idx < len(
        working_creditors
    ):
        debtor, debt_amount = working_debtors[debtor_idx]
        creditor, credit_amount = working_creditors[creditor_idx]

        settlement_amount = min(debt_amount, credit_amount)

        # Debtor makes payment (positive deposit)
        settlement_transactions.append(
            {
                "date": settlement_date,
                "transaction_type": "deposit",
                "amount": settlement_amount,
                "description": _("Settlement payment to {}").format(
                    creditor.name
                ),
                "payer_id": debtor.id,
                "payer_name": debtor.name,
                "from_to": "From",
            }
        )

        # Creditor receives payment (negative deposit, shown as refund)
        settlement_transactions.append(
            {
                "date": settlement_date,
                "transaction_type": "deposit",  # Will be displayed as Refund due to negative amount
                "amount": -settlement_amount,
                "description": _("Settlement payment from {}").format(
                    debtor.name
                ),
                "payer_id": creditor.id,
                "payer_name": creditor.name,
                "from_to": "To",
            }
        )

        # Update remaining amounts
        debt_amount -= settlement_amount
        credit_amount -= settlement_amount

        if debt_amount == 0:
            debtor_idx += 1
        else:
            working_debtors[debtor_idx] = (debtor, debt_amount)

        if credit_amount == 0:
            creditor_idx += 1
        else:
            working_creditors[creditor_idx] = (creditor, credit_amount)

    # Handle remaining creditors (members with positive balances that weren't matched)
    # If multiple creditors remain, pair them together (smallest pays largest)
    # Otherwise, refund remaining creditors
    remaining_creditors = (
        working_creditors[creditor_idx:]
        if creditor_idx < len(working_creditors)
        else []
    )

    if len(remaining_creditors) > 1:
        # Pair creditors: smallest pays largest to zero smallest balance
        remaining_creditors.sort(key=lambda x: x[1])  # Sort by amount

        while len(remaining_creditors) > 1:
            smaller_creditor, smaller_amount = remaining_creditors[0]
            larger_creditor, larger_amount = remaining_creditors[-1]

            # Smaller creditor pays larger creditor to zero smaller balance
            settlement_amount = smaller_amount

            # Smaller creditor makes payment (negative deposit to reduce their positive balance)
            settlement_transactions.append(
                {
                    "date": settlement_date,
                    "transaction_type": "deposit",
                    "amount": -settlement_amount,
                    "description": _("Settlement payment to {}").format(
                        larger_creditor.name
                    ),
                    "payer_id": smaller_creditor.id,
                    "payer_name": smaller_creditor.name,
                    "from_to": "To",
                }
            )

            # Larger creditor receives payment (negative deposit to reduce their positive balance)
            settlement_transactions.append(
                {
                    "date": settlement_date,
                    "transaction_type": "deposit",
                    "amount": -settlement_amount,
                    "description": _("Settlement payment from {}").format(
                        smaller_creditor.name
                    ),
                    "payer_id": larger_creditor.id,
                    "payer_name": larger_creditor.name,
                    "from_to": "To",
                }
            )

            # Remove smaller creditor (now at zero)
            remaining_creditors.pop(0)

            # Update larger creditor's remaining balance
            new_larger_amount = larger_amount - settlement_amount
            if new_larger_amount == 0:
                remaining_creditors.pop()
            else:
                remaining_creditors[-1] = (larger_creditor, new_larger_amount)
                remaining_creditors.sort(key=lambda x: x[1])

        # Refund any remaining single creditor
        if len(remaining_creditors) == 1:
            creditor, credit_amount = remaining_creditors[0]
            settlement_transactions.append(
                {
                    "date": settlement_date,
                    "transaction_type": "deposit",
                    "amount": -credit_amount,
                    "description": _("Settlement: Refund remaining balance"),
                    "payer_id": creditor.id,
                    "payer_name": creditor.name,
                    "from_to": "To",
                }
            )
    elif len(remaining_creditors) == 1:
        # Single remaining creditor - just refund
        creditor, credit_amount = remaining_creditors[0]
        settlement_transactions.append(
            {
                "date": settlement_date,
                "transaction_type": "deposit",
                "amount": -credit_amount,
                "description": _("Settlement: Refund remaining balance"),
                "payer_id": creditor.id,
                "payer_name": creditor.name,
                "from_to": "To",
            }
        )

    # Handle remaining debtors (members with negative balances that weren't matched)
    # They still need to pay to zero their balance
    while debtor_idx < len(working_debtors):
        debtor, debt_amount = working_debtors[debtor_idx]
        # Create a positive deposit for the debtor to pay their debt
        settlement_transactions.append(
            {
                "date": settlement_date,
                "transaction_type": "deposit",
                "amount": debt_amount,
                "description": _("Settlement: Pay remaining debt"),
                "payer_id": debtor.id,
                "payer_name": debtor.name,
                "from_to": "From",
            }
        )
        debtor_idx += 1

    return settlement_transactions
