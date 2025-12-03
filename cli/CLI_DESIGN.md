# CLI Design - Kubectl-Style Command Structure

## Command Format

```
divvy [verb] [resource] [flags] [arguments]
```

## Commands

### General Commands

```
divvy get RESOURCE [ID] [flags]
divvy create RESOURCE [-f FILE | NAME] [flags]
divvy edit RESOURCE ID [flags]
divvy delete RESOURCE ID [flags]
divvy delete -f FILE [flags]
divvy apply -f FILE [--dry-run]
```

**Resources:**

- `group` or `groups` (plural supported like kubectl)
- `period` or `periods`
- `transaction` or `transactions`

**Note:**

- `-f FILE` or `--file=FILE`: YAML file (use `-f -` for stdin)
- `create`: Create resources from YAML file (`-f FILE`) or directly via arguments (simple resources only)
  - Simple resources (group, period): Support direct creation via `divvy create group NAME [--description=DESC]`
  - Complex resources (transaction): Require YAML file (`-f FILE`)
- `edit`: Opens YAML editor (uses $EDITOR, defaults to vi/nano) for editing the resource
- `apply`: Create or update resources from YAML (idempotent)
- `delete`: Delete resources by ID (`divvy delete RESOURCE ID`) or from YAML file (`divvy delete -f FILE`). When using `-f FILE`, resource type is inferred from YAML.
- `--dry-run`: Show what would be done without making changes
- Supports multiple resources in one YAML file (like kubectl)

### Authentication

```
divvy auth login [--user=USER | -u USER] [--password=PASSWORD | -p[PASSWORD]]
divvy auth register [--user=USER | -u USER] [--name=NAME] [--password=PASSWORD | -p[PASSWORD]]
divvy auth logout
divvy auth status
```

**Note:** When `-p` is provided without a value, password will be prompted interactively (similar to MySQL client). For security, prefer interactive prompting when possible.

### Period Operations (Period-specific verbs)

```
divvy period close [PERIOD_ID] [--group=GROUP_ID]
divvy period balance [--period=PERIOD_ID] [--group=GROUP_ID] [-o FORMAT | --output=FORMAT]
divvy period plan [--period=PERIOD_ID] [--group=GROUP_ID] [-o FORMAT | --output=FORMAT]
divvy period apply [--period=PERIOD_ID] [--group=GROUP_ID] [--yes]
```

### Transaction Operations (Transaction-specific verbs)

```
divvy transaction approve TRANSACTION_ID
divvy transaction reject TRANSACTION_ID
divvy transaction submit TRANSACTION_ID
```

### Config

```
divvy config view
divvy config set-context [--group=GROUP_ID|GROUP_NAME] [--period=PERIOD_ID|PERIOD_NAME]
divvy config unset-context [--group] [--period]
divvy config current-context
divvy config get|set PREFERENCE_KEY [VALUE]
```

**Note:** Context management is part of `config` command, following kubectl's pattern. Use `config set apiUrl URL` or `config set language LANG` for specific settings.

### Completion

```
divvy completion bash
divvy completion zsh
```

**Note:** Generates shell completion scripts. Install with:

- Bash: `divvy completion bash > /etc/bash_completion.d/divvy` or `~/.bash_completion.d/divvy`
- Zsh: `divvy completion zsh > ~/.zsh/completions/_divvy`

### Version

```
divvy version [--short]
```

**Note:** Shows CLI version information. Use `--short` for version number only.

### Help

```
divvy help
divvy [command] --help
divvy [command] [subcommand] --help
```

## Flags

- `--group=ID` or `-g ID`: Specify group
- `--period=ID` or `-P ID`: Specify period
- `--user=USER` or `-u USER`: User/email address (auth commands only)
- `--password=PASSWORD` or `-p[PASSWORD]`: Password (auth commands only; `-p` without value forces interactive prompt)
- `--output=FORMAT` or `-o FORMAT`: Output format (table (default), json, yaml, wide)
  - `table`: Human-readable table format (default)
  - `json`: JSON format
  - `yaml`: YAML format (like kubectl)
  - `wide`: Table format with additional columns
- `--yes` or `-y`: Auto-confirm prompts
- `--quiet` or `-q`: Minimal output
- `--verbose` or `-v`: Detailed output
- `-f FILE` or `--file=FILE`: YAML file (general commands)
- `--dry-run`: Show what would be done without making changes

## Short Aliases

**Note:** Short aliases are not currently defined. With verb-first structure, aliases would need to be context-aware (e.g., `divvy g` could mean `divvy get` or a resource name). Consider implementing resource name completion instead.

## Examples

```bash
# Authentication
divvy auth login
divvy auth login -u user@example.com
divvy auth login -u user@example.com -p
divvy auth login -u user@example.com --password=mypassword
divvy auth login -u user@example.com -pmypassword
divvy auth register
divvy auth register -u user@example.com --name="John Doe"
divvy auth register -u user@example.com --name="John Doe" -p
divvy auth status

# Get resources (verb-first, like kubectl)
divvy get group
divvy get group "Apartment Roommates"
divvy get period
divvy get period "January 2024"
divvy get transaction
divvy get transaction 123

# Create resources
divvy create group "Apartment Roommates"  # Direct creation
divvy create group "Apartment Roommates" --description="Roommate expenses"
divvy create group -f group.yaml  # From YAML
divvy create period "January 2024"  # Direct creation
divvy create period "January 2024" --group=1  # With flags
divvy create period -f period.yaml  # From YAML
divvy create transaction -f transaction.yaml  # Transaction requires YAML

# Edit resources (opens YAML editor)
divvy edit group "Apartment Roommates"
divvy edit period "January 2024"
divvy edit transaction 123

# Delete resources
divvy delete group "Apartment Roommates"
divvy delete period "January 2024"
divvy delete transaction 123
divvy delete -f resources.yaml  # Delete from YAML file

# Apply from YAML (idempotent)
divvy apply -f group.yaml
divvy apply -f period.yaml
divvy apply -f resources.yaml  # Multiple resources in one file
divvy get group "Apartment Roommates" -o yaml | divvy apply -f -
divvy apply -f group.yaml --dry-run

# Output formats (like kubectl)
divvy get group "Apartment Roommates" -o yaml
divvy get group "Apartment Roommates" -o json
divvy get period "January 2024" -o yaml
divvy get transaction 123 -o yaml
divvy period balance -o yaml
divvy period plan -o yaml

# Save to file
divvy get group "Apartment Roommates" -o yaml > group.yaml
divvy get period "January 2024" -o yaml > period.yaml

# Period settlement operations
divvy period balance
divvy period plan
divvy period apply --yes

# Transaction operations (using general commands)
divvy get transaction 123
divvy create transaction -f transaction.yaml
divvy edit transaction 123
divvy apply -f transaction.yaml
divvy delete transaction 123

# Transaction-specific operations
divvy transaction approve 123
divvy transaction reject 123
divvy transaction submit 123

# Config and context (consolidated, like kubectl)
divvy config view
divvy config set-context --group="Apartment Roommates" --period="January 2024"
divvy config unset-context --group
divvy config current-context
divvy config set apiUrl http://localhost:8000
divvy config set language en_US
divvy config get apiUrl

# Using flags to override context
divvy get transaction -g "Other Group" -P "February 2024"
divvy period balance -o json

# Completion and version
divvy completion bash
divvy version
divvy version --short
```
