#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi, cv2, numpy, PIL" >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -f "frontend/dist/index.html" ]; then
  echo "Building frontend..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

echo ""
echo "Rocogi 洛克工坊"
echo "  http://127.0.0.1:8787"
echo "  API docs: http://127.0.0.1:8787/docs"
echo ""

exec .venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8787
