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
- [Code Quality & Linting](#code-quality--linting)
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
- **Expense Types**: Support for three expense types:
  - **Shared Expenses**: Paid from the group's public fund first, then split remainder among members
  - **Personal Expenses**: Only affect the payer's balance (not split among members)
  - **Individual Expenses**: Split evenly among all active members (default)
- **Category System**: Pre-configured categories (Rent, Groceries, Utilities, etc.)
- **Public Fund (Group Fund)**: Deposit funds to a shared pool that can be used for shared expenses
- **Deposit Management**: Track member contributions to individual accounts or the public fund
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

- **Period Summaries**: View detailed summaries for any period (current or past)
- **Settlement Calculations**: Calculate who owes what and who is owed
- **Settlement Plans**: View recommended settlement transactions before closing a period
- **Transaction History**: Full transaction history with dates, categories, and split types
- **Public Fund Tracking**: Monitor the group's public fund balance in period summaries

## Requirements

- **Python**: 3.10 or higher
- **Environment Manager**: conda

## Installation

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

## Usage

After activating your environment, start the application:

```bash
./divvy
```

### Language Selection

Divvy supports multiple languages (English and Chinese). The language is automatically detected from your environment, or you can set it explicitly:

**Using Environment Variable:**

```bash
# Set to Chinese (Simplified)
export DIVVY_LANG=zh_CN
# or
export LANG=zh_CN.UTF-8

# Set to English
export DIVVY_LANG=en_US
# or
export LANG=en_US.UTF-8

# Then run the application
./divvy
```

**Supported Language Codes:**
- `en`, `en_US` - English (United States) - Default
- `zh`, `zh_CN`, `zh_CN.UTF-8` - Chinese (Simplified)

The application checks language settings in this order:
1. `DIVVY_LANG` environment variable (application-specific)
2. `LANG` environment variable (system default)
3. System locale settings
4. Falls back to English (`en_US`) if no match is found

**Compiling Translations:**

If you modify translation files (`.po` files), compile them to binary format (`.mo`) using:

```bash
python compile_translations.py
```

Or manually using `msgfmt`:

```bash
msgfmt -o src/divvy/locale/en_US/LC_MESSAGES/divvy.mo \
       src/divvy/locale/en_US/LC_MESSAGES/divvy.po

msgfmt -o src/divvy/locale/zh_CN/LC_MESSAGES/divvy.mo \
       src/divvy/locale/zh_CN/LC_MESSAGES/divvy.po
```

The interactive menu will guide you through all operations:

```
--- DIVVY ---
Current Period: Initial Period
1. Add Expense
2. Add Deposit
3. Add Refund
4. View Period
5. Close period
6. Add member
7. Remove Member
8. Exit
-----------------------------
```

**Menu Options Explained:**

- **1. Add Expense**: Record a new expense (shared, personal, or individual split)
- **2. Add Deposit**: Record a deposit to a member or the public fund (Group)
- **3. Add Refund**: Process a refund to any member (including inactive members)
- **4. View Period**: View detailed summary of any period (current or past)
- **5. Close period**: Settle the current period and start a new one
- **6. Add member**: Add a new member or rejoin an inactive member
- **7. Remove Member**: Deactivate a member (with balance warnings)
- **8. Exit**: Exit the application

### Common Workflows

#### Setting Up Your Group

1. **Add Members**: Select option `6` and enter member names
2. **Initial Deposits**: Use option `2` to record initial contributions:
   - You can deposit to individual members (select member from list)
   - You can deposit to the public fund (select "Group" from list) for shared expenses

#### Recording Expenses

1. Select `1. Add Expense`
2. Enter expense description (optional)
3. Enter amount (e.g., `30.50`)
4. Choose expense type:
   - `s` or `shared`: Uses the group's public fund first, then splits remainder
   - `p` or `personal`: Only affects the payer's balance (not split)
   - `i` or `individual` (default): Splits evenly among all active members
5. Select payer from the list:
   - For shared expenses, payer is automatically set to "Group"
   - For personal/individual expenses, select a member
6. Choose a category (Groceries, Rent, etc.)

The system automatically:

- For individual expenses: Splits evenly among active members and assigns remainder using round-robin logic
- For shared expenses: Uses public fund first, then splits any remainder among members
- For personal expenses: Only updates the payer's balance
- Updates member balances accordingly

#### Viewing Period Summary

Select `4. View Period` to see a list of all periods (current and past):

- Select any period to view its details, or press Enter for the current period
- View includes:
  - All transactions in the period (deposits, expenses, refunds)
  - Transaction details: date, category, type, split type, amount, description, payer/from/to
  - Public fund balance for the period
  - Totals for deposits and expenses
  - All active member balances with remainder status indicators

#### Closing a Period

1. Select `5. Close period`
2. Review the period summary that's automatically displayed
3. Review the settlement plan (recommended transactions to balance all accounts)
4. Confirm closure (`y` to proceed)
5. Enter name for the new period (or press Enter for auto-generated name)

This will:

- Settle the current period (marks it as settled with a settlement date)
- Create a new active period
- Reset remainder flags for fair distribution in the new period
- Distribute any remaining public fund balance to creditors if applicable

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
│       ├── i18n.py          # Internationalization support
│       ├── schema.sql        # Database schema
│       └── locale/          # Translation files
│           ├── en_US/
│           │   └── LC_MESSAGES/
│           │       ├── divvy.po  # English translations (source)
│           │       └── divvy.mo  # English translations (compiled)
│           └── zh_CN/
│               └── LC_MESSAGES/
│                   ├── divvy.po  # Chinese translations (source)
│                   └── divvy.mo  # Chinese translations (compiled)
├── tests/
│   ├── test_cli.py          # CLI tests
│   ├── test_database.py     # Database tests
│   └── test_logic.py        # Logic tests
├── environment.yml          # Conda environment configuration
├── compile_translations.py  # Script to compile translation files
├── LICENSE                  # Apache License 2.0
├── divvy                    # Convenience launcher script
└── README.md                # This file
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

## Code Quality & Linting

This project uses [Ruff](https://github.com/astral-sh/ruff) for code linting and formatting to ensure consistent code quality and style.

### Running Ruff

After installing dependencies (Ruff is included in `environment.yml`), you can use the following commands:

**Check for linting issues:**

```bash
ruff check .
```

**Automatically fix fixable issues:**

```bash
ruff check --fix .
```

**Format code:**

```bash
ruff format .
```

**Check and format together:**

```bash
ruff check --fix . && ruff format .
```

### Configuration

Ruff configuration is defined in `pyproject.toml`. The current configuration:

- Enables comprehensive linting rules (pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, bugbear, and more)
- Sets line length to 100 characters
- Targets Python 3.10+
- Uses double quotes for string formatting
- Allows autofix for most rules

### Pre-Commit Integration (Optional)

To automatically run Ruff before commits, you can install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

Create a `.pre-commit-config.yaml` file with Ruff configuration if you want automated checks.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/JIRA-123-amazing-feature`) - include JIRA ticket number if applicable
3. Make your changes
4. Add tests for new functionality
5. Run linting: `ruff check --fix . && ruff format .`
6. Ensure all tests pass (`pytest tests/ -v`)
7. Commit your changes with a JIRA ticket number in the commit message:
   ```bash
   git commit -m 'feat: JIRA-123 Add amazing feature'
   ```
   Format: `<type>: JIRA-<ticket-number> <description>`
8. Push to the branch (`git push origin feature/JIRA-123-amazing-feature`)
9. Open a Pull Request (include JIRA ticket number in PR title if applicable)

### Development Setup

1. Clone the repository
2. Create a conda environment: `conda env create -f environment.yml`
3. Activate the environment: `conda activate divvy`
4. Run linting: `ruff check --fix . && ruff format .`
5. Run tests to verify setup: `pytest tests/ -v`

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

For more information about the Apache License, visit http://www.apache.org/licenses/LICENSE-2.0

---

**Note**: The database file (`data/expenses.db`) is created automatically on first run. Make sure the `data/` directory exists or the application will create it.
