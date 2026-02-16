#!/usr/bin/env bash
# Render build script for Python + React
set -e

echo "==> Installing Node.js via nvm..."
# Install nvm if not present
if [ ! -d "$HOME/.nvm" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
fi
# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
# Install and use Node 20
nvm install 20
nvm use 20

echo "==> Node.js version: $(node --version)"
echo "==> npm version: $(npm --version)"

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Building React frontend..."
cd frontend
npm ci --prefer-offline --no-audit
npm run build
cd ..

echo "==> Verifying frontend build..."
if [ -d "frontend/dist" ]; then
    echo "✓ Frontend built successfully in frontend/dist/"
    ls -la frontend/dist/
else
    echo "✗ ERROR: Frontend build failed - dist directory not found"
    exit 1
fi

echo "==> Build complete!"
