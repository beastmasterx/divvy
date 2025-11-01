from . import database
from .i18n import _

# --- Helper functions ---


def _cents_to_dollars(cents: int) -> str:
    """Converts an amount in cents to a dollar string (e.g., 12345 -> "123.45")."""
    return f"{cents / 100:.2f}"


def _dollars_to_cents(dollars_str: str) -> int:
    """Converts a dollar string to an amount in cents (e.g., "123.45" -> 12345)."""
    try:
        return int(float(dollars_str) * 100)
    except ValueError as err:
        raise ValueError(_("Invalid amount format. Please enter a number.")) from err


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
            return _("Error: Member '{}' already exists and is active.").format(name)
        else:
            return _("Error: Member '{}' exists but is inactive. Please use rejoin option.").format(name)

    # Add the new member
    new_member_id = database.add_member(name)
    if new_member_id is None:  # Should not happen if check for existing_member passed
        return _("Error: Could not add member '{}'.").format(name)

    return _("Member '{}' added successfully.").format(name)


def record_expense(
    description: str | None,
    amount_str: str,
    payer_name: str,
    category_name: str,
    is_personal: bool = False,
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
        return _("Error: Payer '{}' not found.").format(payer_name)
    payer_id_for_transaction = payer["id"]

    category = database.get_category_by_name(category_name)
    if not category:
        return _("Error: Category '{}' not found.").format(category_name)

    # For personal expenses, only the payer owes the amount (no split, no remainder logic)
    if is_personal:
        # Record the personal expense transaction
        database.add_transaction(
            transaction_type="expense",
            amount=amount_cents,
            description=description,
            payer_id=payer_id_for_transaction,
            category_id=category["id"],
            is_personal=True,
        )
        
        if description:
            return (
                _("Personal expense '{}' of {} recorded successfully.").format(
                    description,
                    _cents_to_dollars(amount_cents),
                )
            )
        else:
            return (
                _("Personal expense of {} recorded successfully.").format(
                    _cents_to_dollars(amount_cents),
                )
            )

    # For shared/individual expenses, split among active members
    active_members = database.get_active_members()
    if not active_members:
        return _("Error: No active members to split the expense among.")

    num_active_members = len(active_members)
    remainder = amount_cents % num_active_members

    remainder_payer_name = _("N/A")
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
            return _("Internal Error: Could not determine remainder payer.")

    # Record the expense transaction (not personal)
    database.add_transaction(
        transaction_type="expense",
        amount=amount_cents,
        description=description,
        payer_id=payer_id_for_transaction,
        category_id=category["id"],
        is_personal=False,
    )

    if description:
        return (
            _("Expense '{}' of {} recorded successfully. "
              "Remainder of {} assigned to {}.").format(
                description,
                _cents_to_dollars(amount_cents),
                _cents_to_dollars(remainder),
                remainder_payer_name,
            )
        )
    else:
        return (
            _("Expense of {} recorded successfully. "
              "Remainder of {} assigned to {}.").format(
                _cents_to_dollars(amount_cents),
                _cents_to_dollars(remainder),
                remainder_payer_name,
            )
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
        return _("Error: Payer '{}' not found.").format(payer_name)

    # Record the deposit transaction
    database.add_transaction(
        transaction_type="deposit",
        amount=amount_cents,
        description=description,
        payer_id=payer["id"],
        category_id=None,
    )

    if description:
        return (
            _("Deposit '{}' of {} from {} recorded successfully.").format(
                description,
                _cents_to_dollars(amount_cents),
                payer_name,
            )
        )
    else:
        return (
            _("Deposit of {} from {} recorded successfully.").format(
                _cents_to_dollars(amount_cents),
                payer_name,
            )
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
        return _("Error: Member '{}' not found.").format(recipient_name)

    # Record refund as negative deposit (reduces recipient's balance)
    # Note: We store as positive amount, but mark it as refund in description
    refund_base = _("Refund to {}").format(recipient_name)
    refund_desc = description if description else refund_base
    if not description or not description.startswith(_("Refund")):
        refund_desc = _("Refund: {}").format(refund_desc) if description else refund_base

    database.add_transaction(
        transaction_type="deposit",
        amount=-amount_cents,  # Negative amount for refund
        description=refund_desc,
        payer_id=recipient["id"],  # Recipient gets the refund
        category_id=None,
    )

    # Use original description for display, not refund_desc (which always has a value)
    if description:
        return (
            _("Refund '{}' of {} to {} recorded successfully.").format(
                description,
                _cents_to_dollars(amount_cents),
                recipient_name,
            )
        )
    else:
        return (
            _("Refund of {} to {} recorded successfully.").format(
                _cents_to_dollars(amount_cents),
                recipient_name,
            )
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
    virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)

    member_balances = {member["id"]: 0 for member in all_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    # Calculate initial contributions and expenses
    # Process transactions in chronological order to track public fund correctly
    for tx in all_transactions:
        if tx["transaction_type"] == "deposit":
            # Credit deposits to payer (including virtual member for public fund)
            if tx["payer_id"] and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]
            # If virtual member deposits, add to public fund
            if tx["payer_id"] and virtual_member and tx["payer_id"] == virtual_member["id"]:
                public_fund_balance += tx["amount"]
        elif tx["transaction_type"] == "expense":
            payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
            is_virtual = payer and database.is_virtual_member(payer)
            
            if is_virtual:
                # Shared expense: use public fund first, then split remainder
                expense_amount = tx["amount"]
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
                            member_balances[member["id"]] -= base_share
                            if i < remainder:
                                member_balances[member["id"]] -= 1
                continue
            
            # Handle personal expenses: only subtract from payer (NO credit for paying)
            if tx.get("is_personal", 0):  # Check if this is a personal expense
                if tx["payer_id"] and tx["payer_id"] in member_balances:
                    member_balances[tx["payer_id"]] -= tx["amount"]
                continue
            
            # Individual expense: credit real member for paying (not personal)
            if payer and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]

            # Distribute expense cost among current active members (individual split)
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
            formatted_balances[member_name] = _("Is owed {}").format(_cents_to_dollars(balance))
        elif balance < 0:
            formatted_balances[member_name] = _("Owes {}").format(_cents_to_dollars(abs(balance)))
        else:
            formatted_balances[member_name] = _("Settled")

    return formatted_balances


def remove_member(name: str) -> str:
    """
    Removes (deactivates) a member from the group.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if not member["is_active"]:
        return _("Error: Member '{}' is already inactive.").format(name)

    database.deactivate_member(member["id"])
    return _("Member '{}' has been removed (deactivated).").format(name)


def rejoin_member(name: str) -> str:
    """
    Rejoins (reactivates) an inactive member.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if member["is_active"]:
        return _("Error: Member '{}' is already active.").format(name)

    database.reactivate_member(member["id"])
    return _("Member '{}' has been reactivated (rejoined).").format(name)


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
    virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)

    # Calculate period balances
    member_balances = {member["id"]: 0 for member in all_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            # Credit deposits to payer (including virtual member for public fund)
            if tx["payer_id"] and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]
            # If virtual member deposits, add to public fund
            if tx["payer_id"] and virtual_member and tx["payer_id"] == virtual_member["id"]:
                public_fund_balance += tx["amount"]
        elif tx["transaction_type"] == "expense":
            payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
            is_virtual = payer and database.is_virtual_member(payer)
            
            if is_virtual:
                # Shared expense: use public fund first, then split remainder
                expense_amount = tx["amount"]
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
                            member_balances[member["id"]] -= base_share
                            if i < remainder:
                                member_balances[member["id"]] -= 1
                continue
            
            # Handle personal expenses: only subtract from payer (NO credit for paying)
            if tx.get("is_personal", 0):  # Check if this is a personal expense
                if tx["payer_id"] and tx["payer_id"] in member_balances:
                    member_balances[tx["payer_id"]] -= tx["amount"]
                continue
            
            # Individual expense: credit real member for paying (not personal)
            if payer and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]

            # Subtract shares from all active members (for both real and shared expenses)
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
            formatted_balances[member_name] = _("Is owed {}").format(_cents_to_dollars(balance))
        elif balance < 0:
            formatted_balances[member_name] = _("Owes {}").format(_cents_to_dollars(abs(balance)))
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
        period_id = current_period["id"]

    transactions = database.get_transactions_by_period(period_id)
    active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)

    # Calculate balances
    member_balances = {member["id"]: 0 for member in active_members}
    # Track public fund balance (virtual member's balance, can't go negative)
    public_fund_balance = 0

    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            # Credit deposits to payer (including virtual member for public fund)
            if tx["payer_id"] and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]
            # If virtual member deposits, add to public fund
            if tx["payer_id"] and virtual_member and tx["payer_id"] == virtual_member["id"]:
                public_fund_balance += tx["amount"]
        elif tx["transaction_type"] == "expense":
            payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
            is_virtual = payer and database.is_virtual_member(payer)
            
            if is_virtual:
                # Shared expense: use public fund first, then split remainder
                expense_amount = tx["amount"]
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
                            member_balances[member["id"]] -= base_share
                            if i < remainder:
                                member_balances[member["id"]] -= 1
                continue
            
            # Handle personal expenses: only subtract from payer (NO credit for paying)
            if tx.get("is_personal", 0):  # Check if this is a personal expense
                if tx["payer_id"] and tx["payer_id"] in member_balances:
                    member_balances[tx["payer_id"]] -= tx["amount"]
                continue
            
            # Individual expense: credit real member for paying (not personal)
            if payer and tx["payer_id"] in member_balances:
                member_balances[tx["payer_id"]] += tx["amount"]

            # Subtract shares from all active members (for both real and shared expenses)
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


