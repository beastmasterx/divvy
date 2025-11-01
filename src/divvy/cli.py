from . import database, logic
from .i18n import _, set_language, translate_category, translate_transaction_type


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


def _display_view_period() -> None:
    """Displays the combined period view with transactions and active member balances."""
    summary = logic.get_period_summary()

    if not summary or not summary.get("period"):
        print(_("No active period found."))
        return

    period = summary["period"]
    transactions = summary["transactions"]
    totals = summary["totals"]

    # Get active members with balances
    active_members = database.get_active_members()
    active_balances = logic.get_active_member_balances(period["id"])

    # Calculate net
    net_cents = totals["deposits"] - totals["expenses"]
    net_formatted = logic._cents_to_dollars(net_cents)
    net_sign = "+" if net_cents >= 0 else "-"

    # Format deposits and expenses with signs
    deposits_formatted = f"+{totals['deposits_formatted']}"
    expenses_formatted = f"-{totals['expenses_formatted']}"

    print("\n" + "=" * 60)
    print(_("                 VIEW PERIOD: {}").format(period["name"]))
    print("=" * 60)
    active_status = _("Active") if not period["is_settled"] else _("Settled")
    # Extract date only from start_date (remove time portion)
    start_date_only = period["start_date"].split()[0] if " " in period["start_date"] else period["start_date"]
    print(
        _("Period: {} | Started: {} | {}").format(
            period["name"], start_date_only, active_status
        )
    )
    print(
        _("Deposits: {} | Expenses: {} | Net: {}{}").format(
            deposits_formatted, expenses_formatted, net_sign, net_formatted
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
            timestamp_str = tx.get("TIMESTAMP", tx.get("timestamp", ""))
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
            if tx["payer_id"]:
                payer = database.get_member_by_id(tx["payer_id"])
                if payer:
                    payer_name = database.get_member_display_name(payer)
                else:
                    payer_name = _("Member ID {}").format(tx["payer_id"])

            transactions_data.append(
                {
                    "date": date_only,
                    "category": category_name,
                    "type": tx_type,
                    "amount": amount_cents,
                    "amount_formatted": f"{amount_sign}{amount_formatted}",
                    "description": desc,
                    "payer": payer_name,
                }
            )

        # Sort by date, category, type, payer
        transactions_data.sort(key=lambda x: (x["date"], x["category"], x["type"], x["payer"]))

        # Calculate column widths
        max_category_len = (
            max(len(t["category"]) for t in transactions_data) if transactions_data else 10
        )
        max_desc_len = (
            max(len(t["description"]) for t in transactions_data) if transactions_data else 10
        )
        max_payer_len = max(len(t["payer"]) for t in transactions_data) if transactions_data else 8

        category_width = max(15, max_category_len)
        desc_width = max(20, max_desc_len)
        payer_width = max(12, max_payer_len)

        # Print header
        header_date = _("Date")
        header_category = _("Category")
        header_type = _("Type")
        header_amount = _("Amount")
        header_description = _("Description")
        header_payer = _("Payer")
        print(
            f"  {header_date:<12} | {header_category:<{category_width}} | {header_type:<8} | {header_amount:>12} | {header_description:<{desc_width}} | {header_payer:<{payer_width}}"
        )
        print(
            f"  {'-' * 12} | {'-' * category_width} | {'-' * 8} | {'-' * 12} | {'-' * desc_width} | {'-' * payer_width}"
        )

        # Print transactions
        for tx in transactions_data:
            desc_display = tx["description"] if tx["description"] else ""
            print(
                f"  {tx['date']:<12} | {tx['category']:<{category_width}} | {tx['type']:<8} | {tx['amount_formatted']:>12} | {desc_display:<{desc_width}} | {tx['payer']:<{payer_width}}"
            )
    else:
        print(_("\n--- Transactions (0) ---"))
        print(_("  No transactions in this period."))

    # Active members with balances
    if active_members:
        print(_("\n--- Members ({} active) ---").format(len(active_members)))
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
        print(_("\n--- Members (0 active) ---"))
        print(_("  No active members."))

    print("\n" + "=" * 60 + "\n")


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
        virtual_member = database.get_member_by_name(database.VIRTUAL_MEMBER_INTERNAL_NAME)
        if virtual_member:
            # Create a display version with translated name
            members_with_group = members + [
                {**virtual_member, "name": database.get_member_display_name(virtual_member)}
            ]
            payer = select_from_list(members_with_group, "name", _("Payer"))
            if payer:
                # Return internal name if virtual member selected
                if payer.get("id") == virtual_member["id"]:
                    return database.VIRTUAL_MEMBER_INTERNAL_NAME
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
                payer_name = database.VIRTUAL_MEMBER_INTERNAL_NAME
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
            _display_view_period()

        elif choice == "5":
            # Show period status first
            _display_view_period()

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
