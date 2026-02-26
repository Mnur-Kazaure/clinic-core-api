# Phase: Ward / Bed Management Implementation Pack v1

## Execution Principle
- Sequence changes in small, testable slices.
- No schema/status churn beyond defined contract.
- Preserve backward compatibility for existing admission flows.

## Phase 0 — Baseline Gate
1. Run migration state check (`alembic heads` and DB at head).
2. Run backend suite (`pytest app/tests -q`).
3. Run targeted frontend lint on admission/bed screens.

Exit criteria:
- Backend green.
- No lint errors in touched frontend files.

## Phase 1 — Bed Board Read Model
Backend:
- Add `GET /v1/bed-board` read endpoint:
  - ward summary counts,
  - per-bed occupancy snapshot,
  - linked active admission id and patient context (name/MRN masked fallback).
- Add schema DTOs for board payload.

Frontend:
- Add board section to `clinic-app/src/app/admin/admissions/page.tsx`.
- Keep existing queue UI; board is additive.

Tests:
- API contract test for deterministic payload shape.
- Tenant isolation and occupancy accuracy test.

## Phase 2 — Bed Status Lifecycle Controls
Backend:
- Add `POST /v1/beds/{bed_id}/status`.
- Rules:
  - `AVAILABLE` <-> `OUT_OF_SERVICE`.
  - Block switch to `OUT_OF_SERVICE` when active assignment exists.
  - Emit `BED_STATUS_CHANGED`.

Frontend:
- Add action menu on bed board row for status switch.
- Add confirm dialog with reason (audit reason).

Tests:
- Occupied bed cannot be marked out-of-service.
- Status switch is idempotent and audited.

## Phase 3 — Manual Bed Release Workflow
Backend:
- Add `POST /v1/admissions/{admission_id}/bed/release`.
- Rules:
  - Requires ACTIVE admission.
  - Releases current active bed assignment only.
  - Does not discharge/cancel admission.
  - Emit `BED_RELEASED`.

Frontend:
- Add "Release Bed" action for active assigned admissions.
- Success state refreshes queue + board.

Tests:
- Release clears active assignment.
- Repeat release returns clean conflict/no-op response contract.

## Phase 4 — Hardening + Rollout
- Add regression tests for request -> approve -> assign -> transfer -> release -> discharge.
- Add API error mapping table to frontend for deterministic operator messages.
- Run short manual smoke checklist on admin admission dashboard.

## Rollout Checklist
1. Merge backend + frontend with migration notes.
2. Apply migrations to staging.
3. Perform smoke using seeded admission scenarios.
4. Seal phase with test evidence attached.

## Ownership
- Backend: `app/api/v1/beds.py`, `app/services/bed_service.py`, `app/schemas/bed.py`.
- Frontend: `clinic-app/src/app/admin/admissions/page.tsx`, `clinic-app/src/domains/bed/services/bedService.ts`.
- Tests: `app/tests/test_bed_*`, `app/tests/test_admission_*`.
