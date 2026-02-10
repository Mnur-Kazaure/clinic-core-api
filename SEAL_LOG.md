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

## Phase 9 — ANC/Maternity v1.0
- Status: READY_FOR_SEAL (manual UI proof gate pending)
- Date: 2026-02-08
- Scope: Service-line routing (`OPD|ANC|MATERNITY`), owner-role enforcement, ANC/Maternity queue/workspace flows, and scoped PMR summary access for CHEW/MIDWIFE.

### Evidence (Current)
- Alembic head migration run completed.
- Backend suite run on target branch: `pytest app/tests` → **94 passed**.
- New ANC/Maternity endpoints and services are present (`/api/v1/anc`, `/api/v1/maternity`).

### Pending Proof Gate (Required Before Seal)
- Reception manual smoke: start ANC/MATERNITY visits and assign correct owners.
- CHEW manual smoke: queue visibility, episode/encounter create, sign immutability.
- MIDWIFE manual smoke: queue visibility, delivery draft/sign, postnatal + family planning append.
- PMR policy smoke: CHEW/MIDWIFE summary-only access allowed only for assigned active visit.

## Phase 10 — Flexible Visit Workflow v1.0.1
- Status: READY_FOR_SEAL (final runtime smoke pending)
- Date: 2026-02-08
- Scope: Outstanding-work completion pre-checks, override completion with reason codes, optimistic concurrency, and pharmacy/visit continuity.

### Evidence (Current)
- Postgres regression gate:
  - `app/tests/test_flexible_visit_workflow_completion.py`
  - `app/tests/test_visit_start_service_line_owner.py`
  - `app/tests/test_visit_start_after_completion.py`
  - Result: **11 passed**

### Controls Verified
- Normal completion blocks with `VISIT_HAS_OUTSTANDING_WORK` when labs/prescriptions are pending.
- Override completion requires reason code; `OTHER` requires min-length reason text.
- Override completion records immutable history snapshot (`pending_labs_count_snapshot`, `unfulfilled_prescriptions_count_snapshot`) with source `override`.
- Version conflict is enforced through `expected_version`.
- Visit restart-after-completion behavior remains valid.

### Pending Proof Gate (Required Before Seal)
- Runtime UI smoke in Reception:
  - Complete visit (normal path) when outstanding is zero.
  - Complete visit (override path) with reason picker and confirmation modal.
  - Confirm user guidance links and no dead-end workflow traps.
