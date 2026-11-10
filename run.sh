#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "==> Creating Python venv and installing backend deps"
  python3 -m venv .venv
  .venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -d frontend/node_modules ]; then
  echo "==> Installing frontend deps"
  (cd frontend && npm install)
fi

if [ ! -f backend/data/recordings.json ]; then
  echo "==> Generating demo data (5 MP3 parts + transcripts)"
  "$PY" scripts/generate_demo_data.py
fi

echo "==> Starting backend on http://localhost:8000"
(cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

echo "==> Starting frontend on http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT
echo
echo "Open http://localhost:5173 in your browser. Ctrl+C to stop."
wait
