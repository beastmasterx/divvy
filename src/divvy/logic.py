from . import database

# --- Helper functions ---

def _cents_to_dollars(cents: int) -> str:
    """Converts an amount in cents to a dollar string (e.g., 12345 -> "123.45")."""
    return f"{cents / 100:.2f}"

def _dollars_to_cents(dollars_str: str) -> int:
    """Converts a dollar string to an amount in cents (e.g., "123.45" -> 12345)."""
    try:
        return int(float(dollars_str) * 100)
    except ValueError:
        raise ValueError("Invalid amount format. Please enter a number.")

# --- Business logic functions ---

def add_new_member(name: str) -> str:
    """
    Adds a new member to the group.
    - Calculates the required buy-in to the public fund.
    - Adds the member to the database.
    - Records the buy-in as a deposit transaction.
    """
    existing_member = database.get_member_by_name(name)
    if existing_member:
        return f"Error: Member '{name}' already exists."

    # Calculate buy-in
    public_fund_balance = database.get_public_fund_balance()
    active_members = database.get_active_members()
    num_active_members = len(active_members)

    buy_in_amount = 0
    if num_active_members > 0: # If there are existing members, calculate buy-in
        buy_in_amount = public_fund_balance // num_active_members
    
    # Add the new member
    new_member_id = database.add_member(name)
    if new_member_id is None: # Should not happen if check for existing_member passed
        return f"Error: Could not add member '{name}'."

    # Record buy-in if applicable
    if buy_in_amount > 0:
        database.add_transaction(
            transaction_type='deposit',
            description=f"Buy-in for {name}",
            amount=buy_in_amount,
            payer_id=new_member_id
        )
        return f"Member '{name}' added successfully. Buy-in of {_cents_to_dollars(buy_in_amount)} recorded."
    else:
        return f"Member '{name}' added successfully. No buy-in required as public fund is empty or no other active members."

def record_expense(description: str, amount_str: str, payer_name: str, category_name: str, remark: str | None = None) -> str:
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

    payer_id_for_transaction = None
    if payer_name.lower() == "public fund":
        payer_id_for_transaction = None # Public fund pays
    else:
        payer = database.get_member_by_name(payer_name)
        if not payer:
            return f"Error: Payer '{payer_name}' not found."
        payer_id_for_transaction = payer['id']
    
    category = database.get_category_by_name(category_name)
    if not category:
        return f"Error: Category '{category_name}' not found."

    active_members = database.get_active_members()
    if not active_members:
        return "Error: No active members to split the expense among."

    num_active_members = len(active_members)
    base_share = amount_cents // num_active_members
    remainder = amount_cents % num_active_members

    remainder_payer_name = 'N/A'
    remainder_payer_id = None

    if remainder > 0: # Only assign remainder if there is one
        # First, check if all members have paid a remainder in the current cycle
        all_paid_remainder = True
        for member in active_members:
            if not member['paid_remainder_in_cycle']:
                all_paid_remainder = False
                break
        
        if all_paid_remainder:
            database.reset_all_member_remainder_status()
            # Re-fetch active members after reset to get updated status
            active_members = database.get_active_members()

        # Find the next member to pay the remainder
        for member in active_members:
            if not member['paid_remainder_in_cycle']:
                remainder_payer_id = member['id']
                remainder_payer_name = member['name']
                database.update_member_remainder_status(member['id'], True)
                break
        
        if remainder_payer_id is None: # Should not happen if logic is correct and active_members is not empty
            return "Internal Error: Could not determine remainder payer."

    # Record the expense transaction
    database.add_transaction(
        transaction_type='expense',
        description=description,
        amount=amount_cents,
        payer_id=payer_id_for_transaction,
        category_id=category['id'],
        remark=remark
    )

    return f"Expense '{description}' of {_cents_to_dollars(amount_cents)} recorded successfully. Remainder of {_cents_to_dollars(remainder)} assigned to {remainder_payer_name}."

def get_settlement_balances() -> dict[str, str]:
    """
    Calculates and returns the final settlement balances for all members.
    - For each member, calculates total paid vs. total share.
    - Determines who owes money and who is owed money.
    """
    all_members = database.get_all_members()
    all_transactions = database.get_all_transactions()
    current_active_members = database.get_active_members()
    
    member_balances = {member['id']: 0 for member in all_members}
    
    # Calculate initial contributions and expenses
    for tx in all_transactions:
        if tx['transaction_type'] == 'deposit':
            if tx['payer_id']:
                member_balances[tx['payer_id']] += tx['amount']
        elif tx['transaction_type'] == 'expense':
            if tx['payer_id']:
                member_balances[tx['payer_id']] += tx['amount']
            
            # Distribute expense cost among current active members
            num_active = len(current_active_members)
            if num_active == 0: # Should not happen if record_expense prevents it
                continue
            
            base_share = tx['amount'] // num_active
            remainder = tx['amount'] % num_active
            
            for i, member in enumerate(current_active_members):
                member_balances[member['id']] -= base_share
                if i < remainder: # Distribute remainder sequentially for historical expenses
                    member_balances[member['id']] -= 1

    # Format balances for display
    formatted_balances = {}
    for member_id, balance in member_balances.items():
        member_name = database.get_member_by_id(member_id)['name']
        if balance > 0:
            formatted_balances[member_name] = f"Is owed {_cents_to_dollars(balance)}"
        elif balance < 0:
            formatted_balances[member_name] = f"Owes {_cents_to_dollars(abs(balance))}"
        else:
            formatted_balances[member_name] = "Settled"
            
    return formatted_balances