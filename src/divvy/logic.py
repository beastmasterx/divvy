from . import database

# --- Helper functions ---


def _cents_to_dollars(cents: int) -> str:
    """Converts an amount in cents to a dollar string (e.g., 12345 -> "123.45")."""
    return f"{cents / 100:.2f}"


def _dollars_to_cents(dollars_str: str) -> int:
    """Converts a dollar string to an amount in cents (e.g., "123.45" -> 12345)."""
    try:
        return int(float(dollars_str) * 100)
    except ValueError as err:
        raise ValueError("Invalid amount format. Please enter a number.") from err


# --- Business logic functions ---


def add_new_member(name: str) -> str:
    """
    Adds a new member to the group.
    - If member exists (active or inactive): returns error (use rejoin_member for inactive members).
    - If member doesn't exist: adds new member.
    """
    existing_member = database.get_member_by_name(name)
    if existing_member:
        if existing_member["is_active"]:
            return f"Error: Member '{name}' already exists and is active."
        else:
            return f"Error: Member '{name}' exists but is inactive. Please use rejoin option."

    # Add the new member
    new_member_id = database.add_member(name)
    if new_member_id is None:  # Should not happen if check for existing_member passed
        return f"Error: Could not add member '{name}'."

    return f"Member '{name}' added successfully."


def record_expense(
    description: str | None,
    amount_str: str,
    payer_name: str,
    category_name: str,
) -> str:
    """
    Records a new expense.
    - Converts amount to cents.
    - Validates participants.
    - Calculates the split and remainder.
    - Records the expense transaction in the database.
    - Updates the remainder-paid cycle for the member who paid the remainder.
    """
    try:
        amount_cents = _dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    payer = database.get_member_by_name(payer_name)
    if not payer:
        return f"Error: Payer '{payer_name}' not found."
    payer_id_for_transaction = payer["id"]

    category = database.get_category_by_name(category_name)
    if not category:
        return f"Error: Category '{category_name}' not found."

    active_members = database.get_active_members()
    if not active_members:
        return "Error: No active members to split the expense among."

    num_active_members = len(active_members)
    remainder = amount_cents % num_active_members

    remainder_payer_name = "N/A"
    remainder_payer_id = None

    if remainder > 0:  # Only assign remainder if there is one
        # First, check if all members have paid a remainder in the current cycle
        all_paid_remainder = True
        for member in active_members:
            if not member["paid_remainder_in_cycle"]:
                all_paid_remainder = False
                break

        if all_paid_remainder:
            database.reset_all_member_remainder_status()
            # Re-fetch active members after reset to get updated status
            active_members = database.get_active_members()

        # Find the next member to pay the remainder
        for member in active_members:
            if not member["paid_remainder_in_cycle"]:
                remainder_payer_id = member["id"]
                remainder_payer_name = member["name"]
                database.update_member_remainder_status(member["id"], True)
                break

        if (
            remainder_payer_id is None
        ):  # Should not happen if logic is correct and active_members is not empty
            return "Internal Error: Could not determine remainder payer."

    # Record the expense transaction
    database.add_transaction(
        transaction_type="expense",
        amount=amount_cents,
        description=description,
        payer_id=payer_id_for_transaction,
        category_id=category["id"],
    )

    description_display = description if description else "(no description)"
    return (
        f"Expense '{description_display}' of "
        f"{_cents_to_dollars(amount_cents)} recorded successfully. "
        f"Remainder of {_cents_to_dollars(remainder)} assigned to "
        f"{remainder_payer_name}."
    )


def record_deposit(
    description: str | None,
    amount_str: str,
    payer_name: str,
) -> str:
    """
    Records a new deposit from a member.
    - Converts amount to cents.
    - Validates the payer.
    - Records the deposit transaction in the database.
    """
    try:
        amount_cents = _dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    payer = database.get_member_by_name(payer_name)
    if not payer:
        return f"Error: Payer '{payer_name}' not found."

    # Record the deposit transaction
    database.add_transaction(
        transaction_type="deposit",
        amount=amount_cents,
        description=description,
        payer_id=payer["id"],
        category_id=None,
    )

    description_display = description if description else "(no description)"
    return (
        f"Deposit '{description_display}' of "
        f"{_cents_to_dollars(amount_cents)} from {payer_name} "
        f"recorded successfully."
    )


