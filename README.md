# Divvy - Expense Splitting CLI

A command-line utility designed to help groups track and split shared expenses fairly. Perfect for roommates, shared households, and collaborative expense management.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Overview

Divvy is a Python-based CLI application that simplifies expense tracking and splitting for groups. It provides a fair way to distribute shared expenses, handle deposits, manage refunds, and calculate settlements using a round-robin approach for remainder distribution.

**Key Capabilities:**

- Track shared expenses with categorization
- Manage group members (add/remove)
- Handle deposits and refunds
- Period-based expense tracking
- Automatic fair remainder distribution
- Settlement calculations and reporting

## Features

### 💰 Expense Management

- **Expense Tracking**: Record expenses with descriptions, amounts, and categories
- **Category System**: Pre-configured categories (Rent, Groceries, Utilities, etc.)
- **Deposit Management**: Track member contributions to shared funds
- **Refund Handling**: Process refunds to members

### 👥 Member Management

- **Add Members**: Easily add new members to the group
- **Remove Members**: Deactivate members with balance warnings
- **Active/Inactive Tracking**: Manage member status over time

### ⚖️ Fair Distribution

- **Round-Robin Remainder**: Automatically distributes remainder cents fairly among members
- **Period-Based Tracking**: Organize expenses into settlement periods
- **Balance Calculations**: Real-time balance tracking for all members

### 📊 Reporting & Settlement

- **Period Summaries**: View detailed period summaries with transactions
- **Settlement Calculations**: Calculate who owes what and who is owed
- **Transaction History**: Full transaction history with dates and categories

## Requirements

- **Python**: 3.10 or higher
- **Environment Manager**: conda (recommended) or venv/virtualenv

## Installation

### Using Conda (Recommended)

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd divvy
   ```

2. **Create and activate the conda environment**:

   ```bash
   conda env create -f environment.yml
   conda activate divvy
   ```

3. **Run the application**:

   ```bash
   python -m src.divvy.cli
   ```

   Or use the convenience script:

   ```bash
   ./divvy
   ```

### Using pip/virtualenv

1. **Create a virtual environment**:

   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python -m src.divvy.cli
   ```

## Usage

After activating your environment, start the application:

```bash
./divvy
```

The interactive menu will guide you through all operations:

```
--- Divvy Expense Splitter ---
Current Period: Initial Period
1. Add Expense
2. Add Deposit
3. Add Refund
4. View Period
5. Close period
6. Add member
7. Remove Member
8. Exit
```

### Common Workflows

#### Setting Up Your Group

1. **Add Members**: Select option `6` and enter member names
2. **Initial Deposits**: Use option `2` to record initial contributions

#### Recording Expenses

1. Select `1. Add Expense`
2. Enter expense description (optional)
3. Enter amount (e.g., `30.50`)
4. Select payer from the list
5. Choose a category (Groceries, Rent, etc.)

The system automatically:

- Splits the expense evenly among active members
- Assigns any remainder (cents) using round-robin logic
- Updates member balances

#### Viewing Period Summary

Select `4. View Period` to see:

- All transactions in the current period
- Member balances
- Totals for deposits and expenses
- Net balance

#### Closing a Period

1. Select `5. Close period`
2. Review the period summary
3. Confirm closure
4. Enter name for the new period (or auto-generate)

This will:

- Settle the current period
- Create a new active period
- Reset remainder flags for fair distribution

## Project Structure

```
divvy/
├── data/
│   └── expenses.db          # SQLite database (created on first run)
├── src/
│   └── divvy/
│       ├── __init__.py
│       ├── cli.py           # Command-line interface
│       ├── database.py       # Database operations
│       ├── logic.py          # Business logic
│       └── schema.sql        # Database schema
├── tests/
│   ├── test_cli.py          # CLI tests
│   ├── test_database.py     # Database tests
│   └── test_logic.py        # Logic tests
├── environment.yml          # Conda environment configuration
├── requirements.txt         # Pip dependencies
├── divvy                    # Convenience launcher script
└── README.md               # This file
```

## Testing

Run the complete test suite:

```bash
pytest tests/ -v
```

Run tests with coverage reporting:

```bash
pytest tests/ --cov=src/divvy --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Test Coverage

The project includes comprehensive tests covering:

- Database operations
- Business logic
- CLI interactions
- Edge cases and error handling

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/ -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

1. Clone the repository
2. Create a development environment using conda or venv
3. Install dependencies
4. Run tests to verify setup: `pytest tests/ -v`

## License

[Add your license here - MIT, Apache 2.0, etc.]

---

**Note**: The database file (`data/expenses.db`) is created automatically on first run. Make sure the `data/` directory exists or the application will create it.
