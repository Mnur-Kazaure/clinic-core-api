# Kazaure Specialist Hospital EMR/HIS CMD Presentation Audit

Audit date: 2026-05-06  
Presentation date: 2026-05-07  
Scope reviewed: backend API, domain services, database models, migrations, frontend dashboards, auth/RBAC, billing, visits, admissions, follow-up, pharmacy, lab, audit/access logs, configuration, and tests in the current repository state.

## 1. Executive Summary

The current implementation is strongest as an outpatient, pharmacy, lab, billing, and operational governance EMR/HIS. There is real backend and frontend depth for patient registration, visits, triage, consultation, lab orders/results, prescriptions, pharmacy dispensing, cashier billing, accountant oversight, admission requests, ward/bed board, follow-up worklists, audit logging, role-based routing, and department/service-line scoping.

The system is not yet a complete hospital-wide inpatient EMR. It supports admission, discharge, wards, beds, bed assignment, discharge disposition, and an admin admissions dashboard, but inpatient clinical documentation is still thin: no dedicated nursing notes, medication administration record, inpatient progress notes, ward round notes, fluid charts, inpatient care plan, vitals charting by ward, or discharge summary workflow was found.

The CMD-specific ask is partially satisfied. There is a CMD role and `/cmd` dashboard, but the current CMD dashboard is pharmacy approval-focused, not a hospital-wide executive traceability cockpit. The best CMD demonstration should use `/admin/audit`, `/admin/reports`, `/admin/admissions`, `/cashier`, `/accountant`, `/cmd`, `/pharmacy-hod`, `/pharmacy-store`, `/reception`, and `/doctor` together.

Biometric time attendance is not implemented. Staff/user models exist, but no attendance table, biometric device identity mapping, attendance API, attendance import/sync job, lateness/absence model, or attendance dashboard was found.

## 2. Current System Readiness Verdict

Overall readiness score: **68 / 100**

Presentation readiness:

- Already implemented and demo-ready: OPD registration-to-consultation flow, triage, consultation, lab request/result flow, pharmacy workflow, cashier billing, accountant review, admission requests, bed board, follow-up worklist, RBAC role routing, audit/access log primitives.
- Partially implemented: inpatient workflow, CMD-level traceability, executive dashboards, security hardening, production crash-prevention, payment analytics, follow-up outcome reporting.
- Not implemented: biometric attendance integration, hospital-wide CMD activity cockpit, inpatient nursing/MAR/care-plan documentation, production deployment/backup/monitoring artifacts.
- Recommended for demo simulation: biometric attendance using a prepared CSV/import concept and dashboard mock, but label it explicitly as planned integration unless implemented before demo.
- Recommended for production implementation: immutable append-only audit store, attendance domain, inpatient documentation module, monitoring/backup/deployment hardening, endpoint-level RBAC audit.

## 3. System Stack Review

Backend:

- FastAPI app in `app/main.py`, mounted router at `/api/v1` from `app/api/v1/router.py`.
- SQLAlchemy ORM models in `app/models/*`; Alembic migrations in `alembic/versions/*`.
- Service layer exists in `app/services/*`, which is broadly consistent with Clean Architecture separation of API route, schema/model, and domain service.
- Health check exists at `/health`.

Frontend:

- Next.js app in `clinic-app/src/app/*`.
- API client uses Axios with `withCredentials` cookies in `clinic-app/src/api/client.ts`.
- Role route mapping exists in `clinic-app/src/shared/constants/roleRoutes.ts`.

Database/migrations:

- Rich model coverage exists for visits, triage, consultations, patients, admissions, wards, beds, follow-ups, lab, pharmacy, billing, receipts, refunds, cashier shifts, event logs, access logs, and audit review.
- Migration set is large and active. Risk: many untracked migration files are present in the working tree and should be reconciled before production deployment.

Auth/RBAC:

