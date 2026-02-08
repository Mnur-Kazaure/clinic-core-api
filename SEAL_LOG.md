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

## Phase 7 — Patient Medical Record + MRN (PMR)
- Status: SEALED
- Date: 2026-02-01
- Scope: PMR read semantics, MRN issuance/retirement, revocation-aware identity closure, and audit-safe access logging.

### Evidence (Proof Gates)
- Fresh Postgres DB: `clinic_pmr_pg`
- Alembic head: `f7a8b9c0d1e2`
- Test suite: `pytest app/tests` with `POSTGRES_TEST_URL` → **63 passed**

### Controls Verified
- MRN uniqueness is DB-enforced and case-insensitive (CITEXT + UNIQUE).
- Single ACTIVE MRN per patient per clinic enforced via partial unique index.
- MRN issuance is race-safe (sequence row lock + transactional insert).
- Identity closure excludes revoked mappings and detects cycles.
- PMR access logging emits `ACCESS_LOGGED` and `BREAK_GLASS_USED` with `patient_id_requested` + `patient_id_canonical`.
- Break-glass is read-only and uses Phase 5 access log invariants.

## Phase 8 — Admission Stability + Bed Assignment
- Status: SEALED
- Date: 2026-02-08
- Scope: Admission discharge disposition semantics and bed assignment invariants.

### Evidence (Proof Gates)
- Fresh Postgres DB: `clinic_admission_pg`
- Alembic head: `ad12ef34ab56`
- Test suite: `pytest app/tests` with `POSTGRES_TEST_URL` → **94 passed** (2 deprecation warnings)

### Controls Verified
- DISCHARGED admissions require `discharged_at` + `discharge_disposition`; CANCELLED requires `cancel_reason` + `cancelled_at` (mutually exclusive with discharge).
- Disposition constraints enforced: TRANSFERRED_OUT requires `transferred_to_facility`; DECEASED requires `death_pronounced_at`; transfer and death are mutually exclusive.
- Bed assignment invariants: an admission cannot be assigned a second active bed; transfers require an existing active assignment.
- Bed occupancy is derived from active `bed_assignments` (`released_at IS NULL`); beds.status remains serviceability only.
