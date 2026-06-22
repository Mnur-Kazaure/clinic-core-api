# SEALED CLINICAL RECORDS WORKSPACE SPEC

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

The Clinical Records Workspace defines the EMR / Clinical Records subdomain inside KSH Enterprise HIS.

It is the clinical documentation and care decision workspace for doctors and authorized clinical roles. It is not the entire HIS platform.

## 2. Architecture Foundation

```text
KSH Enterprise HIS = parent platform
EMR / Clinical Records = clinical subdomain
Doctor / Clinical Records = clinical documentation and care decision workspace
Reception = intake capability
```

Clinical Records must be documented and implemented as a clinical domain inside HIS, not as an independent product or umbrella system.

## 3. Clinical Records Workspace Owns

- doctor queue
- active consultations
- patient chart
- encounter notes
- diagnosis
- prescriptions
- lab orders
- radiology orders
- lab/radiology result review
- admission decisions
- follow-up decisions
- clinical history
- signed clinical records
- discharge summaries
- clinical audit trail

## 4. Clinical Records Must Not Own

- reception registration
- payment collection
- accountant reconciliation
- pharmacy inventory CRUD
- pharmacy dispensing execution
- lab sample processing
- laboratory result validation where assigned to lab professionals
- radiology image acquisition
- CMD governance actions
- platform administration
- user/role management unless separately authorized

## 5. Approved Workspace Sections

| Section | Purpose | Priority |
|---|---|---|
| Clinical Overview | Doctor workload, active encounters, pending results, and clinical alerts | Critical |
| My Patient Queue | Assigned patients awaiting consultation/review | Critical |
| OPD Consultations | Outpatient consultation workflow and encounter documentation | Critical |
| Follow-Up Consultations | Linked return visits and continuity review | High |
| Inpatient Reviews | Ward/admitted patient review workflow | High |
| Emergency Consultations | Urgent/A&E clinical review pathway | High |
| Patient Chart | Persistent chart shell and longitudinal clinical context | Critical |
| Clinical Notes | Encounter documentation, vitals, complaints, diagnosis, notes | Critical |
| Orders | Lab, radiology, pharmacy, and procedure orders where applicable | Critical |
| Results Review | Review and acknowledge diagnostic results | High |
| Prescriptions | Medication prescribing and pharmacy handoff | Critical |
| Admission Decisions | Admit request, clinical justification, and receiving ward context | High |
| Discharge Summaries | Discharge documentation and clinical summary | High |
| Clinical Audit Trail | Trace clinical access, edits, signatures, and handoffs | High |

## 6. Patient Chart Model

The patient chart must provide a persistent clinical context.

Approved patient chart structure:

| Chart Area | Required Content |
|---|---|
| Demographics Summary | name, MRN, age/date of birth, sex, phone where permitted |
| Encounter Timeline | prior visits, active visit, follow-up history, admissions |
| Active Visit | current status, department, queue state, responsible clinician |
| Diagnoses | working diagnosis, final diagnosis, problem list where supported |
| Medications | current prescriptions, medication history, active pharmacy handoffs |
| Investigations | lab/radiology orders, pending results, completed results |
| Prescriptions | issued prescriptions, status, pharmacy handoff |
| Clinical Notes | vitals, presenting complaints, diagnosis, notes, plan |
| Allergies / Alerts | allergies, high-risk clinical alerts where available |
| Signed Records | completed consultations, discharge summaries, locked records |

## 7. Clinical Encounter Governance

Approved encounter flow:

```text
Patient Selected
-> Clinical Context Loaded
-> Consultation Started
-> Notes / Diagnosis / Plan Captured
-> Orders / Prescriptions if required
-> Results Reviewed if required
-> Follow-Up / Admission / Discharge Decision
-> Clinical Record Signed / Completed
```

Completed clinical records must become read-only except through governed correction/addendum workflows.

## 8. Role Ownership

| Capability | Reception | Doctor / Clinical Records | Nursing / Ward | Lab | Radiology | Pharmacy | Cashier | Accountant | CMD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Register patient | Yes | No | No | No | No | No | No | No | Oversight only |
| Start consultation | No | Yes | No | No | No | No | No | No | Oversight only |
| Sign clinical note | No | Yes | No, unless authorized for nursing notes | No | No | No | No | No | Oversight only |
| Request lab/radiology | No | Yes | Limited where authorized | No | No | No | No | No | Oversight only |
| Validate lab result | No | Review only | No | Yes | No | No | No | No | Oversight only |
| Approve radiology report | No | Review only | No | No | Yes | No | No | No | Oversight only |
| Dispense medicine | No | No | No | No | No | Yes | No | No | Oversight only |
| Collect payment | No | No | No | No | No | No | Yes | No | Oversight only |
| Reconcile payment | No | No | No | No | No | No | No | Yes | Oversight only |

## 9. Audit Requirements

Clinical Records must audit:

- patient chart access
- purpose of use
- consultation start
- clinical note creation and updates
- vitals capture
- diagnosis capture
- prescription creation
- lab/radiology order creation
- results review
- admission decision
- discharge decision
- follow-up decision
- clinical record completion/signature
- correction/addendum events
- actor, role, timestamp, workstation, and visit/encounter ID

## 10. Demo Vs Production Boundary

This specification defines the target Clinical Records Workspace before UI redesign.

Current Doctor route behavior already includes some operational clinical workflows, but this document does not claim full implementation of the target architecture.

Production implementation requires:

- clinical encounter APIs
- immutable clinical audit logging
- patient chart aggregation APIs
- order lifecycle APIs
- prescription APIs
- result review APIs
- admission/discharge APIs
- follow-up APIs
- role-based clinical authorization
- signed-record locking and addendum governance

## 11. Governance Constraint

No engineer, designer, or AI agent may redesign the Doctor route as a generic doctor dashboard. It must evolve toward a governed Clinical Records Workspace inside KSH Enterprise HIS.

