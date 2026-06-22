# CURRENT RECEPTION AND DOCTOR IMPLEMENTATION AUDIT

Version: v1.0
Status: Current-state audit before redesign
Audience: architects, engineers, designers, auditors, product reviewers, and AI agents

## 1. Purpose

This document records the current Reception and Doctor / Clinical Records frontend implementation before enterprise clinical workspace redesign.

This is an audit and exposure document only. It does not approve a redesign, change workflows, or introduce new backend behavior.

## 2. Audit Scope

Audited frontend files:

| Area | Files Reviewed |
|---|---|
| Reception route | `clinic-app/src/app/reception/page.tsx` |
| Reception auth/layout | `clinic-app/src/app/reception/layout.tsx` |
| Reception visit queue | `clinic-app/src/app/reception/components/visit/VisitQueue.tsx` |
| Reception patient registry | `clinic-app/src/app/reception/components/patient/PatientRegistryPanel.tsx` |
| Doctor route | `clinic-app/src/app/doctor/page.tsx` |
| Doctor auth/layout | `clinic-app/src/app/doctor/layout.tsx` |
| Doctor queue | `clinic-app/src/app/doctor/components/DoctorQueue.tsx` |
| Doctor consultation modal | `clinic-app/src/app/doctor/components/consultation/ConsultationModal.tsx` |
| Shared header | `clinic-app/src/app/components/Header.tsx` |

Screenshots were not captured in this pass. Findings are based on source inspection.

## 3. Current Reception Implementation Structure

### Route Structure

| Route | Purpose |
|---|---|
| `/reception` | Reception dashboard for patient registration, visit intake, queue coordination, follow-up handling, and patient registry review |

### Auth And Layout

`clinic-app/src/app/reception/layout.tsx`:

- client-side auth guard
- role context guard
- requires `RECEPTION` role
- redirects unauthorized users to `/confirm-access`
- loads clinic profile for the shared header
- wraps content in `DashboardUserProvider`
- renders shared `Header`

### Workspace Model

Current model:

