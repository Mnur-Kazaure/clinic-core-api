# SEALED CLINICAL RECORDS NAVIGATION ARCHITECTURE

Version: v1.0
Status: Sealed navigation architecture target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

This document defines the approved sidebar/workspace navigation architecture for the Clinical Records Workspace.

The Clinical Records Workspace is the EMR / Clinical Records subdomain inside KSH Enterprise HIS. It is the clinical documentation and care decision workspace for doctors and authorized clinical roles.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Doctor / Clinical Records = clinical documentation and care decision workspace
```

Clinical Records navigation must preserve persistent patient context across notes, orders, results, prescriptions, admission, discharge, and follow-up.

## 3. Approved Sidebar Navigation

```text
Clinical Records Workspace
|-- Clinical Overview
|-- My Patient Queue
|-- OPD Consultations
|-- Follow-Up Consultations
|-- Inpatient Reviews
|-- Emergency Consultations
|-- Patient Chart
|-- Clinical Notes
|-- Orders
|-- Results Review
|-- Prescriptions
|-- Admission Decisions
|-- Discharge Summaries
`-- Clinical Audit Trail
```

## 4. Persistent Clinical Context Shell

The Clinical Records Workspace must include a persistent patient context shell whenever a patient or encounter is selected.

The doctor should never lose patient context while moving between:

- notes
- orders
- results
- prescriptions
- admission
- discharge
- follow-up

### Patient Context Header

The patient context header should preserve:

| Context Field | Purpose |
|---|---|
| Patient name | Confirms active patient identity |
| MRN | Confirms enterprise patient identifier |
| Age / Sex | Supports clinical context |
| Active visit | Shows current encounter/visit |
| Department | Shows current department or clinical service |
| Priority | Shows routine, urgent, emergency, or high-risk posture |
| Allergies / Alerts if available | Surfaces safety-critical warnings |

### Encounter Rail

The encounter rail should preserve longitudinal and active-care context:

| Encounter Area | Purpose |
|---|---|
| Active encounter | Current consultation, review, or admission context |
| Previous visits | Prior encounters and continuity context |
| Follow-ups | Follow-up history, due follow-ups, missed/rescheduled states |
| Admissions | Past/current admissions and ward context |
| Lab/Radiology orders | Ordered, pending, completed, and reviewed investigations |
| Prescriptions | Active and prior prescriptions with pharmacy handoff state |

## 5. Navigation Item Ownership

