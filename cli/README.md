# Divvy CLI (Dart)

A command-line interface for the Divvy expense splitting application, built with Dart. This CLI provides an interactive menu-driven interface for managing expenses, members, periods, and settlements.

## Overview

The Divvy CLI is a Dart-based command-line application that communicates with the Divvy REST API to manage group expenses. It provides the same functionality as the Python CLI (`cli-py/`) but uses the REST API instead of direct database access.

**Key Features:**

- Interactive menu-driven interface
- Expense tracking (shared, personal, individual)
- Member management
- Period-based expense tracking
- Settlement calculations
- Wide character support (CJK) for display formatting

## Requirements

- **Dart SDK**: 3.9.2 or higher
- **Divvy API Server**: Running and accessible (default: `http://localhost:8000`)

## Installation

1. **Ensure Dart SDK is installed**:

   ```bash
   dart --version
   ```

2. **Install dependencies**:

   ```bash
   cd cli
   dart pub get
   ```

3. **Generate API client** (if not already generated):
   ```bash
   dart run build_runner build --delete-conflicting-outputs
   ```

## Configuration

### API Base URL

The CLI connects to the Divvy API server. Configure the API URL using:

**Environment Variable:**

```bash
export DIVVY_API_URL=http://localhost:8000
dart run bin/cli.dart
```

**Default:** `http://localhost:8000`

## Usage

### Running the CLI

```bash
dart run bin/cli.dart
```

Or if you have a compiled executable:

```bash
dart cli/bin/cli.dart
```

### Interactive Menu

The CLI provides an interactive menu:

```
--- Divvy Expense Splitter ---
Current Period: [period name]
1. Add Expense
2. Add Deposit
3. Add Refund
4. View Period
5. Close period
6. Add member
7. Remove Member
8. Exit
-----------------------------
Enter your choice:
```

### Menu Options

#### 1. Add Expense

Record a new expense with the following options:

- **Shared**: Uses the group's public fund first, then splits remainder
- **Personal**: Only affects the payer's balance (not split)
- **Individual**: Splits evenly among all active members (default)

You'll be prompted for:

- Description (optional)
- Amount
- Expense type (s/p/i)
- Payer (if needed)
- Category

#### 2. Add Deposit

Record a deposit to:

- Individual member account
- Public fund (Group)

You'll be prompted for:

- Description (optional)
- Amount
- Payer (member or Group)

#### 3. Add Refund

Process a refund to any member (including inactive).

You'll be prompted for:

- Member to refund (from all members)
- Description (optional)
- Amount

#### 4. View Period

View detailed summary of any period (current or past).

Displays:

- Period information (dates, status)
- All transactions with formatted table
- Member balances
- Totals (deposits, expenses, public fund)

#### 5. Close Period

Settle the current period and create a new one.

Process:

1. Shows current period summary
2. Shows settlement plan (recommended transactions)
3. Asks for confirmation
4. Optionally prompts for new period name

#### 6. Add Member

Add a new member or rejoin an inactive member.

You'll be prompted for:

- Email address
- Name

If member exists but is inactive, you'll be asked to rejoin.

#### 7. Remove Member

Deactivate a member with balance warnings.

Process:

1. Shows current period status
2. Select member to remove
3. Shows balance warning if non-zero
4. Asks for confirmation

#### 8. Exit

Exit the application.

## Project Structure

```
cli/
├── bin/
│   └── cli.dart                    # Main entry point
├── lib/src/
│   ├── api/
│   │   └── divvy_client.dart       # API client wrapper
│   ├── services/
│   │   ├── members.dart           # Member operations
│   │   ├── periods.dart           # Period operations
│   │   ├── transactions.dart      # Transaction operations
│   │   ├── settlement.dart        # Settlement operations
│   │   └── categories.dart        # Category operations
│   ├── ui/
│   │   ├── menu.dart              # Menu system
│   │   ├── selectors.dart         # Interactive selectors
│   │   └── displays.dart          # Display functions
│   ├── utils/
│   │   ├── formatting.dart        # Text formatting & display width
│   │   ├── validation.dart       # Input validation
│   │   └── i18n.dart             # Internationalization
│   └── generated/                 # Generated API client (gitignored)
│       └── api/
│           └── divvy/
├── test/
│   └── unit/
│       └── utils/
│           ├── formatting_test.dart
│           └── validation_test.dart
├── api/
│   └── openapi.json               # OpenAPI specification
├── pubspec.yaml                   # Dart dependencies
└── README.md                      # This file
```

