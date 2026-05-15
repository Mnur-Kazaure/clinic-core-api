#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/scripts/dev-env.sh"

if ss -ltn | awk '{print $4}' | grep -Eq ":${FRONTEND_PORT}$"; then
  echo "Port ${FRONTEND_PORT} is already in use. Set FRONTEND_PORT to a free port and retry."
  exit 1
fi

cd "$ROOT_DIR/clinic-app"

if [[ ! -d node_modules ]]; then
  echo "Missing node_modules. Install first: pnpm install"
  exit 1
fi

exec pnpm dev --port "$FRONTEND_PORT"
