# SEALED RECEPTION INTAKE WORKSPACE SPEC

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

The Reception Intake Workspace is the enterprise patient intake and visit initiation workspace inside KSH Enterprise HIS.

Reception is an intake capability, not the whole clinical workflow. It initiates patient movement into the HIS and coordinates routing to the correct department, queue, or follow-up pathway.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Reception = intake capability
Doctor / Clinical Records = clinical documentation and care decision workspace
```

Reception must not be described as an EMR platform. Reception operates inside HIS Clinical Operations.

## 3. Reception Owns

- patient registration
- patient lookup
- visit creation
- OPD intake
- emergency intake
- follow-up check-in
- department intake routing
- queue initiation
- appointment and follow-up coordination
- patient registry review for operational intake purposes
- intake audit traceability

## 4. Reception Must Not Own

- clinical consultation
- diagnosis
- prescriptions
- lab result approval
- radiology report approval
- pharmacy dispensing
- payment collection
- financial reconciliation
- clinical record signing
- inpatient clinical care decisions
- CMD governance decisions
- platform administration unless separately authorized

## 5. Approved Workspace Sections

| Section | Purpose | Priority |
|---|---|---|
| Intake Overview | Current intake posture, queue pressure, emergency flags, and follow-up arrivals | Critical |
| Patient Registration | Register new patients and issue patient identifiers according to HIS policy | Critical |
| Patient Lookup | Search existing patients by MRN, name, phone, visit, or invoice context where permitted | Critical |
| Start Visit | Create a visit and route it to department/clinic queue | Critical |
| OPD Intake Queue | Manage outpatient arrivals and routing to consultation or triage | Critical |
| Emergency Intake | Fast intake path for A&E and urgent cases | Critical |
| Follow-Up Check-In | Check returning patients into linked follow-up workflows | High |
| Appointment Coordination | Schedule, reschedule, and coordinate appointment arrival where supported | High |
| Department Intake | Govern department-specific intake such as GOPD, A&E, Specialist Clinics, and Maternity | High |
| Patient Registry | Operational patient registry review for intake and visit creation | High |
| Intake Audit Trail | Trace intake actions, actor, timestamp, and purpose of use | High |

## 6. Department Reception Principle

Each major department may operate an intake capability.

Approved examples:

- GOPD Reception
- A&E Intake
- Specialist Clinic Reception
- Maternity Reception
- Pediatrics Intake
- Gynecology Intake
- Radiology Booking / Intake
- Laboratory Sample Reception

Department reception must remain governed under the parent department workspace where applicable. It must not become disconnected dashboard sprawl.

## 7. Intake Workflow Model

```text
Patient Arrival
-> Patient Lookup / Registration
-> Visit Creation
-> Department / Clinic Routing
-> Queue Initiation
-> Triage if required
-> Doctor / Service Queue
```

Follow-up intake follows:

```text
Patient Returns
-> Follow-Up Lookup
-> Follow-Up Check-In
-> Linked Visit Creation
-> Follow-Up Queue
-> Doctor / Clinic Review
```

Emergency intake follows:

```text
Emergency Arrival
-> Emergency Registration / Minimum Data Capture
-> Emergency Flag
-> A&E Queue / Triage
-> Doctor / Emergency Care Team
```

## 8. Role Ownership

| Workflow Area | Primary Owner | Supporting Roles | Must Not Own |
|---|---|---|---|
| Patient registration | Reception | Admin for configuration | Doctor, Cashier, CMD |
| Visit creation | Reception | Department intake staff | Accountant, CMD |
| OPD queue initiation | Reception | Triage/Nursing where required | Accountant, Pharmacy |
| Emergency intake | A&E Intake / Reception | Triage/Nursing, Doctor | Accountant, CMD |
| Follow-up check-in | Reception | Doctor / Clinical Records | Cashier, Accountant |
| Patient registry lookup | Reception | Admin audit controls | Unauthorized roles |
| Clinical documentation | Doctor / Clinical Records | Nursing where applicable | Reception |

## 9. State Model

Recommended intake states:

| State | Meaning |
|---|---|
| PATIENT_LOOKUP | Existing patient search is in progress |
| REGISTRATION_IN_PROGRESS | New patient registration is being captured |
| REGISTERED | Patient is registered and available for visit creation |
| VISIT_CREATED | Visit exists and is awaiting department routing |
| ROUTED_TO_DEPARTMENT | Visit has department or clinic routing context |
| WAITING_TRIAGE | Visit is waiting for triage where required |
| TRIAGED | Triage has been completed |
| WAITING_CONSULTATION | Patient is in doctor/clinic queue |
| EMERGENCY_FLAGGED | Visit is marked urgent/emergency |
| FOLLOW_UP_CHECKED_IN | Follow-up patient has arrived and is linked to prior encounter |
| CANCELLED | Intake/visit workflow was cancelled according to policy |

## 10. Handoff Points

| Handoff | Source | Target | Required Trace |
|---|---|---|---|
| Registration to visit | Reception | Visit workflow | patient, actor, timestamp, department context |
| Visit to triage | Reception | Triage/Nursing | visit ID, emergency flag, department |
| Visit to doctor queue | Reception/Triage | Doctor / Clinical Records | visit state, assigned department, priority |
| Follow-up check-in to doctor | Reception | Clinical Records | original encounter link, reason, due date |
| Emergency intake to A&E | Reception / A&E Intake | A&E clinical team | emergency flag, intake time, minimum patient identity |

## 11. Audit Requirements

Every intake event must preserve:

- patient ID and MRN where available
- visit ID where created
- actor identity
- role
- workstation or intake point
- department context
- timestamp
- purpose of use
- routing decision
- emergency flag where applicable
- follow-up linkage where applicable
- cancellation or reschedule reason where applicable

## 12. Demo Vs Production Boundary

This specification defines governance targets before Reception UI redesign.

Current frontend and backend behavior may implement only part of this target model. Any future implementation must clearly distinguish:

- current implemented behavior
- frontend demonstration behavior
- production backend/API-backed behavior

Production implementation requires durable audit logging, role authorization, visit state validation, patient identity controls, and governed handoffs to clinical, diagnostic, pharmacy, and revenue workflows.

## 13. Governance Constraint

No engineer, designer, or AI agent may redesign Reception as a generic dashboard. Reception must remain a governed HIS intake workspace with clear patient-flow ownership and controlled handoffs.

