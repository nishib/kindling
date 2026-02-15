#!/usr/bin/env bash
# Render start script for Kindling
# Starts the FastAPI server (which also serves the built frontend)
set -e

# Render sets PORT environment variable
PORT=${PORT:-8000}

echo "Starting Kindling on port $PORT..."
exec uvicorn server:app --host 0.0.0.0 --port $PORT