- Cookie-based JWT auth and refresh-token flow exist in `app/api/v1/auth.py`.
- Password hashing uses bcrypt through Passlib in `app/core/auth/passwords.py`.
- Role enum includes `CMD`, `ADMIN`, `CLINIC_ADMIN`, `DOCTOR`, `RECEPTION`, `CASHIER`, `ACCOUNTANT`, lab roles, pharmacy roles, `CHEW`, and `MIDWIFE`.
- Weakness: cookies set `secure=False`; this is acceptable locally but not production-ready.

Deployment/runtime:

- Local scripts exist for isolated backend/frontend and DB setup.
- No Dockerfile, compose, process supervisor, backup script, production deployment manifest, uptime monitoring config, or structured logging pipeline was found.

Logging/observability:

- Domain event logging exists through `EventService`.
- Access logging exists for patient/resource access and break-glass.
- `/admin/audit-timeline`, `/admin/clinic-health`, `/admin/system-metrics`, `/admin/compliance-summary`, and `/admin/payment-dashboard` exist.
- Missing: centralized exception handling, request correlation IDs, structured access logs, Sentry/OpenTelemetry, audit immutability controls, and production alerting.

Security:

- Good foundations: JWT, refresh tokens, hashed passwords, CORS config, role guards, department context, access logs, break-glass write rejection middleware.
- Gaps: `secure=False` cookies, no CSRF token layer for cookie-auth writes, broad CORS methods/headers, no rate limiting, no explicit HTTPS enforcement, no secrets rotation strategy, no file upload policy found, no WAF/proxy guidance, no immutable audit storage.

## 4. CMD Requirement Matrix

| Requirement | Current Status | Evidence/File/Route | Gap | Recommended Action | Demo Priority |
|---|---|---|---|---|---|
| Inpatient workflow | Partial | `app/models/admission.py`, `app/models/bed.py`, `app/api/v1/admissions.py`, `/admin/admissions` | Missing inpatient clinical notes, nursing notes, MAR, ward rounds, care plans | Demo admission request, bed assignment, discharge; label clinical inpatient charting as roadmap | High |
| Outpatient workflow | Demo-ready with polish | `app/models/visit.py`, `app/models/triage_assessment.py`, `app/api/v1/visit.py`, `/reception`, `/doctor`, `/lab`, `/pharmacy`, `/cashier` | Payment sequence may be split by lab/pharmacy billing and not shown as one linear OPD journey | Demo a prepared OPD patient end-to-end | Very High |
| Follow-up workflow | Partial to demo-ready | `app/models/follow_up.py`, `app/api/v1/follow_ups.py`, `/reception`, `/anc`, `/admin/follow-up` | Outcome tracking/reporting is limited; no dedicated follow-up dashboard route | Demo reception follow-up list and linked visit start | High |
| Biometric attendance integration | Not implemented | No attendance/biometric models or APIs found by repository search | No device integration, attendance logs, staff matching, lateness/absence dashboard | Present architecture plan only or implement minimum CSV import demo before presentation | High |
| Payment workflow | Demo-ready | `app/models/billing_ledger_entry.py`, `app/models/billing_item.py`, `app/models/payment_receipt.py`, `app/api/v1/billing.py`, `/cashier`, `/accountant` | `/admin/payments` is placeholder; refund approval is basic | Demo `/cashier` and `/accountant`, not `/admin/payments` | Very High |
| CMD user activity tracing | Partial | `app/models/event_log.py`, `app/models/access_log.py`, `app/api/v1/admin.py`, `/admin/audit`, `/admin/reports` | CMD role not granted to admin audit endpoints; CMD dashboard is pharmacy-only | Use admin/audit for demo; upgrade `/cmd` to enterprise audit cockpit | Very High |
| Roles and access control | Implemented, needs audit | `app/shared/enums.py`, `app/core/rbac.py`, `app/core/guards/*`, `clinic-app/src/shared/constants/roleRoutes.ts` | Some endpoints use broad `get_current_user`; CMD role underused in guards | Produce endpoint guard matrix and add tests for CMD/admin/auditor boundaries | High |
| Production crash prevention | Partial | `/health`, tests, idempotency, optimistic visit version | No production deployment, backups, monitoring, global exception normalization | Present checklist and implement hardening before go-live | Medium |
| Security implementation | Partial | Auth, RBAC, access logs, break-glass middleware | CSRF/rate-limit/secure cookies/HTTPS/audit immutability gaps | Present current controls plus hardening plan | Very High |

