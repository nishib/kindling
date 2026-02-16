#!/usr/bin/env bash
# Render build script
set -e

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Build complete!"
