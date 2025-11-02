from . import database, logic
from .config import load_env_files
from .i18n import _, set_language, translate_category, translate_transaction_type


def _get_display_width(text: str) -> int:
    """
    Calculate display width of text for table alignment.
    Chinese/wide characters count as 2, ASCII as 1.
    """
    width = 0
    for char in text:
        # Check if character is wide (Chinese, Japanese, Korean, etc.)
        # Unicode ranges for wide characters
        if ord(char) > 0x1100:
            # Wide characters (CJK, emoji, etc.) - approximate check
            if (
                (0x2E80 <= ord(char) <= 0x9FFF) or  # CJK
                (0xAC00 <= ord(char) <= 0xD7AF) or  # Hangul
                (0x3040 <= ord(char) <= 0x309F) or  # Hiragana
                (0x30A0 <= ord(char) <= 0x30FF) or  # Katakana
                ord(char) > 0xFF00  # Fullwidth chars
            ):
                width += 2
            else:
                width += 1
        else:
            width += 1
    return width


def _pad_to_display_width(text: str, target_width: int, align: str = "<") -> str:
    """
    Pad text to target display width, accounting for wide characters.
    align: '<' for left, '>' for right, '^' for center
    """
    current_width = _get_display_width(text)
    if current_width >= target_width:
        return text
    
    padding_needed = target_width - current_width
    
    if align == "<":
        return text + " " * padding_needed
    elif align == ">":
        return " " * padding_needed + text
    elif align == "^":
        left_pad = padding_needed // 2
        right_pad = padding_needed - left_pad
        return " " * left_pad + text + " " * right_pad
    else:
        return text + " " * padding_needed


def select_from_list(items: list[dict], name_key: str, prompt: str) -> dict | None:
    """Displays a numbered list and returns the selected item."""
    if not items:
        print(_("No {} available.").format(prompt.lower()))
        return None

    print(_("\n--- Select {} ---").format(prompt))
    for i, item in enumerate(items, 1):
        print(f"{i}. {item[name_key]}")
    print(_("------------------------"))

    while True:
        try:
            choice = input(_("Enter your choice (1-{}): ").format(len(items))).strip()
            if not choice:
                print(_("Input cannot be empty. Please enter a number."))
                continue
            index = int(choice) - 1
            if 0 <= index < len(items):
                return items[index]
            else:
                print(_("Invalid choice. Please enter a number between 1 and {}.").format(len(items)))
        except ValueError:
            print(_("Invalid input. Please enter a number."))
        except KeyboardInterrupt:
            return None


