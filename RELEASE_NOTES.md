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
