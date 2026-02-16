#!/usr/bin/env bash
# Start the FastAPI backend (port 8001). Ensures DB is inited when DATABASE_URL is set.
set -e
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing dependencies (run once)..."
  pip install -r requirements.txt
fi

# Ensure database tables and pgvector (init_db loads .env from repo root)
echo "Ensuring database is initialized..."
if python init_db.py; then
  echo "Database ready."
else
  echo "Warning: database init failed (set DATABASE_URL in .env and start Postgres, or ignore if not using DB). Backend will start; /health will show disconnected."
fi

echo "Starting backend at http://localhost:8001"
exec python -m uvicorn server:app --reload --host 0.0.0.0 --port 8001
