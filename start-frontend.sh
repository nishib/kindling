#!/usr/bin/env bash
# Start the Vite frontend (port 3000). Proxies /api and /health to backend on 8000.
set -e
cd "$(dirname "$0")"

npm install
npm run dev
