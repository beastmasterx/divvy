from . import logic
from . import database


def select_from_list(items: list[dict], name_key: str, prompt: str) -> dict | None:
    """Displays a numbered list and returns the selected item."""
    if not items:
        print(f"No {prompt.lower()} available.")
        return None
    
    print(f"\n--- Select {prompt} ---")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item[name_key]}")
    print("------------------------")
    
    while True:
        try:
            choice = input(f"Enter your choice (1-{len(items)}): ")
            index = int(choice) - 1
            if 0 <= index < len(items):
                return items[index]
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(items)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            return None


def _display_view_period() -> None:
    """Displays the combined period view with transactions and active member balances."""
    summary = logic.get_period_summary()
    
    if not summary or not summary.get('period'):
        print("No active period found.")
        return
    
    period = summary['period']
    transactions = summary['transactions']
    totals = summary['totals']
    
    # Get active members with balances
    active_members = database.get_active_members()
    active_balances = logic.get_active_member_balances(period['id'])
    
    # Calculate net
    net_cents = totals['deposits'] - totals['expenses']
    net_formatted = logic._cents_to_dollars(net_cents)
    net_sign = '+' if net_cents >= 0 else '-'
    
    # Format deposits and expenses with signs
    deposits_formatted = f"+{totals['deposits_formatted']}"
    expenses_formatted = f"-{totals['expenses_formatted']}"
    
    print("\n" + "=" * 60)
    print(f"                 VIEW PERIOD: {period['name']}")
    print("=" * 60)
    print(f"Period: {period['name']} | Started: {period['start_date']} | {'Active' if not period['is_settled'] else 'Settled'}")
    print(f"Deposits: {deposits_formatted} | Expenses: {expenses_formatted} | Net: {net_sign}{net_formatted}")
    
    # Transactions with headers
    if transactions:
        print(f"\n--- Transactions ({len(transactions)}) ---")
        
        # Prepare transactions with all needed data
        transactions_data = []
        for tx in transactions:
            # Category: only show for expenses, blank for deposits/refunds
            category_name = ""
            if tx['transaction_type'] == 'expense' and tx['category_id']:
                category = database.get_category_by_id(tx['category_id'])
                category_name = category['name'] if category else f"Category ID {tx['category_id']}"
            # For deposits/refunds, leave category blank (not "Uncategorized")
            
            # SQLite column names: check for TIMESTAMP (as defined in schema) or lowercase variant
            timestamp_str = tx.get('TIMESTAMP', tx.get('timestamp', ''))
            date_only = timestamp_str.split()[0] if ' ' in timestamp_str else timestamp_str
            
            tx_type = tx['transaction_type'].title()
            amount_cents = tx['amount']
            
            # Handle amount sign: negative amounts (refunds) show as negative
            # Positive deposits show as positive, expenses show as negative
            if amount_cents < 0:
                # Refund (negative deposit)
                amount_formatted = logic._cents_to_dollars(abs(amount_cents))
                amount_sign = '-'
                tx_type = "Refund"  # Show as Refund type for clarity
            elif tx['transaction_type'] == 'deposit':
                amount_formatted = logic._cents_to_dollars(amount_cents)
                amount_sign = '+'
            else:  # expense
                amount_formatted = logic._cents_to_dollars(amount_cents)
                amount_sign = '-'
            
            desc = tx['description'] if tx['description'] else ""
            
            payer_name = "Unknown"
            if tx['payer_id']:
                payer = database.get_member_by_id(tx['payer_id'])
                payer_name = payer['name'] if payer else f"Member ID {tx['payer_id']}"
            
            transactions_data.append({
                'date': date_only,
                'category': category_name,
                'type': tx_type,
                'amount': amount_cents,
                'amount_formatted': f"{amount_sign}{amount_formatted}",
                'description': desc,
                'payer': payer_name
            })
        
        # Sort by date, category, type, payer
        transactions_data.sort(key=lambda x: (x['date'], x['category'], x['type'], x['payer']))
        
        # Calculate column widths
        max_category_len = max(len(t['category']) for t in transactions_data) if transactions_data else 10
        max_desc_len = max(len(t['description']) for t in transactions_data) if transactions_data else 10
        max_payer_len = max(len(t['payer']) for t in transactions_data) if transactions_data else 8
        
        category_width = max(15, max_category_len)
        desc_width = max(20, max_desc_len)
        payer_width = max(12, max_payer_len)
        
        # Print header
        print(f"  {'Date':<12} | {'Category':<{category_width}} | {'Type':<8} | {'Amount':>12} | {'Description':<{desc_width}} | {'Payer':<{payer_width}}")
        print(f"  {'-'*12} | {'-'*category_width} | {'-'*8} | {'-'*12} | {'-'*desc_width} | {'-'*payer_width}")
        
        # Print transactions
        for tx in transactions_data:
            desc_display = tx['description'] if tx['description'] else ""
            print(f"  {tx['date']:<12} | {tx['category']:<{category_width}} | {tx['type']:<8} | {tx['amount_formatted']:>12} | {desc_display:<{desc_width}} | {tx['payer']:<{payer_width}}")
    else:
        print("\n--- Transactions (0) ---")
        print("  No transactions in this period.")
    
    # Active members with balances
    if active_members:
        print(f"\n--- Members ({len(active_members)} active) ---")
        member_strings = []
        for member in active_members:
            balance_cents = active_balances.get(member['name'], 0)
            balance_formatted = logic._cents_to_dollars(abs(balance_cents))
            balance_sign = '+' if balance_cents >= 0 else '-'
            remainder_str = "✓" if member['paid_remainder_in_cycle'] else "✗"
            member_strings.append(f"{member['name']} {remainder_str} {balance_sign}${balance_formatted}")
        print("  " + " | ".join(member_strings))
    else:
        print("\n--- Members (0 active) ---")
        print("  No active members.")
    
    print("\n" + "=" * 60 + "\n")