def _display_settlement_plan(settlement_transactions: list[dict]) -> None:
    """Displays settlement plan transactions in table format."""
    from .i18n import translate_transaction_type
    
    if not settlement_transactions:
        print(_("No settlement transactions needed (all balances already zero)."))
        return
    
    print(_("\n--- Settlement Plan ---"))
    
    # Prepare transactions with all needed data
    transactions_data = []
    for tx in settlement_transactions:
        # Category is blank for settlement transactions
        category_name = ""
        
        date_only = tx["date"]
        
        # Determine transaction type for display
        amount_cents = tx["amount"]
        if amount_cents < 0:
            # Negative deposit = Refund
            tx_type = translate_transaction_type("refund")
            amount_formatted = logic._cents_to_dollars(abs(amount_cents))
            amount_sign = "-"
        else:
            # Positive deposit = Deposit
            tx_type = translate_transaction_type("deposit")
            amount_formatted = logic._cents_to_dollars(amount_cents)
            amount_sign = "+"
        
        desc = tx["description"] if tx["description"] else ""
        
        payer_name = tx.get("payer_name", _("Unknown"))
        from_to = tx.get("from_to", "")
        
        # Format "From: Name" or "To: Name"
        if from_to == "From":
            from_to_display = _("From: {}").format(payer_name)
        elif from_to == "To":
            from_to_display = _("To: {}").format(payer_name)
        else:
            from_to_display = payer_name
        
        transactions_data.append(
            {
                "date": date_only,
                "category": category_name,
                "type": tx_type,
                "personal": "",  # Blank for settlement
                "amount": amount_cents,
                "amount_formatted": f"{amount_sign}{amount_formatted}",
                "description": desc,
                "payer": from_to_display,
            }
        )
    
    # Calculate column widths using display width (not character count)
    max_category_width = (
        max(_get_display_width(t["category"]) for t in transactions_data) if transactions_data else 10
    )
    max_desc_width = (
        max(_get_display_width(t["description"]) for t in transactions_data) if transactions_data else 10
    )
    max_payer_width = max(_get_display_width(t["payer"]) for t in transactions_data) if transactions_data else 8
    
    # Use display width for headers too
    header_date = _("Date")
    header_category = _("Category")
    header_type = _("Type")
    header_split = _("Split")
    header_amount = _("Amount")
    header_description = _("Description")
    header_from_to = _("From/To")
    
    category_width = max(max_category_width, _get_display_width(header_category))
    desc_width = max(max_desc_width, _get_display_width(header_description))
    payer_width = max(max_payer_width, _get_display_width(header_from_to))
    split_width = max(10, _get_display_width(header_split))
    
    # Ensure minimum widths
    category_width = max(15, category_width)
    desc_width = max(20, desc_width)
    payer_width = max(12, payer_width)
    
    # Print header with proper padding for display width
    header_line = (
        f"  {_pad_to_display_width(header_date, 12)} | "
        f"{_pad_to_display_width(header_category, category_width)} | "
        f"{_pad_to_display_width(header_type, 8)} | "
        f"{_pad_to_display_width(header_split, split_width)} | "
        f"{_pad_to_display_width(header_amount, 12, '>')} | "
        f"{_pad_to_display_width(header_description, desc_width)} | "
        f"{_pad_to_display_width(header_from_to, payer_width)}"
    )
    print(header_line)
    print(
        f"  {'-' * 12} | {'-' * category_width} | {'-' * 8} | {'-' * split_width} | {'-' * 12} | {'-' * desc_width} | {'-' * payer_width}"
    )
    
    # Print transactions with proper padding for display width
    for tx in transactions_data:
        desc_display = tx["description"] if tx["description"] else ""
        tx_line = (
            f"  {_pad_to_display_width(tx['date'], 12)} | "
            f"{_pad_to_display_width(tx['category'], category_width)} | "
            f"{_pad_to_display_width(tx['type'], 8)} | "
            f"{_pad_to_display_width(tx['personal'], split_width)} | "
            f"{_pad_to_display_width(tx['amount_formatted'], 12, '>')} | "
            f"{_pad_to_display_width(desc_display, desc_width)} | "
            f"{_pad_to_display_width(tx['payer'], payer_width)}"
        )
        print(tx_line)
    
    print(_("----------------------\n"))


