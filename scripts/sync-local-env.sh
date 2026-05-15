#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT_DIR/scripts/dev-env.sh"

if [[ -z "${AUTH_JWT_SECRET_KEY:-}" ]]; then
  AUTH_JWT_SECRET_KEY="$(openssl rand -hex 48)"
fi

cat >"$ROOT_DIR/.env" <<EOF
APP_ENV=dev
DATABASE_URL=${DATABASE_URL}
CORS_ORIGINS=${CORS_ORIGINS}

AUTH_JWT_SECRET_KEY=${AUTH_JWT_SECRET_KEY}
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ACCESS_TOKEN_TTL_SECONDS=3600
AUTH_REFRESH_TOKEN_TTL_DAYS=14
EOF

cat >"$ROOT_DIR/clinic-app/.env.local" <<EOF
NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
EOF

echo "Updated backend env: $ROOT_DIR/.env"
echo "Updated frontend env: $ROOT_DIR/clinic-app/.env.local"
