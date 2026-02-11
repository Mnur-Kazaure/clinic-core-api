# RELEASE_NOTES.md

## Phase 5 — Break-Glass Access + Audit Review Console (2026-01-30)

### Added
- Break-glass access logging with required purpose-of-use, justification, and resource.
- Dual logging: `ACCESS_LOGGED` + `BREAK_GLASS_USED` with `access_log_id` correlation.
- Audit review workflow: cases, items, and immutable case history.
- Append-only enforcement for audit items and history (Postgres + SQLite triggers).
- Global middleware to reject break-glass on write endpoints.
- New audit-related enums: purpose-of-use and audit case/item lifecycle.

### Changed
- Access log schema renamed `reason` → `justification`.
- `purpose_of_use` now an enum with DB-level constraints.
- EventService supports transactional event creation via `build_event`.

### Migrations
- `d5e6f7a8b9c0_phase5_break_glass_audit_review.py`
  - Safe backfill for access logs (non-destructive).
  - Normalizes out-of-range `purpose_of_use` values to `OPERATIONS`.
  - Adds audit review tables, constraints, triggers, and indexes.

### Tests Added/Updated
- Break-glass DB constraint enforcement.
- Audit review workflow, append-only, and tenant isolation (Postgres).
- Break-glass write-bypass prevention (middleware).
- Access logging + break-glass event correlation.

### Compatibility Notes
- Existing access logs are preserved; only NULL or invalid `purpose_of_use` values are normalized.
- `break_glass` is permitted only on read endpoints; write attempts return 403.

## Phase 6 — Billing & Claims Ledger (2026-01-31)

### Added
- Canonical, append-only billing ledger with composite tenant FKs and reversal support.
- Charge catalog for standardized billable items.
- Billing API endpoints (charge, payment, reversal, patient ledger read).
- Billing guards and RBAC for charge/payment/reversal/read access.
- Clinic currency support and enforcement for ledger writes.

### Changed
- New billing enums for entry type and reason codes.
- API router includes billing routes.

### Migrations
- `e6f7a8b9c0d1_phase6_billing_ledger.py`
  - Adds billing ledger + charge catalog tables, enums, constraints, indexes, and append-only triggers.
  - Adds `billing_currency` to clinics with default `NGN`.

### Tests Added/Updated
- Billing append-only enforcement (Postgres).
- Entry-type context rule enforcement (Postgres).
- Currency discipline and reversal rules.
- External reference uniqueness (Postgres).
- Identity-merge transitive read closure.

## Phase 7 — Patient Medical Record + MRN (PMR) (2026-02-01)

### Added
- PMR API endpoint with canonical identity resolution and revocation-aware closure.
- MRN issuance service with Luhn check digit and transactional sequence locking.
- MRN registry with case-insensitive uniqueness (CITEXT) and append-only deletes blocked.
- PMR access logging with required payload fields: requested + canonical patient IDs.
- PMR guards for role + assignment-based access with break-glass support.

### Changed
- Identity merge flow now retires merged-from MRNs and ensures a single ACTIVE MRN on canonical identity.
- Access log service supports PMR-specific payload fields.

### Migrations
- `f7a8b9c0d1e2_pmr_mrn_registry.py`
  - Adds `clinic_mrn_sequences` and `patient_mrns`.
  - Enforces case-insensitive MRN uniqueness and single ACTIVE MRN per patient per clinic.
  - Append-only delete protection and immutable core MRN fields.
  - Adds revocation index to support closure filtering.

### Tests Added/Updated
- Case-insensitive MRN uniqueness (Postgres).
- Single ACTIVE MRN constraint (Postgres).
- Concurrent MRN issuance safety (Postgres).
- Merge retires MRN for non-canonical patient.
- PMR access logging payload fields + break-glass payload validation.
- Identity closure respects revocations.

### Compatibility Notes
- MRN core fields are immutable; status/retire fields are lifecycle-managed in place.
- Break-glass logging remains Phase 5 compliant (no new fields, uses `justification`).

## Phase 9 — ANC/Maternity v1.0 (2026-02-08)

### Added
- Service-line support in visit flows for `ANC` and `MATERNITY`.
- Role-aware owner validation at visit start:
  - `OPD -> DOCTOR`
  - `ANC -> CHEW`
  - `MATERNITY -> MIDWIFE`
- ANC module API and workspace scaffolding:
  - queue, active episode, episode detail
  - previous pregnancies append
  - encounter draft/sign lifecycle
- Maternity module API and workspace scaffolding:
  - queue
  - delivery draft/sign lifecycle
  - append-only postnatal notes
  - append-only family planning events
- CHEW/MIDWIFE PMR summary guard aligned to assigned active visit policy.

### Verified
- Full backend suite on current branch: `pytest app/tests` → **94 passed**.
- Migration head applies cleanly with ANC/Maternity schema included.

### Pending Manual Gate
- Final seal requires role-based UI smoke pass in real workflow context (Reception/CHEW/MIDWIFE).

## Phase 10 — Flexible Visit Workflow v1.0.1 (2026-02-08)

### Verified
- Postgres regression gate passed:
  - `test_flexible_visit_workflow_completion.py`
  - `test_visit_start_service_line_owner.py`
  - `test_visit_start_after_completion.py`
  - Result: **11 passed**

### Behavior Confirmed
- Completion pre-check returns structured outstanding snapshot and override hints.
- Override completion enforces reason codes and captures immutable snapshot context in history.
- Optimistic concurrency (`expected_version`) returns deterministic conflict handling.
- Completed visits remain compatible with fresh-visit start flow.

### Pending Manual Gate
- Final runtime seal requires Reception UI smoke of normal vs override completion flows.
