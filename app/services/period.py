"""
Period management service.
"""

from datetime import datetime
from typing import Any

import app.db as database
from app.core.i18n import _
from app.models import Member
from app.services.utils import cents_to_dollars


def get_period_balances(period_id: int | None = None) -> dict[str, str]:
    """
    Calculates balances for a specific period.
    If period_id is None, uses the current active period.
    Returns who paid what and who owes what in the period.
    """
    if period_id is None:
        current_period = database.get_current_period()
        if current_period is None:
            return {}
        period_id = current_period.id

    period = database.get_period_by_id(period_id)
    if not period:
        return {}

    transactions = database.get_transactions_by_period(period_id)
    active_members = database.get_active_members()
    all_members = database.get_all_members()
    virtual_member = database.get_member_by_name(
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
    )

    # Calculate period balances
    member_balances = {member.id: 0 for member in all_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    for tx in transactions:
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
                    num_active = len(active_members)
                    if num_active > 0:
                        base_share = remaining_to_split // num_active
                        remainder = remaining_to_split % num_active

                        for i, member in enumerate(active_members):
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

            # Subtract shares from all active members (for both real and shared expenses)
            # Distribute expense among active members at transaction time
            # For simplicity, use current active members (could be enhanced to track at transaction time)
            num_active = len(active_members)
            if num_active == 0:
                continue

            base_share = tx.amount // num_active
            remainder = tx.amount % num_active

            for i, member in enumerate(active_members):
                member_balances[member.id] -= base_share
                if i < remainder:
                    member_balances[member.id] -= 1

    # Format for display
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


def get_active_member_balances(period_id: int | None = None) -> dict[str, int]:
    """
    Gets numeric balances for active members only for a period.
    Returns dict mapping member name to balance in cents (positive = owed, negative = owes).
    """
    if period_id is None:
        current_period = database.get_current_period()
        if current_period is None:
            return {}
        period_id = current_period.id

    transactions = database.get_transactions_by_period(period_id)
    active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(
        database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
    )

    # Calculate balances
    member_balances = {member.id: 0 for member in active_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    for tx in transactions:
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
                    num_active = len(active_members)
                    if num_active > 0:
                        base_share = remaining_to_split // num_active
                        remainder = remaining_to_split % num_active

                        for i, member in enumerate(active_members):
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

            # Subtract shares from all active members (for both real and shared expenses)
            num_active = len(active_members)
            if num_active == 0:
                continue

            base_share = tx.amount // num_active
            remainder = tx.amount % num_active

            for i, member in enumerate(active_members):
                member_balances[member.id] -= base_share
                if i < remainder:
                    member_balances[member.id] -= 1

    # Convert to name-based dict
    result: dict[str, int] = {}
    for member in active_members:
        result[member.name] = member_balances[member.id]

    return result


def get_period_summary(period_id: int | None = None) -> dict[str, Any]:
    """
    Gets comprehensive summary of a period including transactions and balances.
    If period_id is None, uses the current active period.
    """
    if period_id is None:
        current_period = database.get_current_period()
        if current_period is None:
            return {}
        period_id = current_period.id

    period = database.get_period_by_id(period_id)
    if not period:
        return {}

    transactions = database.get_transactions_by_period(period_id)
    balances = get_period_balances(period_id)

    # Calculate totals
    total_deposits = sum(
        tx.amount for tx in transactions if tx.transaction_type == "deposit"
    )
    total_expenses = sum(
        tx.amount for tx in transactions if tx.transaction_type == "expense"
    )

    return {
        "period": period,
        "transactions": transactions,
        "balances": balances,
        "totals": {
            "deposits": total_deposits,
            "deposits_formatted": cents_to_dollars(total_deposits),
            "expenses": total_expenses,
            "expenses_formatted": cents_to_dollars(total_expenses),
            "net": total_deposits - total_expenses,
            "net_formatted": cents_to_dollars(total_deposits - total_expenses),
        },
        "transaction_count": len(transactions),
    }


def settle_current_period(period_name: str | None = None) -> str:
    """
    Settles the current period by creating settlement transactions to zero all balances,
    then creates a new period.
    Returns a message describing what happened.
    """
    current_period = database.get_current_period()
    if not current_period:
        return _("Error: No active period to settle.")

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

    # Create settlement transactions to zero balances
    settlement_messages: list[str] = []
    total_owed = 0
    total_owing = 0

    # Collect members who owe (negative balance) and who are owed (positive balance)
    debtors: list[tuple[Member, int]] = []  # Members who owe money
    creditors: list[tuple[Member, int]] = []  # Members who are owed money

    for member in active_members:
        balance = member_balances_cents.get(member.name, 0)
        if balance < 0:
            debtors.append((member, abs(balance)))
            total_owing += abs(balance)
        elif balance > 0:
            creditors.append((member, balance))
            total_owed += balance

    # Handle public fund - if there's remaining balance, distribute it
    if public_fund_balance > 0 and creditors:
        # Distribute public fund to creditors proportionally or to first creditor
        # Simple approach: give all to first creditor
        creditor, creditor_balance = creditors[0]
        # Negative deposit to creditor reduces their positive balance (they receive the fund)
        database.add_transaction(
            transaction_type="deposit",
            amount=-public_fund_balance,
            description=_("Settlement: Public fund distribution"),
            payer_id=creditor.id,
            period_id=period_id,
        )
        settlement_messages.append(
            _("  Public fund ${} distributed to {}").format(
                cents_to_dollars(public_fund_balance), creditor.name
            )
        )
        # Update the creditor's balance after public fund distribution
        new_balance = creditor_balance - public_fund_balance
        if new_balance <= 0:
            # Balance is zero or negative, remove from creditors list
            creditors.pop(0)
        else:
            # Update the balance in the list
            creditors[0] = (creditor, new_balance)

    # Settle debts: debtors pay creditors
    # Match debtors with creditors to create settlement transactions
    debtor_idx = 0
    creditor_idx = 0

    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor, debt_amount = debtors[debtor_idx]
        creditor, credit_amount = creditors[creditor_idx]

        settlement_amount = min(debt_amount, credit_amount)
        settlement_amount_str = cents_to_dollars(settlement_amount)

        # Record settlement: debtor pays, creditor receives
        # Create matching transactions that zero both balances:
        # 1. Creditor receives payment (negative deposit reduces creditor's positive balance)
        # 2. Debtor makes payment (positive deposit reduces debtor's negative balance)

        # Creditor receives payment (negative deposit decreases their positive balance)
        database.add_transaction(
            transaction_type="deposit",
            amount=-settlement_amount,
            description=_("Settlement payment from {}").format(debtor.name),
            payer_id=creditor.id,
            period_id=period_id,
        )

        # Debtor makes payment (positive deposit reduces their negative balance toward zero)
        database.add_transaction(
            transaction_type="deposit",
            amount=settlement_amount,
            description=_("Settlement payment to {}").format(creditor.name),
            payer_id=debtor.id,
            period_id=period_id,
        )

        settlement_messages.append(
            _("  {} pays ${} to {}").format(
                debtor.name,
                settlement_amount_str,
                creditor.name,
            )
        )

        # Update remaining amounts
        debt_amount -= settlement_amount
        credit_amount -= settlement_amount

        if debt_amount == 0:
            debtor_idx += 1
        else:
            debtors[debtor_idx] = (debtor, debt_amount)

        if credit_amount == 0:
            creditor_idx += 1
        else:
            creditors[creditor_idx] = (creditor, credit_amount)

    # Handle remaining creditors (members with positive balances that weren't matched)
    # If multiple creditors remain, pair them together (smallest pays largest)
    # Otherwise, refund remaining creditors
    remaining_creditors = (
        creditors[creditor_idx:] if creditor_idx < len(creditors) else []
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
            database.add_transaction(
                transaction_type="deposit",
                amount=-settlement_amount,
                description=_("Settlement payment to {}").format(
                    larger_creditor.name
                ),
                payer_id=smaller_creditor.id,
                period_id=period_id,
            )

            # Larger creditor receives payment (negative deposit to reduce their positive balance)
            database.add_transaction(
                transaction_type="deposit",
                amount=-settlement_amount,
                description=_("Settlement payment from {}").format(
                    smaller_creditor.name
                ),
                payer_id=larger_creditor.id,
                period_id=period_id,
            )

            settlement_messages.append(
                _("  {} pays ${} to {}").format(
                    smaller_creditor.name,
                    cents_to_dollars(settlement_amount),
                    larger_creditor.name,
                )
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
            database.add_transaction(
                transaction_type="deposit",
                amount=-credit_amount,
                description=_("Settlement: Refund remaining balance"),
                payer_id=creditor.id,
                period_id=period_id,
            )
            settlement_messages.append(
                _("  {} refunded ${}").format(
                    creditor.name,
                    cents_to_dollars(credit_amount),
                )
            )
    elif len(remaining_creditors) == 1:
        # Single remaining creditor - just refund
        creditor, credit_amount = remaining_creditors[0]
        database.add_transaction(
            transaction_type="deposit",
            amount=-credit_amount,
            description=_("Settlement: Refund remaining balance"),
            payer_id=creditor.id,
            period_id=period_id,
        )
        settlement_messages.append(
            _("  {} refunded ${}").format(
                creditor.name,
                cents_to_dollars(credit_amount),
            )
        )

    # Handle remaining debtors (members with negative balances that weren't matched)
    # They still need to pay to zero their balance
    while debtor_idx < len(debtors):
        debtor, debt_amount = debtors[debtor_idx]
        # Create a positive deposit for the debtor to pay their debt
        database.add_transaction(
            transaction_type="deposit",
            amount=debt_amount,
            description=_("Settlement: Pay remaining debt"),
            payer_id=debtor.id,
            period_id=period_id,
        )
        settlement_messages.append(
            _("  {} pays ${} to settle remaining debt").format(
                debtor.name,
                cents_to_dollars(debt_amount),
            )
        )
        debtor_idx += 1

    # Settle the period
    database.settle_period(period_id)

    # Create new period
    if period_name is None:
        period_name = datetime.now().strftime("%B %Y")  # e.g., "October 2025"

    new_period_id = database.create_new_period(period_name)
    new_period = database.get_period_by_id(new_period_id)

    # Reset remainder flags for new period
    database.reset_all_member_remainder_status()

    return _(
        "Period '{}' has been settled.\n" "New period '{}' created."
    ).format(
        current_period.name,
        new_period.name if new_period else "",
    )