## Development

### Dependencies

Key dependencies:

- `dio`: HTTP client for API calls
- `intl`: Internationalization support
- `collection`: Collection utilities
- `args`: Command-line argument parsing

### Generating API Client

When the API specification changes, regenerate the API client:

```bash
dart run build_runner build --delete-conflicting-outputs
```

The generated client will be in `lib/src/generated/api/divvy/`.

#### Manual JAR Download (Slow Network)

If you experience network issues or timeouts during the build process, you can manually download the required JAR files before running the build:

```bash
# Create cache directory if it doesn't exist
mkdir -p .dart_tool/openapi_generator_cache

# Download the OpenAPI Generator CLI
curl -L -o .dart_tool/openapi_generator_cache/openapi-generator-cli-7.9.0.jar \
  https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/7.9.0/openapi-generator-cli-7.9.0.jar

# Download the custom Dart generator
curl -L -o .dart_tool/openapi_generator_cache/custom-openapi-dart-generator-7.2.jar \
  https://repo1.maven.org/maven2/com/bluetrainsoftware/maven/openapi-dart-generator/7.2/openapi-dart-generator-7.2.jar

# Verify downloads
java -jar .dart_tool/openapi_generator_cache/openapi-generator-cli-7.9.0.jar --version
```

After downloading the JAR files, the build process will skip the download step and use the cached files.

### Code Structure

- **Services**: Business logic layer that wraps API calls
- **UI**: Interactive components (menu, selectors, displays)
- **Utils**: Shared utilities (formatting, validation, i18n)
- **API Client**: Generated from OpenAPI spec (in `generated/`)

## Testing

Run all tests:

```bash
dart test
```

Run specific test file:

```bash
dart test test/unit/utils/formatting_test.dart
```

### Test Coverage

Current test coverage:

- ✅ Formatting utilities (display width, padding, amount formatting)
- ✅ Validation utilities (amount, email, name validation)

## Code Quality

### Linting

Run the analyzer:

```bash
dart analyze
```

### Formatting

Format code:

```bash
dart format .
```

## API Requirements

The CLI requires the Divvy API server to be running. Ensure the following endpoints are available:

- `GET /api/v1/members/` - List members
- `POST /api/v1/members/` - Create member
- `GET /api/v1/periods/` - List periods
- `GET /api/v1/periods/current` - Get current period
- `GET /api/v1/periods/{id}/summary` - Get period summary
- `GET /api/v1/categories/` - List categories
- `POST /api/v1/transactions/expenses` - Create expense
- `POST /api/v1/transactions/deposits` - Create deposit
- `POST /api/v1/transactions/refunds` - Create refund
- `GET /api/v1/settlement/plan` - Get settlement plan
- `POST /api/v1/periods/current/settle` - Settle period

See the main [README.md](../README.md) for API server setup.

## Migration from Python CLI

This Dart CLI replaces the Python CLI (`cli-py/`). Key differences:

- **Architecture**: Uses REST API instead of direct database access
- **Language**: Dart instead of Python
- **Dependencies**: Dart packages instead of Python packages
- **Functionality**: Same features, same user experience

## Troubleshooting

### API Connection Errors

If you see connection errors:

1. Verify the API server is running
2. Check `DIVVY_API_URL` environment variable
3. Verify network connectivity to the API server

### API Client Not Generated

If you see `UnimplementedError`:

1. Run: `dart run build_runner build --delete-conflicting-outputs`
2. Verify `api/openapi.json` exists and is up-to-date

If the build hangs or times out during JAR download, see [Manual JAR Download](#manual-jar-download-slow-network) in the Development section.

### Tests Failing

If tests fail:

1. Ensure all dependencies are installed: `dart pub get`
2. Check Dart SDK version: `dart --version` (should be 3.9.2+)

## License

See the main [LICENSE](../LICENSE) file.
