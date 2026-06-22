# SEALED FOLLOW-UP WORKFLOW

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

This document defines follow-up / return visit governance for KSH Enterprise HIS.

Follow-up workflow preserves clinical continuity between encounters. It must link a returning patient to the original visit, follow-up reason, responsible clinician/clinic, scheduled date, missed/rescheduled status, and follow-up outcome.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Reception = follow-up check-in capability
Doctor / Clinical Records = follow-up clinical review workspace
```

Follow-up is a patient journey across Reception and Clinical Records. It is not a standalone disconnected dashboard.

## 3. Approved Follow-Up Flow

```text
Doctor Recommends Follow-Up
-> Follow-Up Appointment Created
-> Patient Returns
-> Reception Follow-Up Check-In
-> Follow-Up Queue
-> Doctor Reviews Previous Visit
-> Continue Treatment / Orders / Prescription
-> Complete Follow-Up
-> Book Next Follow-Up if needed
```

## 4. Follow-Up Ownership

| Step | Primary Owner | Supporting Domain |
|---|---|---|
| Follow-up recommendation | Doctor / Clinical Records | Patient chart |
| Appointment creation | Doctor / Clinical Records or Reception, according to policy | Appointment coordination |
| Patient return | Reception | Department intake |
| Follow-up check-in | Reception | Clinical Records |
| Follow-up queue | Clinical Records | Reception |
| Previous visit review | Doctor / Clinical Records | Patient chart |
| Continue treatment/orders | Doctor / Clinical Records | Lab, Radiology, Pharmacy |
| Rescheduling | Reception or Doctor according to policy | Audit trail |
| Missed follow-up review | Reception / Clinical Records | Department supervisor where required |
| Next follow-up booking | Doctor / Reception according to policy | Follow-up workflow |

## 5. Required Follow-Up Record

Every follow-up record must preserve:

- original visit linkage
- original encounter / consultation ID where available
- patient ID and MRN
- reason for follow-up
- responsible doctor
- responsible clinic/department
- scheduled date and time
- created by
- created timestamp
- check-in timestamp where patient returns
- missed status where applicable
- rescheduled status and reason where applicable
- follow-up outcome
- next follow-up recommendation where applicable

## 6. Suggested Follow-Up States

| State | Meaning |
|---|---|
| FOLLOW_UP_RECOMMENDED | Doctor has recommended follow-up |
| FOLLOW_UP_BOOKED | Follow-up appointment exists |
| DUE_TODAY | Follow-up is due today |
| CHECKED_IN | Patient has returned and checked in |
| WAITING_FOLLOW_UP_CONSULTATION | Patient is waiting for follow-up review |
| IN_FOLLOW_UP_CONSULTATION | Doctor is reviewing follow-up encounter |
| FOLLOW_UP_COMPLETED | Follow-up encounter is complete |
| RESCHEDULED | Follow-up was rescheduled with reason |
| MISSED | Patient missed scheduled follow-up |
| CANCELLED | Follow-up was cancelled according to policy |

## 7. Clinical Continuity Requirements

Doctor follow-up review must surface:

- original encounter summary
- previous diagnosis
- previous treatment plan
- medication/prescription history
- prior lab/radiology orders and results
- reason for follow-up
- current symptoms / updates
- outcome of follow-up review
- next plan

Follow-up visits must not be treated as unrelated new visits when a linkage exists.

## 8. Handoff Points

| Handoff | Source | Target | Required Trace |
|---|---|---|---|
| Doctor to follow-up booking | Clinical Records | Follow-up workflow | reason, date, responsible clinic |
| Follow-up due list to reception | Follow-up workflow | Reception | patient, due date, department |
| Reception check-in to doctor queue | Reception | Clinical Records | original visit link, check-in time |
| Doctor follow-up review to orders | Clinical Records | Lab/Radiology/Pharmacy | order and source encounter |
| Follow-up completion to next booking | Clinical Records | Follow-up workflow / Reception | outcome and next plan |

## 9. Missed And Rescheduled Follow-Up Governance

Missed follow-ups must preserve:

- scheduled date
- missed status
- responsible clinic/doctor
- last contact attempt where supported
- reschedule history where applicable

Rescheduled follow-ups must preserve:

- original date
- new date
- actor
- role
- reason
- timestamp
- patient/department context

## 10. Audit Requirements

Follow-up workflow must audit:

- recommendation creation
- booking creation
- check-in
- reschedule
- missed follow-up marking
- linked visit creation
- follow-up consultation start
- follow-up consultation completion
- next follow-up booking
- cancellation and reason
- actor, role, timestamp, workstation, patient, visit, and original encounter link

## 11. What Must Not Happen

- Follow-up must not lose its original encounter linkage.
- Reception must not alter clinical follow-up reason without authorization.
- Doctor must not rely on a follow-up visit without access to previous clinical context.
- Follow-up rescheduling must not overwrite original date without audit trail.
- Missed follow-ups must not be silently deleted.
- Cashier/Accountant must not alter clinical follow-up state.
- CMD must not perform frontline follow-up actions from oversight dashboards.

## 12. Demo Vs Production Boundary

This document defines governance targets before UI redesign.

Current implementation may support only part of this model. Production implementation requires:

- follow-up lifecycle APIs
- original encounter linkage
- patient recall APIs
- check-in APIs
- follow-up queue APIs
- rescheduling APIs
- missed follow-up controls
- audit logging
- role-based authorization

## 13. Governance Constraint

No future redesign may treat follow-up as a simple appointment list only. Follow-up is a clinical continuity workflow and must preserve encounter linkage, patient journey context, and audit traceability.