```text
Reception Dashboard
|-- Hero / role context
|-- Queue KPI cards
|-- Optional patient registration form
|-- Success / error banners
|-- Quick Actions
|-- Recent Activity
|-- Follow-Ups
|-- Visit Queue
|-- Patient Registry
|-- Start Visit modal
|-- Visit Details modal
`-- Reschedule Follow-Up modal
```

### Current Navigation

The Reception implementation does not have an internal sidebar navigation model.

It uses:

- global application header
- hero action buttons
- cards and modal actions
- visit queue filter controls
- follow-up quick search
- patient registry search and pagination

### Current Section / Subsection Model

Reception currently uses a single-page operational dashboard rather than section/subsection switching.

Current visible sections include:

- Dashboard hero: `Reception Dashboard`
- Queue Total
- Waiting (Registered/Triaged)
- Completed (Queue)
- Emergency (Queue)
- Quick Actions
- Recent Activity
- Follow-Ups
- Visit Queue
- Patient Registry

### Current Workflow Capabilities

Reception currently supports:

- register patient
- start new visit
- continue existing active visit
- view visit details
- view queue statistics
- filter visit queue by status
- review recent visit activity
- review today/tomorrow follow-ups
- start linked follow-up visits
- reschedule follow-up records
- search patient registry
- view patient registration details
- switch reception department context where allowed departments exist

### Current Strengths

- Real operational workflow exists, not static demo content.
- Reception auth boundary is enforced.
- Patient registration, visit start, queue review, follow-up handling, and registry search are already connected into a practical workflow.
- Visit queue includes operational statuses such as emergency, admitted, registered, triaged, consultation, laboratory, pharmacy pending, completed, and cancelled.
- Follow-up workflow includes linked visit creation and rescheduling.
- Patient registry access includes `PurposeOfUse.OPERATIONS` and justification text.
- Department context exists through allowed department selection.

### Current Architecture Observations

- Reception currently behaves as a centralized front-desk dashboard with optional department context, not a full enterprise intake workspace model.
- The route includes intake, follow-up, registry, visit queue, and modal workflows in one page.
- Department reception is partially present through `allowedDepartments`, but not yet expressed as a governed Department Workspace Architecture.
- Reception is correctly treated as intake capability, but it is not yet modeled as multiple department intake sub-workspaces such as GOPD Reception, A&E Intake, Specialist Clinic Reception, or Maternity Reception.

### Current UI / UX Observations

- The interface is functional and operationally clear.
- Visual language is still older light-card dashboard styling, not yet aligned with the newer premium HIS workstations.
- The dashboard uses a long operational page rather than focused sidebar workspaces.
- Large workflows are exposed through cards and modals, which is practical but may become dense as outpatient, inpatient, follow-up, and department-specific intake workflows expand.
- Patient Registry uses a conventional table with horizontal overflow protection.
- The dashboard has nested semantic layout risk: `layout.tsx` renders a `<main>` and `page.tsx` also renders a `<main>`.

### Current Fragmentation / Problems

- No internal sidebar or workspace navigation for intake categories.
- Reception and patient registry are mixed into the same route without clear enterprise workspace ownership.
- Follow-up operations are present but not yet separated into a governed Follow-Up Intake / Recall sub-workspace.
- Department reception context exists but does not yet expose department-specific intake models.
- Older commented implementation remains in `reception/layout.tsx`, which should be cleaned in a future code hygiene pass.
- Current title `Reception Dashboard` should eventually align with HIS terminology such as Reception Intake Workspace or Patient Intake Workspace, subject to redesign approval.

### Missing For Enterprise HIS Maturity

- governed reception workspace architecture
- department intake model for GOPD, A&E, Specialist Clinics, Maternity, and other high-volume departments
- clearer separation of registration, visit intake, follow-up, registry, and queue workspaces
- explicit outpatient vs inpatient intake pathways
- stronger triage and emergency intake posture
- role-sensitive navigation for reception supervisors versus standard reception operators
- enterprise visual alignment with the newer HIS workstation design language
- formal audit posture for patient lookup, break-glass, visit continuation, and follow-up rescheduling

## 4. Current Doctor / Clinical Records Implementation Structure

### Route Structure

| Route | Purpose |
|---|---|
| `/doctor` | Doctor clinical workspace for consultation queue, clinical documentation, lab requests, prescriptions, lab results, and visit details |

### Auth And Layout

`clinic-app/src/app/doctor/layout.tsx`:

- client-side auth guard
- role context guard
- requires `DOCTOR` role
- redirects unauthorized users to `/confirm-access`
- loads clinic profile for the shared header
- wraps content in `DashboardUserProvider`
- renders shared `Header`

### Workspace Model

Current model:

```text
Doctor Dashboard
|-- Hero / role context
|-- Overview KPI cards
|-- Patient Queue
|-- Active Consultations
|-- Consultation Actions
|-- Completed Visits Today
|-- Recent Activity
|-- Consultation modal
|-- Lab Request modal
|-- Prescription modal
|-- Lab Results modal
`-- Visit Details modal
```

### Current Navigation

The Doctor implementation does not have an internal sidebar navigation model.

It uses:

- global application header
- queue status filter
- selected patient context
- action cards
- modals for documentation and orders

### Current Section / Subsection Model

Doctor currently uses a single-page clinical workspace rather than section/subsection switching.

Current visible sections include:

- Dashboard hero: `Doctor Dashboard`
- Overview
- Today's Consultations
- In Progress
- Completed Today
- Pending Lab Results
- Emergency Flagged
- Patient Queue
- Active Consultations
- Consultation Actions
- Completed Visits Today
- Recent Activity

### Current Workflow Capabilities

Doctor currently supports:

- load doctor queue
- poll doctor queue near real-time
- filter queue by registered, in consultation, emergency, and lab requested
- start consultation from registered/triaged/in-consultation visits
- resume active consultations
- view completed consultations
- record consultation notes through modal workflow
- request laboratory tests
- view laboratory results
- issue prescriptions
- send eligible visit to pharmacy
- view visit details
- request admission from visit details
- show active consultation state and lab result readiness

### Current Strengths