def record_refund(
    description: str | None,
    amount_str: str,
    recipient_name: str,
) -> str:
    """
    Records a refund to a member (active or inactive).
    - Converts amount to cents.
    - Validates the recipient.
    - Records the refund as a negative deposit transaction.
    """
    try:
        amount_cents = _dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    recipient = database.get_member_by_name(recipient_name)
    if not recipient:
        return f"Error: Member '{recipient_name}' not found."

    # Record refund as negative deposit (reduces recipient's balance)
    # Note: We store as positive amount, but mark it as refund in description
    refund_desc = description if description else f"Refund to {recipient_name}"
    if not description or not description.startswith("Refund"):
        refund_desc = f"Refund: {refund_desc}" if description else f"Refund to {recipient_name}"

    database.add_transaction(
        transaction_type="deposit",
        amount=-amount_cents,  # Negative amount for refund
        description=refund_desc,
        payer_id=recipient["id"],  # Recipient gets the refund
        category_id=None,
    )

    description_display = refund_desc
    return (
        f"Refund '{description_display}' of "
        f"{_cents_to_dollars(amount_cents)} to {recipient_name} "
        f"recorded successfully."
    )


def get_settlement_balances() -> dict[str, str]:
    """
    Calculates and returns the final settlement balances for all members.
    - For each member, calculates total paid vs. total share.
    - Determines who owes money and who is owed money.
    """
    all_members = database.get_all_members()
    all_transactions = database.get_all_transactions()
    current_active_members = database.get_active_members()

    member_balances = {member["id"]: 0 for member in all_members}

    # Calculate initial contributions and expenses
    for tx in all_transactions:
        if tx["transaction_type"] == "deposit":
            if tx["payer_id"]:
                member_balances[tx["payer_id"]] += tx["amount"]
        elif tx["transaction_type"] == "expense":
            if tx["payer_id"]:
                member_balances[tx["payer_id"]] += tx["amount"]

            # Distribute expense cost among current active members
            num_active = len(current_active_members)
            if num_active == 0:  # Should not happen if record_expense prevents it
                continue

            base_share = tx["amount"] // num_active
            remainder = tx["amount"] % num_active

            for i, member in enumerate(current_active_members):
                member_balances[member["id"]] -= base_share
                if i < remainder:  # Distribute remainder sequentially for historical expenses
                    member_balances[member["id"]] -= 1

    # Format balances for display
    formatted_balances = {}
    for member_id, balance in member_balances.items():
        member_name = database.get_member_by_id(member_id)["name"]
        if balance > 0:
            formatted_balances[member_name] = f"Is owed {_cents_to_dollars(balance)}"
        elif balance < 0:
            formatted_balances[member_name] = f"Owes {_cents_to_dollars(abs(balance))}"
        else:
            formatted_balances[member_name] = "Settled"

    return formatted_balances


def remove_member(name: str) -> str:
    """
    Removes (deactivates) a member from the group.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return f"Error: Member '{name}' not found."

    if not member["is_active"]:
        return f"Error: Member '{name}' is already inactive."

    database.deactivate_member(member["id"])
    return f"Member '{name}' has been removed (deactivated)."


def rejoin_member(name: str) -> str:
    """
    Rejoins (reactivates) an inactive member.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return f"Error: Member '{name}' not found."

    if member["is_active"]:
        return f"Error: Member '{name}' is already active."

    database.reactivate_member(member["id"])
    return f"Member '{name}' has been reactivated (rejoined)."


