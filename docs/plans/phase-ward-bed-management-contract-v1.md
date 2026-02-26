# Phase: Ward / Bed Management Contract v1

## Role
- System Architect + Regulatory Gatekeeper

## Scope Lock

### In scope
- Formalize ward/bed operations on top of the existing Admission Request and Bed Assignment implementation.
- Keep current visit/admission enums; improve operational flexibility through workflow design, not enum churn.
- Provide an enterprise-safe bed board contract (occupancy visibility, assignment, transfer, release).
- Keep all write actions audited and tenant-isolated.

### Out of scope
- New admission status values.
- Bed auto-allocation AI/rule engine.
- Billing redesign.
- Inpatient clinical documentation redesign.

## Authoritative Invariants (must remain true)
- One ACTIVE admission per `(clinic_id, patient_id)`.
- One active bed assignment per admission.
- One active bed occupant per bed.
- No cross-clinic reads/writes.
- Bed assignment/transfer allowed only for ACTIVE admissions.
- Bed actions require active ward + active bed + bed status `AVAILABLE`.
- All lifecycle-changing actions emit event logs and remain traceable.

## Operational Model

### Core entities (existing)
- `admission_requests` = intake decision workflow.
- `admissions` = inpatient state.
- `wards` + `beds` = capacity inventory.
- `bed_assignments` = occupancy timeline.

### Canonical transitions
1. Admission request `PENDING` -> `APPROVED` creates `ACTIVE` admission.
2. `ACTIVE` admission -> bed `ASSIGN` (initial occupancy).
3. `ACTIVE` admission -> bed `TRANSFER` (intra-facility move).
4. Admission `DISCHARGED`/`CANCELLED` auto-releases active bed assignment.

## RBAC Contract
- `CLINIC_ADMIN` / `ADMIN`: full ward-bed governance and admission approvals.
- `RECEPTION`: request visibility and admission intake operations as already permitted.
- `DOCTOR`: admission request creation only for assigned active visits.
- Bed inventory mutation remains restricted to bed-management roles (admin side).

## API Contract v1 (design target)

### Keep (already live)
- `GET /v1/wards`
- `POST /v1/wards`
- `GET /v1/beds`
- `POST /v1/beds`
- `POST /v1/beds/assign`
- `POST /v1/beds/transfer`
- Admission request/approval/reject/cancel endpoints.

### Add (next implementation slice)
1. `POST /v1/beds/{bed_id}/status`
   - Purpose: controlled switch between `AVAILABLE` and `OUT_OF_SERVICE`.
   - Guard: deny `OUT_OF_SERVICE` if bed currently occupied.
2. `GET /v1/bed-board`
   - Returns ward-level occupancy summary + per-bed status snapshot.
   - Required for deterministic dashboard rendering.
3. `POST /v1/admissions/{admission_id}/bed/release`
   - Manual release only for ACTIVE admissions when patient leaves bed before discharge.
   - Must not close admission automatically.

## Frontend Contract v1 (design target)

### Admin / Admission dashboard
- Keep request queue and decision flow.
- Add bed-board panel:
  - occupancy by ward,
  - available/occupied/out-of-service counts,
  - quick filter by ward.
- Bed action modal keeps explicit error mapping for:
  - bed unavailable,
  - admission inactive,
  - transfer target same as current.

### UX requirements
- No hidden state changes.
- Every destructive/irreversible action has confirmation.
- Button states always reflect backend truth after refresh.

## Audit & Event Contract
- Continue append-only event model.
- Required events for ward-bed lifecycle:
  - `ADMISSION_REQUEST_CREATED`
  - `ADMISSION_REQUEST_APPROVED`
  - `ADMISSION_REQUEST_REJECTED`
  - `ADMISSION_REQUEST_CANCELLED`
  - `PATIENT_ADMITTED`
  - `BED_ASSIGNED`
  - `BED_TRANSFERRED`
  - `PATIENT_DISCHARGED`
  - `ADMISSION_CANCELLED`
- New events to add with v1 expansion:
  - `BED_STATUS_CHANGED`
  - `BED_RELEASED`

## Concurrency Safety Contract
- Use row-level locking on admission/bed/assignment records for all write workflows.
- Convert integrity races into deterministic `409` API responses.
- Event writes stay in same transaction scope as state mutation.

## Test Gates (must pass before seal)
- Unit/integration:
  - no second active admission for same patient,
  - no second active assignment for same admission,
  - no second active occupant for same bed,
  - transfer requires active admission + different target bed,
  - out-of-service guard blocks assignment.
- Contract tests:
  - queue/list DTO fields stay stable for frontend.
- Smoke:
  - request -> approve -> assign -> transfer -> discharge path.

## Seal Status
- Contract v1 drafted from validated implementation baseline.
- Ready for implementation planning pack execution.