- Real clinical workflow exists and uses live services.
- Doctor auth boundary is enforced.
- Queue polling is implemented.
- Consultation flow includes record locking semantics for completed consultations.
- Lab request and prescription workflows are integrated with the clinical context.
- Visit transitions include conflict handling and allowed-transition checks.
- Visit details use `PurposeOfUse.TREATMENT`, which aligns with clinical access intent.
- Active consultations and lab status are visible without leaving the route.

### Current Architecture Observations

- The current route is a doctor workstation rather than a broader Clinical Records Workspace.
- EMR functionality is present through consultation notes, vitals, diagnosis, prescriptions, lab orders, and visit details, but it is not explicitly framed as the EMR / Clinical Records subdomain inside HIS.
- Outpatient consultation, emergency consultation, admitted patient review, follow-up review, and pharmacy/lab handoff are currently collapsed into one doctor route.
- The route is operationally useful but not yet organized as a governed clinical workspace with outpatient, inpatient, follow-up, and department-specific work modes.

### Current UI / UX Observations

- The interface is functional and clinician-oriented.
- Visual language is older light-card styling and does not yet match the newer enterprise workstation polish.
- Main work occurs through queue selection plus modal actions, which is efficient but may become constrained as clinical domains expand.
- Active consultation context is present, but the workspace does not yet provide a persistent clinical sidebar or patient chart shell.
- Clinical documentation occurs in modals, not a full clinical record workspace.
- The dashboard has nested semantic layout risk: `layout.tsx` renders a `<main>` and `page.tsx` also renders a `<main>`.

### Current Fragmentation / Problems

- No internal sidebar for clinical work modes.
- The route title `Doctor Dashboard` underrepresents the EMR / Clinical Records domain.
- Consultation, lab request, prescription, lab result review, and visit detail review are modal-heavy rather than structured as a clinical record workspace.
- Outpatient, inpatient, follow-up, A&E, ward review, specialist clinic, maternity, pediatric, and theatre review pathways are not yet governed in the UI architecture.
- No explicit patient chart timeline or longitudinal clinical record view is visible at the route level.
- Clinical handoffs to laboratory, pharmacy, admission, ward, and follow-up exist as actions but not as a mature cross-domain navigation model.

### Missing For Enterprise HIS Maturity

- approved Clinical Records Workspace structure
- doctor sidebar or clinical workspace rail
- outpatient consultation workspace
- inpatient / ward review workspace
- follow-up / recall workspace
- clinical record timeline
- orders workspace for lab, radiology, pharmacy, and procedures
- diagnosis/problem list model
- clinical notes model by encounter
- department-aware clinical workflows
- admission and discharge clinical workflow visibility
- enterprise visual alignment with KSH Enterprise HIS terminology

## 5. Cross-Implementation Findings

### Shared Strengths

- Both routes enforce role-specific access.
- Both routes use shared clinic branding through the global header.
- Both routes support real operational workflows instead of placeholder screens.
- Both routes rely on domain services and existing backend behavior.
- Both routes have patient/visit traceability foundations.

### Shared Risks

- Both routes are single-page dashboards, not yet department-workspace architectures.
- Both routes use older dashboard naming and styling compared to CMD, Accountant, and Revenue Collection Desk.
- Both routes contain nested `<main>` landmarks through layout/page composition.
- Both routes need HIS terminology alignment: Reception as intake capability and Doctor as EMR / Clinical Records domain.
- Both routes require careful redesign planning before changing workflows because they appear to be connected to live operational services.

## 6. Recommended Architecture Direction For Next Design Phase

Do not redesign immediately without sealed clinical workflow architecture.

Recommended next governance work:

1. Define Reception Intake Workspace architecture.
2. Define Clinical Records Workspace architecture.
3. Define outpatient, inpatient, and follow-up workflow ownership.
4. Define department intake sub-workspaces for GOPD, A&E, Specialist Clinics, and Maternity.
5. Define ward review and admitted-patient workflow ownership.
6. Define clinical handoff contracts to Laboratory, Radiology, Pharmacy, Cashier, and Admissions.
7. Define audit requirements for patient lookup, visit access, clinical record access, and break-glass use.

## 7. Implementation Boundary

This audit did not modify frontend code, backend services, APIs, database schema, routes, role guards, or workflows.

Future changes must preserve existing operational behavior unless a separate implementation plan approves migration.
