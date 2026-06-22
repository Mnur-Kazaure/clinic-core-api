# SEALED GOPD INTAKE NAVIGATION ARCHITECTURE

Version: v1.0
Status: Sealed navigation architecture target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

This document defines the approved sidebar/workspace navigation architecture for the GOPD Intake Workspace.

This is not a visual redesign specification. It defines navigation ownership, workspace boundaries, allowed actions, and future backend requirements before Reception UI modernization.

## 2. Architecture Foundation

GOPD Intake is a department-specific intake workspace inside unified KSH Enterprise HIS.

Reception is distributed operationally but unified architecturally.

GOPD Intake must use shared patient identity, shared MRN, shared EMR / Clinical Records, shared visit history, shared billing, and shared audit trail.

## 3. Approved Sidebar Navigation

```text
GOPD Intake Workspace
|-- Intake Overview
|-- Patient Lookup
|-- Patient Registration
|-- Start OPD Visit
|-- GOPD Queue
|-- Triage Routing
|-- Doctor Assignment
|-- Reassignment / Rerouting
|-- Internal Referral
|-- Emergency Escalation
|-- Follow-Up Arrival
`-- Intake Audit Trail
```

## 4. Navigation Item Ownership

| Navigation Item | Purpose | What User Sees | Allowed Actions | Ownership Boundary | Future Backend Requirement |
|---|---|---|---|---|---|
| Intake Overview | Show GOPD intake posture and queue pressure | arrivals, waiting count, triage pressure, emergency flags, follow-up arrivals, active reassignment/referral alerts | refresh view, open focused queues, inspect alerts | intake visibility only; no clinical decisions | GOPD queue summary API, routing summary API, alert/event API |
| Patient Lookup | Find existing patient before registration or visit creation | search by MRN, name, phone, active visit, recent visit, follow-up due state | search patient, view intake-safe summary, open start visit flow | must not expose unrestricted clinical record; use operational purpose of use | patient search API, active visit detection, access audit |
| Patient Registration | Register new patient only after lookup confirms no existing identity | demographic form, contact details, identity checks, duplicate warning | create patient profile, cancel registration, continue to start visit | must not create duplicate patient when matching identity exists | patient registration API, duplicate detection, MRN issuance, audit logging |
| Start OPD Visit | Create outpatient visit under GOPD context | selected patient, visit type, department, priority, reason, doctor/triage routing option | create OPD visit, route to GOPD queue, route to triage where required | must not create clinical note or diagnosis | visit creation API, department context API, state transition API |
| GOPD Queue | Manage patients waiting in GOPD pathway | GOPD waiting patients, status, priority, waiting time, triage state, assigned doctor where available | view visit, send to triage, assign doctor, open reassignment/referral/escalation workflow | queue management only; no clinical signing | GOPD queue API, queue filtering, priority and status API |
| Triage Routing | Route patients to triage when policy or risk requires | waiting triage candidates, emergency indicators, triage readiness, triage outcomes | route to triage, mark triage required, return to queue after triage result | triage execution belongs to Nursing/Triage; GOPD initiates/routs | triage routing API, triage status API, nursing handoff API |
| Doctor Assignment | Assign or route GOPD patient to doctor queue | eligible patients, available doctors/clinic queues, assignment status, workload signals | assign doctor, change assignment before consultation, route to doctor queue | doctor owns consultation; GOPD only routes/assigns | doctor queue API, assignment API, workload/availability API |
| Reassignment / Rerouting | Correct wrong queue or wrong department before consultation | source queue, proposed target, reason, active visit conflict, audit warning | reassign visit, reroute queue, cancel reassignment draft | must not erase prior queue history; pre-consultation correction only | reassignment API, routing rules, queue state machine, audit log |
| Internal Referral | Initiate governed routing to another department/specialty | referral target, reason, source visit, target department reception status | create internal referral, route to target department, add intake note | clinical referral decision belongs to Doctor/Clinical Records unless policy allows intake-level routing | referral API, target department queue API, authorization policy API |
| Emergency Escalation | Move urgent GOPD patient to A&E pathway | urgent flags, escalation reason, A&E target, emergency handoff summary | escalate to A&E, mark emergency, notify A&E intake/triage | A&E owns emergency intake after escalation; GOPD preserves source context | emergency escalation API, A&E queue API, notification/audit API |
| Follow-Up Arrival | Check in returning patient and link to follow-up workflow | due follow-ups, patient match, original encounter, responsible doctor/clinic, missed/rescheduled state | check in follow-up, link visit, reschedule where permitted | follow-up clinical review belongs to Clinical Records | follow-up API, linked visit API, reschedule API, audit logging |
| Intake Audit Trail | Show trace of intake and routing actions | patient movement timeline, actor, role, source/target queue, reason, timestamp | view audit events, filter by patient/visit/action | read-only audit visibility; cannot edit audit records | immutable audit log API, filtering/export controls |

## 5. Navigation Behavior Principles

- Main workspace content should switch to the selected navigation item.
- GOPD users must not lose patient identity context while moving from lookup to visit creation to queue routing.
- Reassignment, referral, and escalation actions must be easy to find but governance-heavy enough to prevent accidental misuse.
- Patient lookup must happen before new registration where possible.
- Active visit detection must be visible before creating a new OPD visit.
- Follow-up arrivals must preserve original encounter linkage.

## 6. Explicit Exclusions

GOPD Intake navigation must not include operational ownership of:

- clinical notes
- diagnosis
- prescriptions
- clinical record signing
- lab result approval
- radiology report approval
- payment collection
- financial reconciliation
- pharmacy dispensing
- inpatient ward care
- CMD governance

If the user needs any excluded capability, the workspace must hand off to the responsible HIS domain.

## 7. Patient Movement Navigation Rule

The GOPD navigation architecture exists to correct and guide patient movement without fragmenting patient continuity.

```text
Correct the patient journey without fragmenting the patient record.
```

Every routing action must preserve:

- patient identity
- MRN
- visit ID
- source department
- target department
- previous queue state
- new queue state
- reason
- actor
- role
- timestamp

## 8. Demo Vs Production Boundary

This document defines navigation architecture before UI redesign.

Current implementation may only partially support these navigation items. Frontend demonstrations must clearly identify simulated routing/reassignment/referral behavior until backend APIs exist.

Production implementation requires backend state machine support, routing APIs, reassignment APIs, internal referral APIs, emergency escalation APIs, active visit detection, duplicate prevention, and immutable audit logging.

## 9. Governance Constraint

No engineer, designer, or AI agent may implement GOPD Intake navigation as an isolated patient system or disconnected department dashboard.

GOPD Intake must remain a department intake workspace inside unified KSH Enterprise HIS.