def _display_view_period(period_id: int | None = None) -> None:
    """Displays the combined period view with transactions and active member balances.
    
    Args:
        period_id: Optional period ID to display. If None, displays the current active period.
    """
    summary = logic.get_period_summary(period_id)

    if not summary or not summary.get("period"):
        if period_id is None:
            print(_("No active period found."))
        else:
            print(_("Period not found."))
        return

    period = summary["period"]
    transactions = summary["transactions"]
    totals = summary["totals"]

    # Get active members with balances
    active_members = database.get_active_members()
    active_balances = logic.get_active_member_balances(period["id"])

    # Calculate public fund balance for the period
    virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)
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

    # Format deposits and expenses with signs
    deposits_formatted = f"+{totals['deposits_formatted']}"
    expenses_formatted = f"-{totals['expenses_formatted']}"
    fund_formatted = logic._cents_to_dollars(public_fund_balance)
    fund_sign = "+" if public_fund_balance >= 0 else "-"

    print("\n" + "=" * 60)
    print(_("                 {}").format(period["name"]))
    print("=" * 60)
    # Extract date only from start_date (handle both datetime objects and strings)
    start_date = period["start_date"]
    if hasattr(start_date, "strftime"):
        # datetime object
        start_date_only = start_date.strftime("%Y-%m-%d")
    else:
        # string (backwards compatibility)
        start_date_only = start_date.split()[0] if " " in str(start_date) else str(start_date)
    
    if period["is_settled"] and period.get("settled_date"):
        # Settled period: show settlement date
        settled_date = period["settled_date"]
        if hasattr(settled_date, "strftime"):
            settled_date_only = settled_date.strftime("%Y-%m-%d")
        else:
            settled_date_only = settled_date.split()[0] if " " in str(settled_date) else str(settled_date)
        print(
            _("Started: {} | Settled: {}").format(
                start_date_only, settled_date_only
            )
        )
    elif period["is_settled"] and period.get("end_date"):
        # Fallback to end_date if settled_date is not available
        end_date = period["end_date"]
        if hasattr(end_date, "strftime"):
            end_date_only = end_date.strftime("%Y-%m-%d")
        else:
            end_date_only = end_date.split()[0] if " " in str(end_date) else str(end_date)
        print(
            _("Started: {} | Settled: {}").format(
                start_date_only, end_date_only
            )
        )
    else:
        # Active period: show active status
        print(
            _("Started: {} | Active").format(start_date_only)
        )
    print(
        _("Deposits: {} | Expenses: {} | Fund: {}{}").format(
            deposits_formatted, expenses_formatted, fund_sign, fund_formatted
        )
    )

    # Transactions with headers
    if transactions:
        print(_("\n--- Transactions ({}) ---").format(len(transactions)))

        # Prepare transactions with all needed data
        transactions_data = []
        for tx in transactions:
            # Category: only show for expenses, blank for deposits/refunds
            category_name = ""
            if tx["transaction_type"] == "expense" and tx["category_id"]:
                category = database.get_category_by_id(tx["category_id"])
                if category:
                    category_name = translate_category(category["name"])
                else:
                    category_name = _("Category ID {}").format(tx["category_id"])
            # For deposits/refunds, leave category blank (not "Uncategorized")

            # SQLite column names: check for TIMESTAMP (as defined in schema) or lowercase variant
            timestamp = tx.get("TIMESTAMP", tx.get("timestamp", ""))
            # Handle both datetime objects and strings
            if hasattr(timestamp, "strftime"):
                date_only = timestamp.strftime("%Y-%m-%d")
            else:
                timestamp_str = str(timestamp)
                date_only = timestamp_str.split()[0] if " " in timestamp_str else timestamp_str

            tx_type = translate_transaction_type(tx["transaction_type"])
            amount_cents = tx["amount"]

            # Handle amount sign: negative amounts (refunds) show as negative
            # Positive deposits show as positive, expenses show as negative
            if amount_cents < 0:
                # Refund (negative deposit)
                amount_formatted = logic._cents_to_dollars(abs(amount_cents))
                amount_sign = "-"
                tx_type = translate_transaction_type("refund")  # Show as Refund type for clarity
            elif tx["transaction_type"] == "deposit":
                amount_formatted = logic._cents_to_dollars(amount_cents)
                amount_sign = "+"
            else:  # expense
                amount_formatted = logic._cents_to_dollars(amount_cents)
                amount_sign = "-"

            desc = tx["description"] if tx["description"] else ""

            payer_name = _("Unknown")
            from_to_display = ""
            if tx["payer_id"]:
                payer = database.get_member_by_id(tx["payer_id"])
                if payer:
                    payer_name = database.get_member_display_name(payer)
                else:
                    payer_name = _("Member ID {}").format(tx["payer_id"])
            
            # Format payer column: use From/To for deposits/refunds, Payer for expenses
            if tx["transaction_type"] == "expense":
                # For expenses, show "Payer: Name"
                from_to_display = _("Payer: {}").format(payer_name)
            elif tx["transaction_type"] == "deposit":
                if amount_cents < 0:
                    # Negative deposit = Refund, show "To: Name"
                    from_to_display = _("To: {}").format(payer_name)
                else:
                    # Positive deposit, show "From: Name"
                    from_to_display = _("From: {}").format(payer_name)
            else:
                # Fallback
                from_to_display = payer_name

            # Determine expense type display for Split column
            split_type_display = ""
            if tx["transaction_type"] == "expense":
                payer = database.get_member_by_id(tx["payer_id"]) if tx["payer_id"] else None
                is_virtual = payer and database.is_virtual_member(payer)
                
                if is_virtual:
                    split_type_display = _("Shared")
                elif tx.get("is_personal", 0):
                    split_type_display = _("Personal")
                else:
                    split_type_display = _("Individual")
            
            transactions_data.append(
                {
                    "date": date_only,
                    "category": category_name,
                    "type": tx_type,
                    "personal": split_type_display,
                    "amount": amount_cents,
                    "amount_formatted": f"{amount_sign}{amount_formatted}",
                    "description": desc,
                    "payer": from_to_display,
                }
            )

        # Sort by date, category, type, payer
        transactions_data.sort(key=lambda x: (x["date"], x["category"], x["type"], x["payer"]))

        # Calculate column widths using display width (not character count)
        max_category_width = (
            max(_get_display_width(t["category"]) for t in transactions_data) if transactions_data else 10
        )
        max_desc_width = (
            max(_get_display_width(t["description"]) for t in transactions_data) if transactions_data else 10
        )
        max_payer_width = max(_get_display_width(t["payer"]) for t in transactions_data) if transactions_data else 8
        max_split_width = max(_get_display_width(t["personal"]) for t in transactions_data) if transactions_data else 0
        
        # Use display width for headers too
        header_date = _("Date")
        header_category = _("Category")
        header_type = _("Type")
        header_split = _("Split")
        header_amount = _("Amount")
        header_description = _("Description")
        header_from_to = _("From/To")
        
        category_width = max(max_category_width, _get_display_width(header_category))
        desc_width = max(max_desc_width, _get_display_width(header_description))
        payer_width = max(max_payer_width, _get_display_width(header_from_to))
        split_width = max(max_split_width, _get_display_width(header_split))
        
        # Ensure minimum widths
        category_width = max(15, category_width)
        desc_width = max(20, desc_width)
        payer_width = max(12, payer_width)
        split_width = max(10, split_width)
        
        # Print header with proper padding for display width
        header_line = (
            f"  {_pad_to_display_width(header_date, 12)} | "
            f"{_pad_to_display_width(header_category, category_width)} | "
            f"{_pad_to_display_width(header_type, 8)} | "
            f"{_pad_to_display_width(header_split, split_width)} | "
            f"{_pad_to_display_width(header_amount, 12, '>')} | "
            f"{_pad_to_display_width(header_description, desc_width)} | "
            f"{_pad_to_display_width(header_from_to, payer_width)}"
        )
        print(header_line)
        print(
            f"  {'-' * 12} | {'-' * category_width} | {'-' * 8} | {'-' * split_width} | {'-' * 12} | {'-' * desc_width} | {'-' * payer_width}"
        )

        # Print transactions with proper padding for display width
        for tx in transactions_data:
            desc_display = tx["description"] if tx["description"] else ""
            tx_line = (
                f"  {_pad_to_display_width(tx['date'], 12)} | "
                f"{_pad_to_display_width(tx['category'], category_width)} | "
                f"{_pad_to_display_width(tx['type'], 8)} | "
                f"{_pad_to_display_width(tx['personal'], split_width)} | "
                f"{_pad_to_display_width(tx['amount_formatted'], 12, '>')} | "
                f"{_pad_to_display_width(desc_display, desc_width)} | "
                f"{_pad_to_display_width(tx['payer'], payer_width)}"
            )
            print(tx_line)
    else:
        print(_("\n--- Transactions (0) ---"))
        print(_("  No transactions in this period."))

    # Active members with balances
    if active_members:
        print(_("\n--- Balances ({} active) ---").format(len(active_members)))
        member_strings = []
        for member in active_members:
            balance_cents = active_balances.get(member["name"], 0)
            balance_formatted = logic._cents_to_dollars(abs(balance_cents))
            balance_sign = "+" if balance_cents >= 0 else "-"
            remainder_str = "✓" if member["paid_remainder_in_cycle"] else "✗"
            member_strings.append(
                f"{member['name']} {remainder_str} {balance_sign}${balance_formatted}"
            )
        print("  " + " | ".join(member_strings))
    else:
        print(_("\n--- Balances (0 active) ---"))
        print(_("  No active members."))

    print("\n" + "=" * 60 + "\n")


