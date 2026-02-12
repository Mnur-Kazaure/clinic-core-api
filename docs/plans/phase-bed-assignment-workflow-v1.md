# Phase: Bed Assignment Workflow v1

## Scope Lock

### In scope
- Wire admission-to-bed assignment flow end-to-end in backend + UI.
- Enforce inventory-safe bed assignment/reassignment behavior using existing bed invariants.
- Add deterministic user-facing errors for capacity/ownership conflicts.
- Add role-based UI states for reception/admission users during assignment actions.
- Add automated tests for assignment success, duplicate prevention, and conflict handling.

### Out of scope
- New admission or visit status enums.
- Bed transfer optimization/auto-balancing.
- Historical data backfill.
- Dashboard redesign outside the assignment flow surfaces.

## Deliverables

1. Backend workflow contract for assign/reassign/release bed.
2. UI flow in admission-related dashboards for assign/reassign/release actions.
3. Error mapping table (HTTP -> user message) for assignment operations.
4. Test gates:
   - Backend pytest for assignment lifecycle and invariants.
   - Frontend smoke (manual checklist + Playwright target flow).

## Gate Criteria (must pass before merge)
- `pytest app/tests -k "bed or admission"` passes.
- Required GitHub check `anc-export-role-matrix` passes on PR.
- Manual smoke:
  - Assign bed to active admission.
  - Reassign bed to another available bed.
  - Release bed and verify inventory state.
  - Attempt conflicting assignment and receive clean error.

## Execution Order
1. Backend contract verification + API hardening.
2. UI wiring with guarded actions.
3. Tests + smoke pass.
4. PR, CI, merge, and phase seal.
