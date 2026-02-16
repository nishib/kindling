#!/usr/bin/env bash
# Render start script
set -e

echo "Starting Kindling server..."
echo "Port: ${PORT:-8000}"
echo "Database initialization will happen in FastAPI lifespan"

# Start uvicorn server (database init happens automatically in server.py lifespan)
exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
