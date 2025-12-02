# Divvy CLI

A command-line interface for the Divvy expense splitting application, built with Dart.

## Overview

The Divvy CLI provides an interactive menu-driven interface for managing group expenses, transactions, and settlements. It communicates with the Divvy REST API and features a context-aware menu system that adapts to your current session state.

**Key Features:**

- Interactive context-aware menu system
- Authentication (login, register, logout)
- Group and period management
- Transaction tracking (expenses, deposits, refunds)
- Settlement calculations and application
- Internationalization (English, Chinese)
- Secure password input with asterisk masking

## Installation

**Requirements:**

- Dart SDK 3.9.2 or higher
- Divvy API server running (default: `http://localhost:8000`)
- For API client generation: Java JDK 11+ and Python 3+ with `openapi-generator-cli` (`pip install openapi-generator-cli`)

**Setup:**

```bash
cd cli
dart pub get
./scripts/generate-dart-api-client.sh  # Generate API client from api/openapi.json
```

## Usage

**Run the CLI:**

```bash
dart run bin/divvy.dart
```

The CLI starts with an interactive menu that adapts based on your authentication status and selected group/period.

**Menu Structure:**

- **Not authenticated**: Login, Register, Exit
- **Authenticated, no group**: Select/Create Group, Settings, More, Exit
- **Authenticated, group selected**: View/Create Period, Select Group, Settings, More, Exit
- **Full context (group + period)**: View/Add Transactions, View Balances, Settlement, Settings, Exit

Less common options are grouped under "More..." to keep the main menu clean.

## Configuration

Configuration is stored in a preferences file:

- **Windows**: `%APPDATA%\divvy\preferences.json`
- **Linux/macOS**: `~/.divvy/preferences.json`

**Settings:**

- `apiUrl`: API server URL (default: `http://localhost:8000`)
- `language`: UI language - `en_US` or `zh_CN` (default: `en_US`)
- `defaultGroupId`: Default group to use
- `lastActiveGroupId`: Last selected group
- `lastActivePeriodId`: Last selected period

Settings can be changed through the Settings menu in the CLI.

## Development

**Project Structure:**

```
cli/
├── bin/
│   └── divvy.dart              # Entry point
├── lib/src/
│   ├── api/                    # API client wrapper
│   ├── auth/                   # Authentication
│   ├── commands/               # Command handlers
│   ├── config/                 # Configuration management
│   ├── models/                 # Data models
│   ├── services/               # Business logic services
│   ├── ui/                     # UI components (menu, prompts, tables)
│   └── utils/                  # Utilities (i18n, errors, validation)
├── test/                       # Unit tests
└── generated/openapi/divvy/    # Generated API client
```