## 5. Dashboard-by-Dashboard Review

| Route | Intended role | Current classification | Existing features | Missing CMD-relevant features | Recommended action |
|---|---|---|---|---|---|
| `/login` | All users | Demo-ready | Cookie login | None for demo | Use first |
| `/confirm-access` | All authenticated users | Demo-ready | Role/session confirmation | Needs clearer multi-role selection if users have multiple roles | Use if role switching matters |
| `/reception` | Reception/records | Demo-ready | Patient registration, visit start, visit queue, follow-up list, linked follow-up visit | Revenue/audit not here | Use for OPD start |
| `/doctor` | Doctor | Demo-ready | Queue, consultation modal, lab request, prescription, lab results | Follow-up outcome capture should be clearer | Use for OPD consultation |
| `/lab` | Lab bench | Demo-ready | Lab queue, specimen/result workflow, QC tabs | Needs minimal explanation of paid gate | Use after doctor lab order |
| `/lab/manager` | Lab manager/HOD | Needs small polishing | Lab governance, verification, QC, sales, receipts | May be too detailed for CMD unless curated | Optional executive deep dive |
| `/pharmacy` | Pharmacist | Demo-ready | Dispensing queue, payment gate, stock/refills, activity | Keep scenario focused | Use after prescription/payment |
| `/pharmacy-hod` | Pharmacy HOD | Demo-ready but dense | Unit operations, approvals, sales, receipts, activity audit | Too much for short CMD demo | Use selected sections only |
| `/pharmacy-store` | Store officer | Demo-ready but dense | Inventory, requests, vouchers, dispatch, returns, activity | Needs concise script | Use only if CMD asks supply chain |
| `/cmd` | CMD | Needs functional upgrade | Pharmacy refill and catalog approvals | No hospital-wide traceability, attendance, payment, OPD/IPD overview | Use only for pharmacy CMD approval; do not present as full CMD cockpit |
| `/cashier` | Cashier | Demo-ready | Cashier shift, pending charges, pay items, receipts, transactions, audit | None critical | Use for payment workflow |
| `/cashier/transactions` | Cashier/admin | Needs small polishing | Transaction view exists | Unknown overlap with `/cashier` | Optional |
| `/accountant` | Accountant | Demo-ready | Revenue, departments, payment methods, sessions, refunds, outstanding, audit feed | Needs CMD-friendly summary | Use for revenue trace |
| `/accountant/dashboard` | Accountant | Should hide/remove | Re-export/empty 2-line route | Duplicates `/accountant` | Hide from nav |
| `/admin` | Admin/Clinic admin | Needs small polishing | Staff, profile, settings, quick actions, payment/patient cards | Stat cards still show awaiting feeds | Use only curated sections |
| `/admin/audit` | Admin/Clinic admin | Demo-ready | Event/access timeline | CMD role access not clear | Use for CMD traceability |
| `/admin/reports` | Admin/Clinic admin | Demo-ready | Compliance summary + audit timeline | Needs export/report generation | Use for compliance |
| `/admin/analytics` | Admin/Clinic admin | Needs small polishing | Staff heatmap, system metrics | Not all metrics meaningful if data sparse | Use only with seeded data |
| `/admin/health` | Admin/Clinic admin | Needs small polishing | Clinic health and staff coverage | Staff coverage is not biometric attendance | Avoid calling it attendance |
| `/admin/access` | Admin/Clinic admin | Needs functional upgrade | Read-only role matrix | Not generated from backend guards | Use as RBAC visual, caveat |
| `/admin/admissions` | Admin/Clinic admin | Demo-ready for bed management | Admission requests, bed board, wards, discharge, activity | Missing inpatient clinical charting | Use for inpatient operational demo |
| `/admin/follow-up` | Admin/Clinic admin | Demo-ready for config | Condition profiles and diagnosis mappings | Not patient follow-up worklist | Use only for configuration story |
| `/admin/payments` | Admin/Clinic admin | Placeholder/mock-only | Static placeholders | Payment API exists but page says feeds pending | Hide before presentation |
| `/admin/service-lines` | Admin/Clinic admin | Demo-ready admin config | Departments, service lines, user mapping | Too technical for CMD | Use only if access control questions arise |
| `/admin/settings` | Admin/Clinic admin | Needs small polishing | Clinic settings/billing defaults | Not strategic | Avoid unless asked |
| `/anc` | CHEW/ANC | Demo-ready as specialty OPD | ANC queue and pregnancy episode panels | Not part of CMD core list unless maternal services matter | Optional |
| `/maternity` | Midwife | Needs small polishing | Maternity queue/dashboard | Inpatient maternity overlap unclear | Optional |
| `/pharmacy/inventory` | Pharmacy | Should hide/remove | 5-line route; likely redirect/wrapper | Not a standalone feature | Hide unless verified |

