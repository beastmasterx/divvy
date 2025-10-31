from . import logic
from . import database

def show_menu():
    """Prints the main menu."""
    print("\n--- Divvy Expense Splitter ---")
    print("1. Add a new member")
    print("2. Record an expense")
    print("3. Show settlement balances")
    print("4. Exit")
    print("-----------------------------")

def main():
    """The main function and entry point for the CLI application."""
    # Ensure the database is initialized before starting
    database.initialize_database()

    while True:
        show_menu()
        choice = input("Enter your choice: ")

        if choice == '1':
            name = input("Enter the new member's name: ")
            logic.add_new_member(name)
            print(f"Member '{name}' added.")

        elif choice == '2':
            description = input("Enter expense description: ")
            amount_str = input("Enter total amount: ")
            payer_name = input("Enter payer's name: ")
            category_name = input("Enter category: ")
            remark = input("Enter any remarks (optional): ")
            logic.record_expense(description, amount_str, payer_name, category_name, remark if remark else None)
            print("Expense recorded.")

        elif choice == '3':
            balances = logic.get_settlement_balances()
            if not balances:
                print("No balances to show yet.")
            else:
                print("\n--- Current Balances ---")
                for name, status in balances.items():
                    print(f"{name}: {status}")
                print("------------------------")

        elif choice == '4':
            print("Exiting Divvy. Goodbye!")
            break

        else:
            print("Invalid choice, please try again.")

if __name__ == '__main__':
    main()