def get_period_balances(period_id: int | None = None) -> dict:
    """
    Calculates balances for a specific period.
    If period_id is None, uses the current active period.
    Returns who paid what and who owes what in the period.
    """
    if period_id is None:
        current_period = database.get_current_period()
        if current_period is None:
            return {}
        period_id = current_period["id"]

    period = database.get_period_by_id(period_id)
    if not period:
        return {}

    transactions = database.get_transactions_by_period(period_id)
    active_members = database.get_active_members()
    all_members = database.get_all_members()

    # Calculate period balances
    member_balances = {member["id"]: 0 for member in all_members}

    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            if tx["payer_id"]:
                member_balances[tx["payer_id"]] += tx["amount"]
        elif tx["transaction_type"] == "expense":
            if tx["payer_id"]:
                member_balances[tx["payer_id"]] += tx["amount"]

            # Distribute expense among active members at transaction time
            # For simplicity, use current active members (could be enhanced to track at transaction time)
            num_active = len(active_members)
            if num_active == 0:
                continue

            base_share = tx["amount"] // num_active
            remainder = tx["amount"] % num_active

            for i, member in enumerate(active_members):
                member_balances[member["id"]] -= base_share
                if i < remainder:
                    member_balances[member["id"]] -= 1

    # Format for display
    formatted_balances = {}
    for member_id, balance in member_balances.items():
        member_name = database.get_member_by_id(member_id)["name"]
        if balance > 0:
            formatted_balances[member_name] = f"Is owed {_cents_to_dollars(balance)}"
        elif balance < 0:
            formatted_balances[member_name] = f"Owes {_cents_to_dollars(abs(balance))}"
        else:
            formatted_balances[member_name] = "Settled"

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
        period_id = current_period["id"]

    transactions = database.get_transactions_by_period(period_id)
    active_members = database.get_active_members()

    # Calculate balances
    member_balances = {member["id"]: 0 for member in active_members}

    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            if tx["payer_id"] and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]
        elif (
            tx["transaction_type"] == "expense"
            and tx["payer_id"]
            and tx["payer_id"] in member_balances
        ):
            # Only process expenses paid by active members (skip if payer_id is None)
            member_balances[tx["payer_id"]] += tx["amount"]

            num_active = len(active_members)
            if num_active == 0:
                continue

            base_share = tx["amount"] // num_active
            remainder = tx["amount"] % num_active

            for i, member in enumerate(active_members):
                member_balances[member["id"]] -= base_share
                if i < remainder:
                    member_balances[member["id"]] -= 1

    # Convert to name-based dict
    result = {}
    for member in active_members:
        result[member["name"]] = member_balances[member["id"]]

    return result


def get_period_summary(period_id: int | None = None) -> dict:
    """
    Gets comprehensive summary of a period including transactions and balances.
    If period_id is None, uses the current active period.
    """
    if period_id is None:
        current_period = database.get_current_period()
        if current_period is None:
            return {}
        period_id = current_period["id"]

    period = database.get_period_by_id(period_id)
    if not period:
        return {}

    transactions = database.get_transactions_by_period(period_id)
    balances = get_period_balances(period_id)

    # Calculate totals
    total_deposits = sum(tx["amount"] for tx in transactions if tx["transaction_type"] == "deposit")
    total_expenses = sum(tx["amount"] for tx in transactions if tx["transaction_type"] == "expense")

    return {
        "period": period,
        "transactions": transactions,
        "balances": balances,
        "totals": {
            "deposits": total_deposits,
            "deposits_formatted": _cents_to_dollars(total_deposits),
            "expenses": total_expenses,
            "expenses_formatted": _cents_to_dollars(total_expenses),
            "net": total_deposits - total_expenses,
            "net_formatted": _cents_to_dollars(total_deposits - total_expenses),
        },
        "transaction_count": len(transactions),
    }


def settle_current_period(period_name: str | None = None) -> str:
    """
    Settles the current period and creates a new one.
    Returns a message describing what happened.
    """
    current_period = database.get_current_period()
    if not current_period:
        return "Error: No active period to settle."

    period_id = current_period["id"]
    period_summary = get_period_summary(period_id)

    # Settle the current period
    database.settle_period(period_id)

    # Create new period
    if period_name is None:
        from datetime import datetime

        period_name = datetime.now().strftime("%B %Y")  # e.g., "October 2025"

    new_period_id = database.create_new_period(period_name)
    new_period = database.get_period_by_id(new_period_id)

    # Reset remainder flags for new period
    database.reset_all_member_remainder_status()

    return (
        f"Period '{current_period['name']}' has been settled.\n"
        f"New period '{new_period['name']}' created.\n"
        f"Period totals: Deposits ${period_summary['totals']['deposits_formatted']}, "
        f"Expenses ${period_summary['totals']['expenses_formatted']}"
    )


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