## 6. Inpatient Workflow Assessment

Best dashboard/page to demonstrate:

- Primary: `/admin/admissions`
- Supporting APIs: `/api/v1/admissions`, `/api/v1/beds`, `/api/v1/wards`, `/api/v1/bed-board`

Existing backend APIs:

- Admission request create/list/approve/reject/cancel.
- Admission create/get/discharge/cancel/release bed.
- Bed list/create/assign/transfer/status/active.
- Ward list/create/range/status/active.
- Bed board and occupied-bed detail.

Existing frontend screens:

- `/admin/admissions` is a large functional dashboard for admission request queue, bed board, ward/bed controls, discharge, transfer, owner reassignment, and activity timeline.

Current data model support:

- Admission, admission request, ward, bed, bed assignment, admission-visit link, discharge disposition, discharge notes, bed status.

Missing states/statuses and clinical objects:

- No dedicated inpatient encounter/ward round.
- No nursing notes or nursing task list.
- No medication administration record.
- No inpatient vitals chart.
- No inpatient lab/medication order bundle tied directly to admission care episode.
- No discharge summary template.
- No dietary, procedure, theatre, or referral workflow.

Recommended industry-standard inpatient workflow:

Admission request -> Admission approval -> Ward/bed assignment -> Initial doctor clerking -> Nursing admission note -> Daily ward round notes -> Medication/lab orders -> MAR/nursing administration -> Billing updates -> Discharge planning -> Discharge summary -> Bed release -> Follow-up booking.

Demo approach:

- Demonstrate as **inpatient operations and bed management**, not a complete inpatient EMR chart.
- Say: "The admission, bed, and discharge backbone is implemented; clinical inpatient documentation is the next implementation phase."

## 7. Outpatient Workflow Assessment

Best dashboard/page to demonstrate:

- `/reception` -> `/doctor` -> `/lab` -> `/cashier` -> `/pharmacy` -> `/admin/audit`

Existing backend APIs:

- `/api/v1/patient`
- `/api/v1/visits/start`
- `/api/v1/visits/{visit_id}/triage/*`
- `/api/v1/consultations/start`
- `/api/v1/lab/request`
- `/api/v1/billing/*`
- `/api/v1/prescriptions`
- `/api/v1/pharmacy/*`

Current data model support:

- Patient, MRN, visit, triage assessment, consultation, lab request/result, prescription, billing item/ledger/receipt, dispensation, event/access logs.

Recommended workflow alignment:

Registration -> Triage -> Consultation -> Lab/Investigation -> Payment -> Pharmacy/Treatment -> Completed.

Current fit:

- Registration, triage, consultation, lab, billing, pharmacy, and completion are implemented.
- Visit statuses exist: `REGISTERED`, `TRIAGED`, `IN_CONSULTATION`, `LAB_REQUESTED`, `LAB_COMPLETED`, `PHARMACY_PENDING`, `COMPLETED`, `CANCELLED`.
- Triage lifecycle is separately modeled with `PENDING`, `TRIAGED`, `NOT_REQUIRED`.

Recommended demo script:

1. Register/search patient in `/reception`.
2. Start OPD visit and assign doctor.
3. Complete triage.
4. Doctor opens queue in `/doctor`, starts consultation.
5. Doctor orders lab or prescription.
6. Cashier collects payment in `/cashier`.
7. Lab/pharmacy executes service.
8. Show audit trail in `/admin/audit`.