def select_period() -> dict | None:
    """Selects a period from all periods, showing the current active period by default.
    Returns the selected period dict, or None if cancelled.
    If user presses Enter without input and there's a current period, returns the current period.
    """
    all_periods = database.get_all_periods()
    
    if not all_periods:
        print(_("No periods available."))
        return None
    
    current_period = database.get_current_period()
    current_period_id = current_period["id"] if current_period else None
    
    # Create display strings for periods
    periods_for_display = []
    for period in all_periods:
        # Extract date only from start_date (handle both datetime objects and strings)
        start_date = period["start_date"]
        if hasattr(start_date, "strftime"):
            # datetime object
            start_date_only = start_date.strftime("%Y-%m-%d")
        else:
            # string (backwards compatibility)
            start_date_only = start_date.split()[0] if " " in str(start_date) else str(start_date)
        status = _("Active") if not period["is_settled"] else _("Settled")
        
        # Mark the current active period
        is_current = (current_period_id is not None and period["id"] == current_period_id)
        marker = _(" [Current]") if is_current else ""
        
        display_name = f"{period['name']} ({start_date_only}, {status}){marker}"
        periods_for_display.append({
            **period,
            "display_name": display_name
        })
    
    # Sort so current period appears first
    if current_period_id:
        periods_for_display.sort(key=lambda p: (p["id"] != current_period_id, -p["id"]))
    
    # Display the list with a hint about the default
    if not periods_for_display:
        print(_("No periods available."))
        return None
    
    print(_("\n--- Select {} ---").format(_("Period")))
    for i, period in enumerate(periods_for_display, 1):
        default_hint = " (default)" if i == 1 and current_period_id else ""
        print(f"{i}. {period['display_name']}{default_hint}")
    print(_("------------------------"))
    
    # Allow Enter to select default (first item, which is current period)
    while True:
        try:
            choice = input(_("Enter your choice (1-{}, or Enter for default): ").format(len(periods_for_display))).strip()
            if not choice:
                # Empty input - return default (current period) if available
                if current_period_id and periods_for_display:
                    return periods_for_display[0]
                print(_("Input cannot be empty. Please enter a number."))
                continue
            index = int(choice) - 1
            if 0 <= index < len(periods_for_display):
                return periods_for_display[index]
            else:
                print(_("Invalid choice. Please enter a number between 1 and {}.").format(len(periods_for_display)))
        except ValueError:
            print(_("Invalid input. Please enter a number."))
        except KeyboardInterrupt:
            return None


