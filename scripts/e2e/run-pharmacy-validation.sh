#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

source scripts/dev-env.sh

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

derive_role_email() {
  local email="$1"
  local suffix="$2"
  local local_part="${email%@*}"
  local domain_part="${email#*@}"
  printf '%s+%s@%s' "$local_part" "$suffix" "$domain_part"
}

require_http_ready() {
  local url="$1"
  local label="$2"
  local attempts="${3:-40}"
  local delay_seconds="${4:-1}"
  local attempt
  for attempt in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay_seconds"
  done
  printf 'Expected %s to be reachable at %s\n' "$label" "$url" >&2
  return 1
}

backend_pid=''
frontend_pid=''

cleanup() {
  if [[ -n "$backend_pid" ]]; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$frontend_pid" ]]; then
    kill "$frontend_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

start_backend_if_needed() {
  if require_http_ready "http://${BACKEND_HOST}:${BACKEND_PORT}/health" "backend health" 1 1; then
    log "Backend already reachable at http://${BACKEND_HOST}:${BACKEND_PORT}"
    return 0
  fi

  log "Starting isolated backend"
  ./scripts/start-backend-isolated.sh > /tmp/pharmacy-e2e-backend.log 2>&1 &
  backend_pid="$!"
  require_http_ready "http://${BACKEND_HOST}:${BACKEND_PORT}/health" "backend health"
}

start_frontend_if_needed() {
  if require_http_ready "${E2E_BASE_URL}/login" "frontend login page" 1 1; then
    log "Frontend already reachable at ${E2E_BASE_URL}"
    return 0
  fi

  log "Starting isolated frontend"
  ./scripts/start-frontend-isolated.sh > /tmp/pharmacy-e2e-frontend.log 2>&1 &
  frontend_pid="$!"
  require_http_ready "${E2E_BASE_URL}/login" "frontend login page"
}

E2E_RECEPTION_EMAIL="${E2E_RECEPTION_EMAIL:-e2e.reception@example.com}"
E2E_RECEPTION_PASSWORD="${E2E_RECEPTION_PASSWORD:-Password123!}"
E2E_CHEW_EMAIL="${E2E_CHEW_EMAIL:-e2e.chew@example.com}"
E2E_CHEW_PASSWORD="${E2E_CHEW_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_MIDWIFE_EMAIL="${E2E_MIDWIFE_EMAIL:-e2e.midwife@example.com}"
E2E_MIDWIFE_PASSWORD="${E2E_MIDWIFE_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_DOCTOR_EMAIL="${E2E_DOCTOR_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "doctor")}"
E2E_DOCTOR_PASSWORD="${E2E_DOCTOR_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_LAB_EMAIL="${E2E_LAB_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "lab")}"
E2E_LAB_PASSWORD="${E2E_LAB_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_PHARMACY_EMAIL="${E2E_PHARMACY_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "pharmacy")}"
E2E_PHARMACY_PASSWORD="${E2E_PHARMACY_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_CMD_EMAIL="${E2E_CMD_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "cmd")}"
E2E_CMD_PASSWORD="${E2E_CMD_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_PHARMACY_HOD_EMAIL="${E2E_PHARMACY_HOD_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "pharmacy-hod")}"
E2E_PHARMACY_HOD_PASSWORD="${E2E_PHARMACY_HOD_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_PHARMACY_STORE_EMAIL="${E2E_PHARMACY_STORE_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "pharmacy-store")}"
E2E_PHARMACY_STORE_PASSWORD="${E2E_PHARMACY_STORE_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"
E2E_CASHIER_EMAIL="${E2E_CASHIER_EMAIL:-$(derive_role_email "$E2E_RECEPTION_EMAIL" "cashier")}"
E2E_CASHIER_PASSWORD="${E2E_CASHIER_PASSWORD:-${E2E_RECEPTION_PASSWORD}}"

E2E_RUN_TOKEN="${E2E_RUN_TOKEN:-$(date '+%Y%m%d%H%M%S')}"
E2E_PHARMACY_WORKFLOW_PATIENT_NAME="${E2E_PHARMACY_WORKFLOW_PATIENT_NAME:-Playwright Pharmacy Workflow Patient ${E2E_RUN_TOKEN}}"
E2E_PHARMACY_WORKFLOW_PHONE_NUMBER="${E2E_PHARMACY_WORKFLOW_PHONE_NUMBER:-0800000${E2E_RUN_TOKEN: -4}}"
E2E_PHARMACY_WORKFLOW_BATCH_NUMBER="${E2E_PHARMACY_WORKFLOW_BATCH_NUMBER:-PW-PHARM-001}"
E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY="${E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY:-40}"
E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY="${E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY:-10}"
E2E_PHARMACY_WORKFLOW_DISPENSE_QUANTITY="${E2E_PHARMACY_WORKFLOW_DISPENSE_QUANTITY:-5}"
E2E_PHARMACY_RETURN_ITEM_NAME="${E2E_PHARMACY_RETURN_ITEM_NAME:-Playwright Return Flow Commodity ${E2E_RUN_TOKEN}}"
E2E_PHARMACY_RETURN_BATCH_NUMBER="${E2E_PHARMACY_RETURN_BATCH_NUMBER:-PW-RETURN-${E2E_RUN_TOKEN: -4}}"
E2E_PHARMACY_RETURN_ISSUED_QUANTITY="${E2E_PHARMACY_RETURN_ISSUED_QUANTITY:-8}"
E2E_PHARMACY_RETURN_REQUEST_QUANTITY="${E2E_PHARMACY_RETURN_REQUEST_QUANTITY:-3}"