| Navigation Item | Purpose | Clinical Ownership | What Doctor Sees | Allowed Actions | Handoff Targets | Audit Requirements |
|---|---|---|---|---|---|---|
| Clinical Overview | Show clinical workload and active care posture | Clinical Records | active consultations, queue pressure, pending results, follow-up due, inpatient review needs | open patient context, open queue, inspect clinical alerts | Reception, Lab, Radiology, Pharmacy, Ward | access event, patient context opened, alert viewed |
| My Patient Queue | Manage assigned patients awaiting consultation/review | Clinical Records | registered/triaged/in-consultation patients, emergency flags, lab status, waiting time | select patient, start/resume consultation, view visit details | Reception/Triage, Ward | queue access, patient selected, consultation started |
| OPD Consultations | Conduct outpatient consultations | Clinical Records | OPD patient chart, vitals, complaints, diagnosis, plan, orders | create/update notes, complete consultation, create orders, prescribe, book follow-up | Lab, Radiology, Pharmacy, Follow-Up, Billing | note create/update, diagnosis, order, prescription, completion |
| Follow-Up Consultations | Review linked return visits | Clinical Records | previous encounter context, follow-up reason, prior plan, outcome | continue treatment, update notes, place orders, prescribe, book next follow-up | Reception, Lab, Radiology, Pharmacy | original encounter link, follow-up review, outcome, next booking |
| Inpatient Reviews | Review admitted patients | Clinical Records | ward, bed, admission context, nursing notes, vitals, active orders | ward review, update plan, request investigations, discharge decision | Nursing/Ward, Lab, Radiology, Pharmacy, Billing | ward review, order, discharge decision, chart access |
| Emergency Consultations | Manage urgent/A&E clinical review | Clinical Records | emergency priority, triage context, presenting issue, urgent vitals | start emergency review, order urgent investigations, admit/escalate, prescribe | A&E, Lab, Radiology, Pharmacy, Ward | emergency chart access, urgent order, admission decision |
| Patient Chart | Longitudinal patient chart shell | Clinical Records | demographics, encounter timeline, diagnoses, medications, investigations, alerts, signed records | review chart, open encounter, view signed records, add authorized addendum where supported | All clinical domains | chart access, record viewed, addendum where applicable |
| Clinical Notes | Encounter documentation | Clinical Records | vitals, complaints, history, examination, diagnosis, plan | save draft, update encounter note, complete/sign record | Patient Chart, Orders, Prescriptions | note access, create/update, signature/completion |
| Orders | Clinical order workspace | Clinical Records | lab/radiology/pharmacy/procedure orders, status, indication | create order, review order status, cancel/modify where policy permits | Laboratory, Radiology, Pharmacy, Billing | order created/changed/cancelled, indication, actor |
| Results Review | Review diagnostic results | Clinical Records | lab/radiology results, pending/ready status, abnormal flags, source order | view result, acknowledge/review, add interpretation note where supported | Laboratory, Radiology, Patient Chart | result access, review/acknowledgement |
| Prescriptions | Medication prescribing and pharmacy handoff | Clinical Records | medication list, dose, frequency, duration, pharmacy status | issue prescription, update before signing where allowed, send to pharmacy | Pharmacy, Billing | prescription create/update, pharmacy handoff |
| Admission Decisions | Convert outpatient/emergency patient to inpatient admission | Clinical Records | admission indication, diagnosis, ward request, priority | request admission, update admission reason, send to bed/ward workflow | Ward/Nursing, Admission Admin, Billing | admission decision, reason, ward target |
| Discharge Summaries | Document clinical discharge | Clinical Records | admission summary, diagnosis, treatment, discharge plan, follow-up | create/sign discharge summary, add follow-up plan | Ward/Nursing, Billing, Follow-Up | summary create/update/sign, discharge decision |
| Clinical Audit Trail | Clinical access and action trace | Clinical Records / Compliance | chart access, note edits, orders, prescriptions, signatures, result reviews | view audit events, filter by patient/visit/action | Audit & Compliance, CMD oversight | immutable read-only audit record |

## 6. Clinical Workspace Principles

- The selected patient must remain visible while moving between workspace sections.
- The selected encounter must remain visible while moving between notes, orders, results, prescriptions, admission, and follow-up.
- Longitudinal chart review must not replace active encounter documentation; both contexts must be clear.
- Completed/signed records must be read-only except through governed correction/addendum workflows.
- Handoffs to Laboratory, Radiology, Pharmacy, Ward, Billing, and Follow-Up must preserve encounter linkage.
- Emergency context must remain visible until emergency workflow is resolved or transferred.

## 7. Clinical Boundary Rules

Clinical Records must not own:

- patient registration
- cashier payment collection
- accountant reconciliation
- pharmacy inventory management
- lab sample processing
- radiology image acquisition
- CMD executive governance
- platform administration

Clinical Records may initiate orders and decisions that hand off to those domains, but it must not execute their operational work.

## 8. Audit Requirements

Each navigation area must preserve audit traceability for:

- patient chart access
- purpose of use
- encounter selected
- clinical note create/update/sign
- diagnosis create/update
- order create/update/cancel
- prescription create/update/send
- result view/review/acknowledgement
- admission decision
- discharge summary create/update/sign
- follow-up decision
- actor
- role
- workstation
- timestamp
- patient ID
- MRN
- visit/encounter ID

## 9. Demo Vs Production Boundary

This document defines navigation architecture before UI redesign.

Current Doctor implementation may only partially support these navigation items. Frontend demonstrations must clearly identify simulated or placeholder clinical navigation until backend APIs exist.

Production implementation requires patient chart aggregation APIs, encounter APIs, order lifecycle APIs, prescription APIs, result review APIs, admission/discharge APIs, follow-up APIs, immutable clinical audit logging, and role-based clinical authorization.

## 10. Governance Constraint

No engineer, designer, or AI agent may redesign the Doctor route as a generic dashboard.

It must evolve toward a governed Clinical Records Workspace with persistent patient context and longitudinal encounter continuity inside KSH Enterprise HIS.

