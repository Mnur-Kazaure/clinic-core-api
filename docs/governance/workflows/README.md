# Workflow Governance

This folder contains sealed and current-state workflow governance documents for KSH Enterprise HIS.

Workflow governance defines patient journeys, role ownership, state transitions, handoffs, audit requirements, and future backend integration requirements before UI redesign or implementation changes.

## Architecture Principle

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Reception = intake capability
Doctor / Clinical Records = clinical documentation and care decision workspace
```

Workflow governance comes before UI redesign.

No engineer, designer, or AI agent should materially change Reception, Doctor / Clinical Records, outpatient, inpatient, or follow-up workflows without reviewing the relevant sealed workflow specification.

## Sealed Workflow Specifications

| Document | Purpose | Status |
|---|---|---|
| `SEALED_RECEPTION_INTAKE_WORKSPACE_SPEC.md` | Defines Reception as the enterprise patient intake and visit initiation workspace | Sealed target |
| `SEALED_GOPD_INTAKE_WORKSPACE_SPEC.md` | Defines GOPD Intake as the first department-specific intake pattern under unified Reception Intake Architecture | Sealed target |
| `SEALED_GOPD_INTAKE_NAVIGATION_ARCHITECTURE.md` | Defines sidebar/workspace navigation for GOPD Intake before UI redesign | Sealed target |
| `SEALED_GOPD_INTAKE_UI_ARCHITECTURE.md` | Defines enterprise UI/UX architecture for GOPD Intake before frontend implementation | Sealed target |
| `SEALED_OUTPATIENT_WORKFLOW.md` | Defines outpatient patient journey governance from arrival through consultation, orders, payment handoff, completion, and follow-up | Sealed target |
| `SEALED_CLINICAL_RECORDS_WORKSPACE_SPEC.md` | Defines EMR / Clinical Records as the clinical documentation and care decision subdomain inside HIS | Sealed target |
| `SEALED_CLINICAL_RECORDS_NAVIGATION_ARCHITECTURE.md` | Defines Clinical Records navigation, persistent patient context shell, and encounter rail before UI redesign | Sealed target |
| `SEALED_CLINICAL_RECORDS_UI_ARCHITECTURE.md` | Defines enterprise EMR / Clinical Records UI architecture before frontend implementation | Sealed target |
| `SEALED_INPATIENT_WORKFLOW.md` | Defines inpatient admission, ward care, doctor review, discharge clearance, and discharge summary governance | Sealed target |
| `SEALED_FOLLOWUP_WORKFLOW.md` | Defines follow-up / return visit governance and clinical continuity requirements | Sealed target |

## Current-State Audits

| Document | Purpose |
|---|---|
| `CURRENT_RECEPTION_DOCTOR_IMPLEMENTATION_AUDIT.md` | Audits current Reception and Doctor route implementation before enterprise clinical workspace redesign |

## Implementation Boundary

These workflow documents may define target behavior before implementation exists.

Future frontend work must clearly distinguish:

- current implemented workflow behavior
- frontend demonstration workspace behavior
- production backend/API-backed behavior

No workflow document should overclaim implemented functionality.

## Governance Warning

Reception and Doctor / Clinical Records are workflow-critical operational systems.

Changes affecting intake, visit creation, queue routing, consultation, clinical documentation, orders, prescriptions, admission, discharge, or follow-up must preserve role ownership, state traceability, auditability, and HIS parent architecture alignment.

GOPD Intake is the first department-specific intake pattern. Other department intake workspaces should inherit its unified-patient, department-context, movement-governance model rather than creating independent patient systems.

Clinical Records navigation must preserve persistent patient context. Doctors must not lose patient identity, active encounter, or longitudinal history while moving between notes, orders, results, prescriptions, admission, discharge, and follow-up.
