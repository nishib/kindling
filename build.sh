#!/usr/bin/env bash
# Render build script
set -e

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "==> Verifying frontend build..."
if [ -d "frontend/dist" ]; then
    echo "✓ Frontend built successfully!"
else
    echo "✗ ERROR: Frontend build failed - dist directory not found"
    exit 1
fi

echo "==> Build complete!"