def get_settlement_plan(period_id: int | None = None) -> list[dict]:
    """
    Calculates and returns the settlement plan without executing it.
    Returns a list of transaction-like dictionaries that would be created.
    Each dict has: date, transaction_type, amount, description, payer_id, payer_name, from_to_label
    """
    if period_id is None:
        current_period = database.get_current_period()
        if not current_period:
            return []
        period_id = current_period["id"]
    
    # Get balances before settlement
    member_balances_cents = get_active_member_balances(period_id)
    active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)
    
    # Calculate public fund balance
    transactions = database.get_transactions_by_period(period_id)
    public_fund_balance = 0
    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            if tx["payer_id"] and virtual_member and tx["payer_id"] == virtual_member["id"]:
                public_fund_balance += tx["amount"]
        elif tx["transaction_type"] == "expense":
            payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
            if payer and database.is_virtual_member(payer):
                expense_amount = tx["amount"]
                fund_used = min(expense_amount, public_fund_balance)
                public_fund_balance -= fund_used
    
    # Calculate settlement plan as transaction records
    from datetime import datetime
    settlement_date = datetime.now().strftime("%Y-%m-%d")
    settlement_transactions = []
    
    # Collect members who owe (negative balance) and who are owed (positive balance)
    debtors = []  # Members who owe money
    creditors = []  # Members who are owed money
    
    for member in active_members:
        balance = member_balances_cents.get(member["name"], 0)
        if balance < 0:
            debtors.append((member, abs(balance)))
        elif balance > 0:
            creditors.append((member, balance))
    
    # Handle public fund - if there's remaining balance, distribute it
    if public_fund_balance > 0:
        if creditors:
            # Distribute public fund to first creditor
            creditor, creditor_balance = creditors[0]
            # Fund distribution creates a refund (negative deposit) to creditor
            settlement_transactions.append({
                "date": settlement_date,
                "transaction_type": "deposit",  # Will be displayed as Refund due to negative amount
                "amount": -public_fund_balance,
                "description": _("Settlement: Public fund distribution"),
                "payer_id": creditor["id"],
                "payer_name": creditor["name"],
                "from_to": "To",
            })
    
    # Calculate debt settlements: debtors pay creditors
    # Match debtors with creditors to create settlement plan
    debtor_idx = 0
    creditor_idx = 0
    
    # Create working copies for planning (without modifying originals)
    working_debtors = [(debtor, debt_amt) for debtor, debt_amt in debtors]
    working_creditors = [(creditor, credit_amt) for creditor, credit_amt in creditors]
    
    while debtor_idx < len(working_debtors) and creditor_idx < len(working_creditors):
        debtor, debt_amount = working_debtors[debtor_idx]
        creditor, credit_amount = working_creditors[creditor_idx]
        
        settlement_amount = min(debt_amount, credit_amount)
        
        # Debtor makes payment (positive deposit)
        settlement_transactions.append({
            "date": settlement_date,
            "transaction_type": "deposit",
            "amount": settlement_amount,
            "description": _("Settlement payment to {}").format(creditor["name"]),
            "payer_id": debtor["id"],
            "payer_name": debtor["name"],
            "from_to": "From",
        })
        
        # Creditor receives payment (negative deposit, shown as refund)
        settlement_transactions.append({
            "date": settlement_date,
            "transaction_type": "deposit",  # Will be displayed as Refund due to negative amount
            "amount": -settlement_amount,
            "description": _("Settlement payment from {}").format(debtor["name"]),
            "payer_id": creditor["id"],
            "payer_name": creditor["name"],
            "from_to": "To",
        })
        
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
    
    return settlement_transactions


