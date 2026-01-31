# SEAL_LOG.md
# Regulatory Phase Seals

## Phase 5 — Break-Glass Access + Audit Review Console
- Status: SEALED
- Date: 2026-01-30
- Scope: Break-glass access controls, dual logging, audit review workflow, append-only audit trails.

### Evidence (Proof Gates)
- Fresh Postgres DB: `clinic_phase5_pg`
- Alembic head: `d5e6f7a8b9c0`
- Test suite: `pytest app/tests` with `POSTGRES_TEST_URL` → **49 passed**

### Controls Verified
- access_logs stores `purpose_of_use`, `justification`, `resource`, `break_glass` with DB-level checks.
- Break-glass dual logging enforced: `ACCESS_LOGGED` + `BREAK_GLASS_USED` (payload includes `access_log_id`).
- audit_review_cases + audit_review_items + audit_review_case_history with append-only triggers.
- RBAC enforced for audit review operations.
- Global prevention of break-glass on write endpoints (middleware + service guards).

## Phase 6 — Billing & Claims Ledger
- Status: SEALED
- Date: 2026-01-31
- Scope: Append-only billing ledger, charge catalog, clinic currency discipline, and billing RBAC.

### Evidence (Proof Gates)
- Fresh Postgres DB: `clinic_phase6_pg`
- Alembic head: `e6f7a8b9c0d1`
- Test suite: `pytest app/tests` with `POSTGRES_TEST_URL` → **56 passed**

### Controls Verified
- billing_ledger_entries append-only enforcement with DB triggers.
- Composite tenant FKs + unique (id, clinic_id) for self-FK integrity.
- Entry-type context and sign rules enforced.
- Reversal rules enforced (no reversal of reversal; related entry required).
- Identity-merge reads include transitive mapped-from patient IDs.
- Clinic currency discipline enforced for ledger writes.
