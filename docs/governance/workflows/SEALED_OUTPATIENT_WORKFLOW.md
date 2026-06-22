# SEALED OUTPATIENT WORKFLOW

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

This document defines outpatient patient journey governance for KSH Enterprise HIS.

The outpatient workflow coordinates Reception, department routing, triage where required, doctor consultation, diagnostic orders, pharmacy, revenue collection, completion, and follow-up booking.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Reception = intake capability
Doctor / Clinical Records = clinical documentation and care decision workspace
```

Outpatient workflow belongs to HIS Clinical Operations. Clinical documentation belongs to EMR / Clinical Records inside HIS.

## 3. Approved Outpatient Flow

```text
Patient Arrival
-> Reception Lookup / Registration
-> OPD Visit Creation
-> Department / Clinic Routing
-> Triage where required
-> Doctor Queue
-> Consultation
-> Orders if required
   - Laboratory
   - Radiology
   - Pharmacy
-> Cashier / Revenue Collection where required
-> Completion
-> Follow-Up Booking if needed
```

## 4. Workflow Ownership

| Step | Primary Owner | Supporting Domain | Notes |
|---|---|---|---|
| Patient arrival | Reception | Department intake | Intake point may be centralized or department-specific |
| Lookup / registration | Reception | Patient registry governance | Must preserve patient identity controls |
| OPD visit creation | Reception | Department intake | Visit must carry department/clinic context |
| Department / clinic routing | Reception | GOPD, Specialist Clinics, A&E, Maternity, others | Routing must be auditable |
| Triage where required | Nursing / Triage | Reception, Doctor | Required for emergency/high-risk cases |
| Doctor queue | Clinical Records | Reception/Triage | Queue must preserve visit priority and state |
| Consultation | Doctor / Clinical Records | Nursing, diagnostics, pharmacy | Clinical documentation belongs to EMR / Clinical Records |
| Lab/radiology orders | Doctor / Clinical Records | Laboratory, Radiology | Service execution belongs to diagnostic domains |
| Pharmacy order/prescription | Doctor / Clinical Records | Pharmacy | Dispensing belongs to Pharmacy |
| Payment where required | Revenue Collection Desk | Billing, Accountant | Cashier collects and receipts only |
| Completion | Clinical Records / Reception depending on flow | Follow-up workflow | Completion must not destroy clinical trace |
| Follow-up booking | Doctor / Reception | Follow-up workflow | Must link to source encounter |

## 5. Suggested OPD Visit States

| State | Meaning |
|---|---|
| REGISTERED | Patient exists and has been registered |
| WAITING_TRIAGE | Visit is waiting for triage where required |
| TRIAGED | Triage has been completed |
| WAITING_CONSULTATION | Visit is ready for doctor/clinic queue |
| IN_CONSULTATION | Doctor consultation is active |
| LAB_REQUESTED | Laboratory order has been requested |
| RADIOLOGY_REQUESTED | Radiology order has been requested |
| PHARMACY_PENDING | Prescription/medicine workflow is pending pharmacy action |
| PAYMENT_PENDING | Payment is required before service completion or release |
| COMPLETED | OPD visit is completed |
| FOLLOW_UP_BOOKED | Follow-up has been scheduled and linked |
| CANCELLED | Visit was cancelled according to policy |

## 6. Approved State Transition Pattern

```text
REGISTERED
-> WAITING_TRIAGE
-> TRIAGED
-> WAITING_CONSULTATION
-> IN_CONSULTATION
-> LAB_REQUESTED / RADIOLOGY_REQUESTED / PHARMACY_PENDING / PAYMENT_PENDING
-> COMPLETED
-> FOLLOW_UP_BOOKED where required
```

Not every visit requires every state. Emergency, direct clinic, pharmacy-only, or diagnostic-linked workflows may follow approved variants, but all variants must preserve patient, visit, actor, department, timestamp, and state transition traceability.

## 7. Handoff Points

| Handoff | Source | Target | Required Governance |
|---|---|---|---|
| Reception to triage | Reception | Nursing/Triage | emergency flag, arrival time, department |
| Reception/triage to doctor queue | Reception/Triage | Clinical Records | visit state, priority, department |
| Doctor to lab | Clinical Records | Laboratory | order, diagnosis/context where required, requester |
| Doctor to radiology | Clinical Records | Radiology | order, indication, requester |
| Doctor to pharmacy | Clinical Records | Pharmacy | prescription, dosage, consultation linkage |
| Clinical to cashier | Clinical/Billing | Revenue Collection Desk | invoice/bill source and service line |
| Doctor to follow-up | Clinical Records | Follow-up workflow | reason, date, responsible clinic/doctor |

## 8. Audit Events

The following outpatient events must be auditable:

- patient lookup
- patient registration
- visit creation
- department routing
- triage state updates
- doctor queue assignment
- consultation start
- consultation save
- consultation completion/signing
- lab order request
- radiology order request
- prescription creation
- pharmacy handoff
- payment request/collection handoff
- visit completion
- follow-up booking
- cancellation and cancellation reason

## 9. What Must Not Happen

- Reception must not sign clinical records.
- Doctor must not perform cashier collection.
- Cashier must not create diagnosis, prescriptions, or clinical notes.
- Laboratory must not approve clinical diagnosis.
- Pharmacy must not alter signed prescriptions without governed clarification workflow.
- Accountant must not modify clinical visit states.
- CMD must not perform frontline clinical or cashier actions from executive oversight screens.
- No visit state transition may bypass audit logging in production.

## 10. Demo Vs Production Boundary

This document is a governance target. It does not claim that every outpatient workflow state is currently implemented.

Frontend demonstrations may show target workflow structure, but production requires:

- visit state machine enforcement
- role-based transition authorization
- audit logging
- patient identity controls
- order lifecycle APIs
- billing integration
- pharmacy/lab/radiology handoff APIs
- follow-up lifecycle APIs

## 11. Governance Constraint

No future redesign may treat outpatient care as independent dashboard cards. It must remain a patient journey with governed state transitions and traceable handoffs.

