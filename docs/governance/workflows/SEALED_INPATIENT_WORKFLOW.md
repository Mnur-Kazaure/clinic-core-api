# SEALED INPATIENT WORKFLOW

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

This document defines inpatient admission and ward workflow governance for KSH Enterprise HIS.

The inpatient workflow governs admission decisions, bed/ward allocation, ward care, doctor review, nursing care, orders, medication administration support, discharge decisions, billing clearance, discharge summaries, and final discharge.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Inpatient & Ward Management = HIS clinical operations domain
Doctor / Clinical Records = clinical decision and documentation workspace
Nursing / Ward = ward care execution workspace
```

## 3. Approved Inpatient Flow

```text
Admission Decision
-> Admission Request
-> Bed / Ward Allocation
-> Patient Admitted
-> Nursing Intake
-> Ward Review
-> Medication / Orders
-> Lab/Radiology Requests if required
-> Pharmacy Supply / Medication Administration
-> Ongoing Ward Monitoring
-> Discharge Decision
-> Discharge Billing Clearance
-> Discharge Summary
-> Discharged
```

## 4. Workflow Owners

| Workflow Area | Primary Owner | Supporting Roles |
|---|---|---|
| Admission decision | Doctor / Clinical Records | Reception/Admin where applicable |
| Admission request | Doctor / Clinical Records | Ward/Nursing, Admin |
| Bed / ward allocation | Ward/Nursing or Admission Admin | Doctor, Reception/Admin |
| Patient admitted state | Ward/Nursing | Doctor / Clinical Records |
| Nursing intake | Nursing / Ward | Doctor |
| Ward review | Doctor / Clinical Records | Nursing / Ward |
| Medication / clinical orders | Doctor / Clinical Records | Nursing, Pharmacy |
| Lab/radiology requests | Doctor / Clinical Records | Laboratory, Radiology |
| Medication administration support | Nursing / Ward | Pharmacy, Doctor |
| Ongoing monitoring | Nursing / Ward | Doctor |
| Discharge decision | Doctor / Clinical Records | Nursing |
| Billing clearance | Revenue Collection Desk / Accountant | Reception/Admin, Ward |
| Discharge summary | Doctor / Clinical Records | Nursing where required |
| CMD oversight | CMD | Receives visibility only for escalations and posture |

## 5. Suggested Inpatient States

| State | Meaning |
|---|---|
| ADMISSION_REQUESTED | Doctor has requested admission |
| BED_PENDING | Patient is awaiting bed/ward allocation |
| ADMITTED | Patient is formally admitted |
| UNDER_WARD_CARE | Patient is under active ward care |
| DOCTOR_REVIEW_REQUIRED | Patient requires doctor review |
| INVESTIGATION_REQUESTED | Lab/radiology investigation has been requested |
| DISCHARGE_DECIDED | Doctor has made discharge decision |
| BILLING_CLEARANCE_PENDING | Discharge is waiting for billing/financial clearance |
| DISCHARGE_SUMMARY_PENDING | Clinical discharge summary is pending |
| DISCHARGED | Patient has been discharged |

## 6. State Transition Governance

```text
ADMISSION_REQUESTED
-> BED_PENDING
-> ADMITTED
-> UNDER_WARD_CARE
-> DOCTOR_REVIEW_REQUIRED where needed
-> INVESTIGATION_REQUESTED where needed
-> DISCHARGE_DECIDED
-> BILLING_CLEARANCE_PENDING
-> DISCHARGE_SUMMARY_PENDING
-> DISCHARGED
```

The order may vary by emergency and operational context, but production implementation must preserve state traceability and authorization.

## 7. Handoff Points

| Handoff | Source | Target | Required Trace |
|---|---|---|---|
| Consultation to admission request | Doctor | Admission/Ward | diagnosis/context, reason, doctor, timestamp |
| Admission request to bed allocation | Doctor/Admin | Ward/Nursing | bed request, ward, priority |
| Bed allocation to admitted care | Ward/Admin | Nursing/Ward | bed, ward, admission time |
| Ward care to doctor review | Nursing/Ward | Doctor | reason, vitals/notes, priority |
| Doctor to diagnostics | Doctor | Laboratory/Radiology | order, indication, visit/admission ID |
| Doctor/Nursing to pharmacy | Doctor/Nursing | Pharmacy | prescription/order, inpatient context |
| Discharge decision to billing clearance | Doctor/Ward | Revenue Collection Desk / Accountant | discharge decision, patient account |
| Clearance to discharge summary | Finance/Ward | Doctor | clearance state, outstanding exceptions |
| Summary to final discharge | Doctor/Ward | Patient discharge process | summary, discharge time, instructions |

## 8. Clinical And Operational Audit Requirements

Inpatient workflow must audit:

- admission decision
- admission request
- bed/ward allocation
- nursing intake
- ward transfer where applicable
- doctor ward review
- nursing notes
- medication administration support
- investigation requests
- pharmacy supply/dispensing handoff
- discharge decision
- billing clearance status
- discharge summary completion
- final discharge
- actor, role, timestamp, workstation, ward, bed, patient, and admission ID

## 9. What Must Not Happen

- Reception must not make clinical admission decisions.
- Cashier must not discharge a patient clinically.
- Accountant must not alter clinical admission/discharge notes.
- Nursing must not sign doctor discharge summaries unless separately authorized by policy.
- Doctor must not bypass billing clearance where discharge policy requires financial clearance.
- CMD must not perform frontline ward actions from oversight dashboards.
- Discharge must not destroy or overwrite admission history.

## 10. Demo Vs Production Boundary

This document is a governance target and does not claim full inpatient implementation.

Production implementation requires:

- admission APIs
- bed/ward allocation APIs
- ward care APIs
- nursing note APIs
- medication administration APIs
- inpatient order lifecycle APIs
- billing clearance integration
- discharge summary APIs
- immutable inpatient audit logging
- role-based authorization

## 11. Governance Constraint

No future redesign may treat inpatient care as a generic dashboard card. It must be modeled as a governed patient journey with ward ownership, clinical documentation, operational handoffs, and discharge integrity.