def select_payer(for_expense: bool = False) -> str | None:
    """Selects a payer from active members.
    For deposits, includes virtual member (Group) as an option for public fund.
    For expenses, only shows regular active members."""
    members = database.get_active_members()

    if not members:
        print(_("No active members available."))
        return None

    # For deposits, add virtual member as an option for public fund
    if not for_expense:
        virtual_member = database.get_member_by_name(database.PUBLIC_FUND_MEMBER_INTERNAL_NAME)
        if virtual_member:
            # Create a display version with translated name
            members_with_group = members + [
                {**virtual_member, "name": database.get_member_display_name(virtual_member)}
            ]
            payer = select_from_list(members_with_group, "name", _("Payer"))
            if payer:
                # Return internal name if virtual member selected
                if payer.get("id") == virtual_member["id"]:
                    return database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
                return payer["name"]
            return None

    payer = select_from_list(members, "name", _("Payer"))
    return payer["name"] if payer else None


def show_menu():
    """Prints the main menu."""
    try:
        current_period = database.get_current_period()
        period_name = current_period["name"] if current_period else _("None")
    except Exception:
        # If database not ready yet, show default
        period_name = _("Initializing...")

    print(_("\n--- Divvy Expense Splitter ---"))
    print(_("Current Period: {}").format(period_name))
    print(_("1. Add Expense"))
    print(_("2. Add Deposit"))
    print(_("3. Add Refund"))
    print(_("4. View Period"))
    print(_("5. Close period"))
    print(_("6. Add member"))
    print(_("7. Remove Member"))
    print(_("8. Exit"))
    print(_("-----------------------------"))