export E2E_RECEPTION_EMAIL E2E_RECEPTION_PASSWORD
export E2E_CHEW_EMAIL E2E_CHEW_PASSWORD
export E2E_MIDWIFE_EMAIL E2E_MIDWIFE_PASSWORD
export E2E_DOCTOR_EMAIL E2E_DOCTOR_PASSWORD
export E2E_LAB_EMAIL E2E_LAB_PASSWORD
export E2E_PHARMACY_EMAIL E2E_PHARMACY_PASSWORD
export E2E_CMD_EMAIL E2E_CMD_PASSWORD
export E2E_PHARMACY_HOD_EMAIL E2E_PHARMACY_HOD_PASSWORD
export E2E_PHARMACY_STORE_EMAIL E2E_PHARMACY_STORE_PASSWORD
export E2E_CASHIER_EMAIL E2E_CASHIER_PASSWORD
export E2E_RUN_TOKEN
export E2E_PHARMACY_WORKFLOW_PATIENT_NAME
export E2E_PHARMACY_WORKFLOW_PHONE_NUMBER
export E2E_PHARMACY_WORKFLOW_BATCH_NUMBER
export E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY
export E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY
export E2E_PHARMACY_WORKFLOW_DISPENSE_QUANTITY
export E2E_PHARMACY_RETURN_ITEM_NAME
export E2E_PHARMACY_RETURN_BATCH_NUMBER
export E2E_PHARMACY_RETURN_ISSUED_QUANTITY
export E2E_PHARMACY_RETURN_REQUEST_QUANTITY

log "Ensuring isolated backend and frontend availability"
start_backend_if_needed
start_frontend_if_needed

log "Seeding deterministic pharmacy workflow"
PYTHONPATH=. .venv/bin/python scripts/seed_playwright_users.py \
  --reception-email "$E2E_RECEPTION_EMAIL" \
  --reception-password "$E2E_RECEPTION_PASSWORD" \
  --chew-email "$E2E_CHEW_EMAIL" \
  --chew-password "$E2E_CHEW_PASSWORD" \
  --midwife-email "$E2E_MIDWIFE_EMAIL" \
  --midwife-password "$E2E_MIDWIFE_PASSWORD" \
  --doctor-email "$E2E_DOCTOR_EMAIL" \
  --doctor-password "$E2E_DOCTOR_PASSWORD" \
  --lab-email "$E2E_LAB_EMAIL" \
  --lab-password "$E2E_LAB_PASSWORD" \
  --pharmacy-email "$E2E_PHARMACY_EMAIL" \
  --pharmacy-password "$E2E_PHARMACY_PASSWORD" \
  --cmd-email "$E2E_CMD_EMAIL" \
  --cmd-password "$E2E_CMD_PASSWORD" \
  --pharmacy-hod-email "$E2E_PHARMACY_HOD_EMAIL" \
  --pharmacy-hod-password "$E2E_PHARMACY_HOD_PASSWORD" \
  --pharmacy-store-email "$E2E_PHARMACY_STORE_EMAIL" \
  --pharmacy-store-password "$E2E_PHARMACY_STORE_PASSWORD" \
  --pharmacy-workflow-patient-name "$E2E_PHARMACY_WORKFLOW_PATIENT_NAME" \
  --pharmacy-workflow-phone-number "$E2E_PHARMACY_WORKFLOW_PHONE_NUMBER" \
  --pharmacy-workflow-batch-number "$E2E_PHARMACY_WORKFLOW_BATCH_NUMBER" \
  --pharmacy-workflow-stock-quantity "$E2E_PHARMACY_WORKFLOW_STOCK_QUANTITY" \
  --pharmacy-workflow-prescribed-quantity "$E2E_PHARMACY_WORKFLOW_PRESCRIBED_QUANTITY" \
  --pharmacy-return-item-name "$E2E_PHARMACY_RETURN_ITEM_NAME" \
  --pharmacy-return-batch-number "$E2E_PHARMACY_RETURN_BATCH_NUMBER" \
  --pharmacy-return-issued-quantity "$E2E_PHARMACY_RETURN_ISSUED_QUANTITY"

log "Running pharmacy role dashboard smoke"
pnpm -C clinic-app exec playwright test e2e/role-dashboard-smoke.spec.ts --project=chromium --grep "CMD|PHARMACY|PHARMACY_HOD|PHARMACY_STORE_OFFICER"

log "Running cashier dashboard workspace smoke"
pnpm -C clinic-app exec playwright test e2e/cashier-dashboard-workspace.spec.ts --project=chromium

log "Running pharmacy end-to-end workflow"
pnpm -C clinic-app exec playwright test e2e/pharmacy-workflow.spec.ts --project=chromium

log "Running pharmacy return-to-store workflow"
pnpm -C clinic-app exec playwright test e2e/pharmacy-return-workflow.spec.ts --project=chromium

log "Pharmacy validation completed successfully"
printf 'Workflow patient: %s\n' "$E2E_PHARMACY_WORKFLOW_PATIENT_NAME"