def select_payer(for_expense: bool = False) -> str | None:
    """Selects a payer from active members."""
    members = database.get_active_members()
    
    if not members:
        print("No active members available.")
        return None
    
    payer = select_from_list(members, 'name', "Payer")
    return payer['name'] if payer else None


def show_menu():
    """Prints the main menu."""
    try:
        current_period = database.get_current_period()
        period_name = current_period['name'] if current_period else "None"
    except Exception:
        # If database not ready yet, show default
        period_name = "Initializing..."
    
    print("\n--- Divvy Expense Splitter ---")
    print(f"Current Period: {period_name}")
    print("1. Add Expense")
    print("2. Add Deposit")
    print("3. Add Refund")
    print("4. View Period")
    print("5. Close period")
    print("6. Add member")
    print("7. Remove Member")
    print("8. Exit")
    print("-----------------------------")


def main():
    """The main function and entry point for the CLI application."""
    # Ensure the database is initialized before starting
    database.initialize_database()

    while True:
        show_menu()
        choice = input("Enter your choice: ")

        if choice == '1':
            description = input("Enter expense description (optional): ")
            amount_str = input("Enter total amount: ").strip()
            
            if not amount_str:
                print("Error: Amount cannot be empty.")
                continue
            
            payer_name = select_payer(for_expense=True)
            if payer_name is None:
                print("Expense recording cancelled.")
                continue
            
            categories = database.get_all_categories()
            category = select_from_list(categories, 'name', "Category")
            if category is None:
                print("Expense recording cancelled.")
                continue
            category_name = category['name']
            
            desc = description if description else None
            result = logic.record_expense(desc, amount_str, payer_name, category_name)
            print(result)

        elif choice == '2':
            description = input("Enter deposit description (optional): ")
            amount_str = input("Enter deposit amount: ").strip()
            
            if not amount_str:
                print("Error: Amount cannot be empty.")
                continue
            
            payer_name = select_payer(for_expense=False)
            if payer_name is None:
                print("Deposit recording cancelled.")
                continue
            
            desc = description if description else None
            result = logic.record_deposit(desc, amount_str, payer_name)
            print(result)

        elif choice == '3':
            # Add Refund
            all_members_list = database.get_all_members()
            if not all_members_list:
                print("No members available.")
                continue
            
            member = select_from_list(all_members_list, 'name', "Member to refund")
            if member is None:
                print("Refund cancelled.")
                continue
            
            description = input("Enter refund description (optional): ")
            amount_str = input("Enter refund amount: ").strip()
            
            if not amount_str:
                print("Error: Amount cannot be empty.")
                continue
            
            desc = description if description else None
            result = logic.record_refund(desc, amount_str, member['name'])
            print(result)

        elif choice == '4':
            _display_view_period()

        elif choice == '5':
            # Show period status first
            _display_view_period()
            
            # Ask for confirmation
            response = input("Close this period? (y/n): ")
            if response.lower() not in ('y', 'yes'):
                print("Period closing cancelled.")
                continue
            
            # Get new period name
            period_name = input(
                "Enter name for new period (press Enter for auto-generated): "
            ).strip()
            if not period_name:
                period_name = None
            
            result = logic.settle_current_period(period_name)
            print(result)

        elif choice == '6':
            name = input("Enter the member's name: ")
            name = name.strip()
            
            if not name:
                print("Member name cannot be empty.")
                continue
            
            # Check if member exists
            existing_member = database.get_member_by_name(name)
            
            if existing_member:
                if existing_member['is_active']:
                    print(f"Error: Member '{name}' already exists and is active.")
                else:
                    # Member is inactive - ask to rejoin
                    response = input(f"Member '{name}' is inactive. Rejoin? (y/n): ")
                    if response.lower() in ('y', 'yes'):
                        result = logic.rejoin_member(name)
                        print(result)
                    else:
                        print("Rejoin cancelled.")
            else:
                # New member - add normally
                result = logic.add_new_member(name)
                print(result)

        elif choice == '7':
            members = database.get_active_members()
            if not members:
                print("No active members to remove.")
                continue
            
            # Show current period status first
            _display_view_period()
            
            member = select_from_list(members, 'name', "Member to remove")
            if member is None:
                print("Member removal cancelled.")
                continue
            
            # Get member's current balance
            active_balances = logic.get_active_member_balances()
            member_balance_cents = active_balances.get(member['name'], 0)
            member_balance_formatted = logic._cents_to_dollars(abs(member_balance_cents))
            balance_sign = '+' if member_balance_cents >= 0 else '-'
            balance_display = f"{balance_sign}${member_balance_formatted}"
            
            # Check if balance needs to be settled
            if member_balance_cents > 0:
                # Member is owed money (positive balance)
                print(f"\n⚠️  Warning: '{member['name']}' is owed {balance_display}.")
                print("   Other members should settle this balance before removal.")
                response = input(f"Remove member '{member['name']}' anyway? (y/n): ")
            elif member_balance_cents < 0:
                # Member owes money (negative balance)
                print(f"\n⚠️  Warning: '{member['name']}' owes {balance_display}.")
                print("   This balance should be settled before removal.")
                response = input(f"Remove member '{member['name']}' anyway? (y/n): ")
            else:
                # Zero balance - safe to remove
                response = input(f"Remove member '{member['name']}' (Balance: $0.00)? (y/n): ")
            
            if response.lower() not in ('y', 'yes'):
                print("Member removal cancelled.")
                continue
            
            result = logic.remove_member(member['name'])
            print(result)

        elif choice == '8':
            print("Exiting Divvy. Goodbye!")
            break

        else:
            print("Invalid choice, please try again.")


if __name__ == '__main__':
    main()
