#!/bin/bash
set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Export PYTHONPATH
export PYTHONPATH=$PROJECT_ROOT

# Activate venv if exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

echo "🚀 Starting WAS to OSS Migration Agent from $PROJECT_ROOT"
echo "📂 Logs will be in $PROJECT_ROOT/logs"

# Install requirements if needed (optional step, typically handled by docker/setup)
# pip install -r $PROJECT_ROOT/backend/requirements.txt

# Run Uvicorn
# --reload for dev mode
uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --app-dir "$PROJECT_ROOT"
