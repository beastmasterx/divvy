#!/bin/bash
# Start FastAPI development server
# Usage: ./scripts/start-api.sh [port]

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default port
PORT=${1:-8000}

# Activate virtual environment if needed
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "Using conda environment: $CONDA_DEFAULT_ENV"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "Activated virtual environment"
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Start uvicorn server
echo "Starting FastAPI server on port $PORT..."
echo "API documentation: http://localhost:$PORT/docs"
echo "ReDoc: http://localhost:$PORT/redoc"
echo ""

cd "$PROJECT_ROOT"
python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload

