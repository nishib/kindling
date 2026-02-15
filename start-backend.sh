#!/usr/bin/env bash
# Start the FastAPI backend (port 8001). Use a venv with deps installed.
set -e
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies (run once)..."
  pip install -r requirements.txt
fi

echo "Starting backend at http://localhost:8001"
exec python -m uvicorn server:app --reload --host 0.0.0.0 --port 8001