## 8. Follow-up Workflow Assessment

Best dashboard/page to demonstrate:

- Reception follow-up list inside `/reception`.
- Clinician follow-ups in `/anc`/clinician components where wired.
- Configuration in `/admin/follow-up`.

Existing backend APIs:

- `/api/v1/follow-ups/my`
- `/api/v1/follow-ups/reception`
- `/api/v1/follow-ups/{follow_up_id}/reschedule`
- Condition profile and diagnosis mapping APIs.

Current data model support:

- Follow-up type, priority, status, due date, owner, reason, origin visit/admission, chronic recall link, completed visit, reschedule link.

Missing:

- Dedicated follow-up command dashboard.
- Outcome templates for "improved / not improved / referred / admitted / defaulted".
- SMS/phone-call reminder log.
- Missed appointment/default tracking.

Recommended industry-standard workflow:

Previous visit review -> Follow-up booking -> Reminder/contact -> Follow-up visit start -> Doctor review -> Treatment continuity -> Outcome tracking -> Reschedule/close.

Demo approach:

- Show a due follow-up in `/reception`, start a linked visit, then show continuity in `/doctor`.

## 9. Biometric Attendance Integration Plan

Current status: **Not implemented**.

Existing staff/user support:

- `app/models/user.py` has user identity, role, specialty, department, availability status.
- `app/models/department.py` and `app/models/user_department.py` support department mapping.

Missing attendance objects:

- No attendance log table.
- No biometric device table.
- No device user ID to staff/user mapping.
- No sync/import API.
- No lateness/absence computation.
- No attendance dashboard.

Recommended integration architecture:

1. Device captures fingerprint and stores device user ID.
2. Device exports logs by TCP/IP SDK, CSV, USB, or push endpoint.
3. HIS imports raw logs into `attendance_device_logs`.
4. HIS maps `device_user_id` to `users.id` or `staff_id`.
5. HIS normalizes clock-in/clock-out into `attendance_records`.
6. HR/Admin dashboard calculates present, late, absent, overtime, department summary.
7. CMD dashboard shows department-level attendance, exceptions, and trends.

Minimum viable demo implementation:

- Add `biometric_devices`, `staff_biometric_profiles`, `attendance_logs`, and `attendance_daily_summary`.
- Add CSV import endpoint: `/api/v1/attendance/import`.
- Add `/admin/attendance` or `/cmd/attendance` page with sample device sync status and department summaries.
- If not implemented before presentation, present this as planned integration, not completed software.

## 10. Payment Workflow Assessment

Existing payment implementation:

- Ledger model: `BillingLedgerEntry` links clinic, patient, optional visit, optional admission, actor, role, amount, currency, reason code, related reversal.
- Billing item model: item-level charges tied to visit, pay point, catalog/pharmacy item, status, paid amount.
- Payment receipts and receipt items exist.
- Refunds, receipt reprints, receipt sequence, cashier shifts, daily reports, transactions, dashboard streams, and accountant views exist.

Frontend:

- `/cashier` is the best payment demo.
- `/accountant` is the best finance oversight demo.
- `/admin/payments` should be hidden because it is placeholder-only despite backend payment dashboard support.

Auditability:

- Ledger captures actor ID and actor role.
- Receipt captures collected_by and pay point.
- Cashier shift supports open/close/reconcile.
- Refund supports requested/approved/processed actors, but approval workflow should be strengthened.

CMD revenue trace:

- Use `/accountant` for revenue by department, payment methods, refunds, outstanding bills, cashier sessions, fraud signals, and audit feed.
- Use `/cashier` for live collection and receipt generation.

## 11. CMD Audit Traceability Assessment

Current implementation:

- `EventLog` captures event type, actor ID, actor role, clinic, patient, payload, timestamps through Base.
- `AccessLog` captures actor, role, clinic, patient, action, purpose of use, justification, resource, break-glass flag, session/device ID.
- `AuditReviewCase` and `AuditReviewItem` support compliance review cases.
- `/admin/audit-timeline` merges event and access logs.

Gaps:

- CMD role is not clearly authorized for the admin audit timeline; the guard uses clinic admin.
- No before/after diff standard across all event payloads.
- IP address/user agent are not captured in access log model.
- Login success/logout events are not visibly logged; failed login is logged.
- Audit immutability is not enforced beyond normal database constraints.
- No dedicated CMD audit cockpit route for filtering by user, role, department, patient, visit, date, critical action, payment, and patient record access.

Recommended CMD-facing audit dashboard:

- `/cmd/audit` or upgraded `/cmd`.
- Filters: user, role, department, patient, visit/admission, date range, event type, payment receipt, break-glass.
- Panels: user activity timeline, login/logout trace, patient record access trace, payment trace, critical actions, department activity, suspicious access.

## 12. RBAC / Roles Assessment

Existing roles:

- `RECEPTION`, `CASHIER`, `ACCOUNTANT`, `CMD`, `DOCTOR`, lab roles, `PHARMACY`, `PHARMACY_HOD`, `PHARMACY_STORE_OFFICER`, `CHEW`, `MIDWIFE`, `ADMIN`, `CLINIC_ADMIN`, `SYSTEM`.

Frontend role routes:

- Role route mapping covers most roles, including `CMD -> /cmd`.

Strengths:

- Many domain guards exist under `app/core/guards/*`.
- Department context and service-line mapping exist.
- Lab and pharmacy unit access context exists.

Weaknesses:

- Some endpoints use broad `get_current_user` instead of role-specific guards.
- `CMD` is a role but not consistently included in executive read/audit/payment guards.
- `ADMIN` and `CLINIC_ADMIN` appear to overlap; ownership should be clarified.
- No explicit `AUDITOR`, `HR_ATTENDANCE_ADMIN`, or `IT_SUPPORT` roles.

Recommended hospital roles:

- CMD / Super Admin
- Hospital Admin
- Doctor
- Nurse
- Reception/Records
- Lab Scientist
- Pharmacist
- Cashier/Billing Officer
- HR/Attendance Admin
- Auditor/Compliance
- IT Support

## 13. Production Stability Assessment

Implemented foundations:

- `/health` endpoint.
- Idempotency support for visit transitions and selected workflows.
- Optimistic concurrency on visits.
- Extensive backend tests and some Playwright E2E specs.
- Domain-level exceptions in several services.

Production gaps:

- No production deployment manifests found.
- No automated backup scripts found.
- No monitoring/alerting config found.
- No global exception normalization middleware.
- No frontend error boundary strategy identified.
- No request ID/correlation ID.
- No rate limiting.
- No migration rollback playbook.
- No staging/prod separation documentation beyond local scripts.

Production-readiness checklist:

- Automated database backups and daily dump verification.
- Health check plus DB readiness endpoint.
- Global API exception normalization.
- Structured request logs with request ID.
- Frontend error boundaries.
- RBAC regression tests by endpoint.
- Alembic migration rollback strategy.
- Staging environment with seeded demo data.
- Uptime monitoring and alerting.
- Offline/export contingency for patient lists, receipts, and pharmacy stock.

## 14. Security Assessment

Implemented:

- Password hashing with bcrypt.
- JWT access tokens and refresh tokens.
- HTTP-only cookies.
- CORS origin config.
- Role guards and department context.
- Access log and break-glass support.
- Break-glass rejected on writes.

Security gaps:

- Cookies use `secure=False`; production must use `secure=True`.
- Cookie-auth write endpoints need CSRF protection or same-site/proxy hardening.
- CORS allows all methods/headers.
- No rate limiting for login or sensitive endpoints.
- No IP/user-agent capture in audit/access logs.
- No audit immutability design.
- No documented secrets management.
- No HTTPS enforcement.
- No file upload controls were found.

Recommended fixes:

- Enable secure cookies in production based on `APP_ENV`.
- Add CSRF token protection for state-changing requests.
- Add login throttling and API rate limits.
- Add request metadata to access logs.
- Make audit/event logs append-only by policy and DB permissions.
- Move secrets to managed environment/secret store.
- Add security headers at reverse proxy.

## 15. Features to Hide Before Presentation

- `/admin/payments`: placeholder-only page with "awaiting feed" despite backend APIs.
- `/accountant/dashboard`: empty/re-export route; use `/accountant`.
- `/pharmacy/inventory`: appears too thin as a standalone route; use `/pharmacy` stock section or `/pharmacy-store`.
- Any "attendance" claim: no biometric attendance implementation exists.
- Any claim of complete inpatient clinical charting: admission/bed workflow exists, but inpatient clinical documentation is not complete.
- Admin overview stat cards that show `—` or "Awaiting feed" unless populated before demo.

## 16. Features to Demonstrate

1. Login and role routing.
2. Reception patient registration/search.
3. OPD visit start and doctor assignment.
4. Triage assessment.
5. Doctor queue and consultation.
6. Lab request and lab workspace.
7. Prescription and pharmacy payment gate.
8. Cashier payment, receipt, and shift.
9. Accountant revenue and audit feed.
10. Admin audit timeline and compliance summary.
11. Admission request and bed assignment.
12. CMD pharmacy approval workflow.

## 17. Urgent Fixes Before Presentation

1. Seed a clean demo dataset with one OPD patient, one follow-up patient, one admission request, one cashier shift, one paid receipt, one lab request, one prescription, and one pharmacy CMD approval request.
2. Hide or remove nav links to placeholder pages, especially `/admin/payments`.
3. Add a CMD presentation note that biometric attendance is an integration plan unless implemented before demo.
4. Ensure `CMD` user can access the pages intended for CMD demo, or use an Admin/CMD combined demo account.
5. Prepare a scripted OPD path so the payment gate and pharmacy/lab states are predictable.
6. Prepare an inpatient scenario as operational admission/bed flow, not full clinical inpatient charting.
7. Ensure cookies/API base URL align in the presentation environment.
8. Verify `/admin/audit` has events after demo actions.
9. Remove "Clinic MVP" language from visible/product-facing presentation material if shown.
10. Run smoke tests and a browser walkthrough before the presentation.

## 18. Recommended Demo Flow for CMD

1. `/login`: sign in as Admin/CMD demo user.
2. `/reception`: register/search patient and start OPD visit.
3. `/reception`: complete triage.
4. `/doctor`: open queue, start consultation, record findings.
5. `/doctor`: create lab request and/or prescription.
6. `/cashier`: start shift if needed, collect payment, show receipt.
7. `/lab`: process lab queue/result, if lab scenario is used.
8. `/pharmacy`: show payment-cleared prescription and dispense.
9. `/admin/audit`: show trace of user actions.
10. `/admin/admissions`: show admission request approval, bed assignment, discharge/bed release.
11. `/reception`: show follow-up list and linked follow-up visit.
12. `/accountant`: show finance oversight and cashier session/revenue trace.
13. `/cmd`: show CMD pharmacy approval queue, explicitly as one CMD approval module.
14. Close with biometric attendance integration plan and production/security plan.

## 19. Implementation Roadmap After Presentation

Phase 1: Presentation hardening

- Hide placeholders, seed demo data, verify role access, stabilize demo scripts.

Phase 2: CMD cockpit

- Upgrade `/cmd` into enterprise dashboard: OPD/IPD/follow-up counters, revenue, attendance, audit, critical alerts, department performance, and approval queues.

Phase 3: Biometric attendance

- Add attendance models, device mapping, CSV/SDK import, HR dashboard, CMD summary, lateness/absence policies.

Phase 4: Inpatient clinical EMR

- Add nursing notes, ward round notes, MAR, inpatient orders, vitals chart, care plans, discharge summary, inpatient billing integration.

Phase 5: Production hardening

- Secure cookies, CSRF, rate limiting, request IDs, structured logs, backups, monitoring, staging/prod deployment, audit immutability, endpoint RBAC tests.

Phase 6: Enterprise QA

- Build workflow regression tests for OPD, IPD, follow-up, billing, pharmacy, lab, audit, and role boundaries.
