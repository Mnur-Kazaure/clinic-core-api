#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/scripts/dev-env.sh"

if ss -ltn | awk '{print $4}' | grep -Eq ":${BACKEND_PORT}$"; then
  echo "Port ${BACKEND_PORT} is already in use. Set BACKEND_PORT to a free port and retry."
  exit 1
fi

cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Create it first: python3 -m venv .venv && .venv/bin/pip install -r requirements"
  exit 1
fi

if [[ ! -x .venv/bin/alembic ]]; then
  echo "Missing .venv/bin/alembic. Install backend dependencies before starting."
  exit 1
fi

echo "Applying database migrations..."
.venv/bin/alembic upgrade head

exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT"