def main():
    """The main function and entry point for the CLI application."""
    # Load environment variables from .env files
    # Supports environment-specific files like .env.dev, .env.production, etc.
    load_env_files(verbose=True)
    
    # Ensure the database is initialized before starting
    database.initialize_database()
    
    # Initialize language (can be overridden by environment variable)
    set_language()

    while True:
        show_menu()
        choice = input(_("Enter your choice: "))

        if choice == "1":
            description = input(_("Enter expense description (optional): "))
            amount_str = input(_("Enter total amount: ")).strip()

            if not amount_str:
                print(_("Error: Amount cannot be empty."))
                continue

            # Ask if it's a shared expense or personal expense
            expense_type = input(_("Expense type - (s)hared, (p)ersonal, or (i)ndividual split? (default: i): ")).strip().lower()

            if expense_type in ("s", "shared"):
                payer_name = database.PUBLIC_FUND_MEMBER_INTERNAL_NAME
                is_personal = False
            elif expense_type in ("p", "personal"):
                payer_name = select_payer(for_expense=True)
                if payer_name is None:
                    print(_("Expense recording cancelled."))
                    continue
                is_personal = True
            else:  # individual (default)
                payer_name = select_payer(for_expense=True)
                if payer_name is None:
                    print(_("Expense recording cancelled."))
                    continue
                is_personal = False

            categories = database.get_all_categories()
            # Create a display version with translated names but keep original for lookup
            categories_for_display = [
                {**cat, "display_name": translate_category(cat["name"])} for cat in categories
            ]
            category = select_from_list(categories_for_display, "display_name", _("Category"))
            if category is None:
                print(_("Expense recording cancelled."))
                continue
            category_name = category["name"]  # Use original name for database lookup

            desc = description if description else None
            result = logic.record_expense(desc, amount_str, payer_name, category_name, is_personal=is_personal)
            print(result)

        elif choice == "2":
            description = input(_("Enter deposit description (optional): "))
            amount_str = input(_("Enter deposit amount: ")).strip()

            if not amount_str:
                print(_("Error: Amount cannot be empty."))
                continue

            payer_name = select_payer(for_expense=False)
            if payer_name is None:
                print(_("Deposit recording cancelled."))
                continue

            desc = description if description else None
            result = logic.record_deposit(desc, amount_str, payer_name)
            print(result)

        elif choice == "3":
            # Add Refund
            all_members_list = database.get_all_members()
            if not all_members_list:
                print(_("No members available."))
                continue

            member = select_from_list(all_members_list, "name", _("Member to refund"))
            if member is None:
                print(_("Refund cancelled."))
                continue

            description = input(_("Enter refund description (optional): "))
            amount_str = input(_("Enter refund amount: ")).strip()

            if not amount_str:
                print(_("Error: Amount cannot be empty."))
                continue

            desc = description if description else None
            result = logic.record_refund(desc, amount_str, member["name"])
            print(result)

        elif choice == "4":
            # Select a period to view (defaults to current active)
            selected_period = select_period()
            if selected_period:
                _display_view_period(selected_period["id"])
            else:
                print(_("Period selection cancelled."))

        elif choice == "5":
            # Show period status first
            _display_view_period()

            # Show settlement plan before asking for confirmation
            current_period = database.get_current_period()
            if current_period:
                settlement_plan = logic.get_settlement_plan(current_period["id"])
                if settlement_plan:
                    _display_settlement_plan(settlement_plan)
                else:
                    print(_("\nNo settlement transactions needed (all balances already zero).\n"))

            # Ask for confirmation
            response = input(_("Close this period? (y/n): "))
            if response.lower() not in ("y", "yes"):
                print(_("Period closing cancelled."))
                continue

            # Get new period name
            period_name = input(
                _("Enter name for new period (press Enter for auto-generated): ")
            ).strip()
            if not period_name:
                period_name = None

            result = logic.settle_current_period(period_name)
            print(result)

        elif choice == "6":
            name = input(_("Enter the member's name: "))
            name = name.strip()

            if not name:
                print(_("Member name cannot be empty."))
                continue

            # Check if member exists
            existing_member = database.get_member_by_name(name)

            if existing_member:
                if existing_member["is_active"]:
                    print(_("Error: Member '{}' already exists and is active.").format(name))
                else:
                    # Member is inactive - ask to rejoin
                    response = input(_("Member '{}' is inactive. Rejoin? (y/n): ").format(name))
                    if response.lower() in ("y", "yes"):
                        result = logic.rejoin_member(name)
                        print(result)
                    else:
                        print(_("Rejoin cancelled."))
            else:
                # New member - add normally
                result = logic.add_new_member(name)
                print(result)

        elif choice == "7":
            members = database.get_active_members()
            if not members:
                print(_("No active members to remove."))
                continue

            # Show current period status first
            _display_view_period()

            member = select_from_list(members, "name", _("Member to remove"))
            if member is None:
                print(_("Member removal cancelled."))
                continue

            # Get member's current balance
            active_balances = logic.get_active_member_balances()
            member_balance_cents = active_balances.get(member["name"], 0)
            member_balance_formatted = logic._cents_to_dollars(abs(member_balance_cents))
            balance_sign = "+" if member_balance_cents >= 0 else "-"
            balance_display = f"{balance_sign}${member_balance_formatted}"

            # Check if balance needs to be settled
            if member_balance_cents > 0:
                # Member is owed money (positive balance)
                print(_("\n⚠️  Warning: '{}' is owed {}.").format(member["name"], balance_display))
                print(_("   Other members should settle this balance before removal."))
                response = input(_("Remove member '{}' anyway? (y/n): ").format(member["name"]))
            elif member_balance_cents < 0:
                # Member owes money (negative balance)
                print(_("\n⚠️  Warning: '{}' owes {}.").format(member["name"], balance_display))
                print(_("   This balance should be settled before removal."))
                response = input(_("Remove member '{}' anyway? (y/n): ").format(member["name"]))
            else:
                # Zero balance - safe to remove
                response = input(_("Remove member '{}' (Balance: $0.00)? (y/n): ").format(member["name"]))

            if response.lower() not in ("y", "yes"):
                print(_("Member removal cancelled."))
                continue

            result = logic.remove_member(member["name"])
            print(result)

        elif choice == "8":
            print(_("Exiting Divvy. Goodbye!"))
            break

        else:
            print(_("Invalid choice, please try again."))


if __name__ == "__main__":
    main()
