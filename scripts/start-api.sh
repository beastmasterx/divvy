#!/bin/bash
#
# Start FastAPI development server
# Usage: ./scripts/start-api.sh [port]
# Automatically detects and uses the appropriate Python interpreter:
# 1. Active Conda environment (if CONDA_PREFIX is set)
# 2. Environment from environment.yml (uses conda run)
# 3. System python3 (fallback)
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Determine Python command: active conda env > environment.yml > python3
PYTHON_CMD="python3"

# Check for active Conda environment (CONDA_PREFIX is set when conda env is activated)
if [ -n "$CONDA_PREFIX" ]; then
    PYTHON_CMD="python"
elif command -v conda >/dev/null && [ -f "$PROJECT_ROOT/environment.yml" ]; then
    ENV_NAME=$(grep -E "^name:" "$PROJECT_ROOT/environment.yml" | sed -E 's/^name:[[:space:]]*([^[:space:]#]+).*/\1/' | head -n1)
    # Use 'conda run' to execute in the specified environment without activating it
    [ -n "$ENV_NAME" ] && PYTHON_CMD="conda run --no-capture-output -n $ENV_NAME python"
fi

# Default port
PORT=${1:-8000}

# Set PYTHONPATH to project root so local packages are importable
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Start uvicorn server
echo "Starting FastAPI server on port $PORT..."
echo "API documentation: http://localhost:$PORT/docs"
echo "ReDoc: http://localhost:$PORT/redoc"
echo ""

cd "$PROJECT_ROOT"
$PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload

