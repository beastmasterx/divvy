#!/bin/bash

# Development environment script
# Sets DIVVY_ENV=dev and runs the CLI application

# Get the absolute path of the project root (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Determine which Python to use
PYTHON_CMD="python3"
ENV_NAME=""

# Try to detect environment name from environment.yml
ENV_YML="$PROJECT_ROOT/environment.yml"
if [ -f "$ENV_YML" ]; then
    # Extract the 'name:' value from environment.yml
    ENV_NAME=$(grep -E "^name:" "$ENV_YML" 2>/dev/null | sed -E 's/^name:[[:space:]]*([^[:space:]#]+).*/\1/' | head -1)
fi

# Try to use conda environment if available
if command -v conda &>/dev/null && [ -n "$ENV_NAME" ]; then
    # Try to find conda base path
    CONDA_BASE=$(conda info --base 2>/dev/null)
    if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/envs/$ENV_NAME/bin/python" ]; then
        # Use Python from conda environment directly
        PYTHON_CMD="$CONDA_BASE/envs/$ENV_NAME/bin/python"
    fi
fi

# Set development environment and logging
export DIVVY_ENV=dev
export DIVVY_LOG_LEVEL=INFO
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" "$PYTHON_CMD" -m cli.main "$@"