def settle_current_period(period_name: str | None = None) -> str:
    """
    Settles the current period by creating settlement transactions to zero all balances,
    then creates a new period.
    Returns a message describing what happened.
    """
    current_period = database.get_current_period()
    if not current_period:
        return _("Error: No active period to settle.")

    period_id = current_period["id"]
    
    # Get balances before settlement
    member_balances_cents = get_active_member_balances(period_id)
    active_members = database.get_active_members()
    virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)
    
    # Calculate public fund balance
    transactions = database.get_transactions_by_period(period_id)
    public_fund_balance = 0
    for tx in transactions:
        if tx["transaction_type"] == "deposit":
            if tx["payer_id"] and virtual_member and tx["payer_id"] == virtual_member["id"]:
                public_fund_balance += tx["amount"]
        elif tx["transaction_type"] == "expense":
            payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
            if payer and database.is_virtual_member(payer):
                expense_amount = tx["amount"]
                fund_used = min(expense_amount, public_fund_balance)
                public_fund_balance -= fund_used
    
    # Create settlement transactions to zero balances
    settlement_messages = []
    total_owed = 0
    total_owing = 0
    
    # Collect members who owe (negative balance) and who are owed (positive balance)
    debtors = []  # Members who owe money
    creditors = []  # Members who are owed money
    
    for member in active_members:
        balance = member_balances_cents.get(member["name"], 0)
        if balance < 0:
            debtors.append((member, abs(balance)))
            total_owing += abs(balance)
        elif balance > 0:
            creditors.append((member, balance))
            total_owed += balance
    
    # Handle public fund - if there's remaining balance, distribute it
    if public_fund_balance > 0:
        if creditors:
            # Distribute public fund to creditors proportionally or to first creditor
            # Simple approach: give all to first creditor
            creditor, creditor_balance = creditors[0]
            # Negative deposit to creditor reduces their positive balance (they receive the fund)
            database.add_transaction(
                transaction_type="deposit",
                amount=-public_fund_balance,
                description=_("Settlement: Public fund distribution"),
                payer_id=creditor["id"],
                period_id=period_id,
            )
            settlement_messages.append(
                _("  Public fund ${} distributed to {}").format(
                    _cents_to_dollars(public_fund_balance), creditor["name"]
                )
            )
    
    # Settle debts: debtors pay creditors
    # Match debtors with creditors to create settlement transactions
    debtor_idx = 0
    creditor_idx = 0
    
    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor, debt_amount = debtors[debtor_idx]
        creditor, credit_amount = creditors[creditor_idx]
        
        settlement_amount = min(debt_amount, credit_amount)
        settlement_amount_str = _cents_to_dollars(settlement_amount)
        
        # Record settlement: debtor pays, creditor receives
        # Create matching transactions that zero both balances:
        # 1. Creditor receives payment (negative deposit reduces creditor's positive balance)
        # 2. Debtor makes payment (positive deposit reduces debtor's negative balance)
        
        # Creditor receives payment (negative deposit decreases their positive balance)
        database.add_transaction(
            transaction_type="deposit",
            amount=-settlement_amount,
            description=_("Settlement payment from {}").format(debtor["name"]),
            payer_id=creditor["id"],
            period_id=period_id,
        )
        
        # Debtor makes payment (positive deposit reduces their negative balance toward zero)
        database.add_transaction(
            transaction_type="deposit",
            amount=settlement_amount,
            description=_("Settlement payment to {}").format(creditor["name"]),
            payer_id=debtor["id"],
            period_id=period_id,
        )
        
        settlement_messages.append(
            _("  {} pays ${} to {}").format(
                debtor["name"],
                settlement_amount_str,
                creditor["name"],
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
    
    # Zero out any remaining creditor balances using public fund if available
    # (This handles cases where total owed > total owing + public fund)
    # Note: Public fund was already distributed above, so remaining credits should match public fund distribution
    
    # Settle the period
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
        _("Period '{}' has been settled.\n"
          "New period '{}' created.").format(
            current_period["name"],
            new_period["name"],
        )
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
