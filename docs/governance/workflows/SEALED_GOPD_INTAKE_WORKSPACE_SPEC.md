# SEALED GOPD INTAKE WORKSPACE SPEC

Version: v1.0
Status: Sealed governance target before UI redesign
Audience: architects, engineers, designers, auditors, clinical operations reviewers, and AI agents

## 1. Purpose

The GOPD Intake Workspace is the first department-specific intake workspace pattern for KSH Enterprise HIS.

GOPD supports high-volume outpatient arrival, patient lookup, patient registration, OPD visit creation, queue routing, triage routing where required, doctor assignment, wrong-department reassignment, internal referral initiation, emergency escalation, and follow-up arrival handling.

This specification exists before UI redesign so the future Reception modernization does not collapse into generic dashboard redesign or fragmented department systems.

## 2. Architecture Principle

Reception is distributed operationally but unified architecturally.

GOPD Intake is not an independent patient system. It operates inside KSH Enterprise HIS and uses:

- shared patient identity
- shared MRN
- shared EMR / Clinical Records
- shared visit history
- shared billing
- shared audit trail
- shared longitudinal patient history

```text
KSH Enterprise HIS
-> Clinical Operations
-> Reception Intake Architecture
-> GOPD Intake Workspace
```

GOPD owns high-volume outpatient intake and routing. It does not own the patient's full clinical record independently.

## 3. GOPD Intake Owns

- high-volume outpatient arrival handling
- patient lookup for GOPD arrival
- registration initiation where patient does not exist
- OPD visit creation
- GOPD queue initiation
- triage routing where required
- doctor assignment / queue routing
- wrong-department correction before consultation
- internal referral initiation where policy permits
- emergency escalation to A&E
- follow-up arrival identification and routing
- intake audit traceability

## 4. GOPD Must Not Own

- diagnosis
- prescriptions
- clinical notes
- lab result approval
- radiology report approval
- payment collection
- financial reconciliation
- pharmacy dispensing
- inpatient ward care
- discharge decisions
- CMD governance
- platform administration
- user/role management

## 5. Approved GOPD Intake Sections

| Section | Purpose | Priority |
|---|---|---|
| GOPD Intake Overview | Current GOPD arrival load, queue posture, waiting patients, triage pressure, and routing exceptions | Critical |
| Patient Lookup | Search existing patients by MRN, name, phone, visit context, or other approved identifiers | Critical |
| Patient Registration | Register new patients when lookup confirms no existing record | Critical |
| Start OPD Visit | Create OPD visit and attach GOPD department context | Critical |
| GOPD Queue | Manage patients waiting for GOPD routing, triage, or doctor queue | Critical |
| Triage Routing | Route patients to triage where risk, policy, or presentation requires triage | High |
| Doctor Assignment | Assign or route patient to appropriate GOPD doctor/clinic queue | High |
| Reassignment / Rerouting | Correct wrong queue or wrong department before consultation where appropriate | High |
| Internal Referral | Initiate governed routing to specialist department/clinic where indicated | High |
| Emergency Escalation | Move urgent cases from GOPD to A&E with emergency traceability | Critical |
| Follow-Up Arrival | Identify returning patients and link arrival to existing follow-up workflow | High |
| Intake Audit Trail | Trace intake, routing, reassignment, referral, and escalation events | High |

## 6. Patient Movement Model

Approved GOPD patient movement model:

```text
Patient Arrival
-> Lookup / Registration
-> OPD Visit Creation
-> GOPD Queue
-> Triage if needed
-> Doctor Queue
-> Consultation
-> Orders / Payment / Pharmacy / Follow-Up
```

The patient identity, MRN, EMR / Clinical Records, and visit history remain unified even when patient movement changes department, queue, or clinical ownership.

## 7. Reassignment / Rerouting Model

GOPD Intake must support real-world patient movement without forcing duplicate registration.

### Operational Reassignment

Operational Reassignment corrects wrong queue or wrong department placement before clinical consultation.

Examples:

- patient arrived at GOPD but should be in Maternity intake
- patient was routed to wrong doctor queue
- patient was placed in a general queue but should be in Specialist Clinics
- duplicate active visit is discovered before consultation

Operational Reassignment must preserve the original visit trace and routing reason.

### Internal Referral

Internal Referral is clinical or clinically guided routing from GOPD to another department or specialty.

Examples:

- GOPD to Specialist Clinics
- GOPD to Gynecology
- GOPD to Pediatrics
- GOPD to Maternity
- GOPD to Theatre review pathway where applicable

Internal Referral should generally occur after a clinical or triage decision, depending on hospital policy.

### Emergency Escalation

Emergency Escalation moves a patient from GOPD to A&E due to urgent or deteriorating condition.

Examples:

- severe respiratory distress identified at intake
- collapsed patient at GOPD front desk
- high-risk vital signs discovered during triage
- urgent trauma presentation discovered after arrival

Emergency Escalation must mark the patient movement as urgent and preserve source GOPD context.

### Admission Conversion

Admission Conversion converts an outpatient patient into an inpatient admission pathway after doctor decision.

Examples:

- GOPD consultation determines admission is required
- outpatient review identifies need for ward monitoring
- emergency escalation later results in admission

Admission Conversion belongs to Doctor / Clinical Records and Inpatient & Ward Management, not GOPD intake alone.

## 8. State Model

Suggested GOPD intake states:

| State | Meaning |
|---|---|
| ARRIVED | Patient has arrived at GOPD intake point |
| LOOKUP_IN_PROGRESS | Existing patient lookup is in progress |
| REGISTERED | Patient is registered or confirmed in the patient registry |
| OPD_VISIT_CREATED | OPD visit has been created |
| GOPD_QUEUE | Patient is waiting in GOPD intake/consultation pathway |
| WAITING_TRIAGE | Patient is waiting for triage |
| TRIAGED | Triage has been completed |
| WAITING_DOCTOR | Patient is waiting for doctor/clinical review |
| IN_CONSULTATION | Doctor consultation has started |
| REASSIGNED | Patient has been operationally reassigned/rerouted |
| REFERRED_INTERNALLY | Patient has been referred to another department/specialty |
| ESCALATED_TO_AE | Patient has been escalated to Accident & Emergency |
| ADMISSION_REQUESTED | Admission request has been initiated by clinical decision |
| COMPLETED | GOPD visit is completed |
| FOLLOW_UP_BOOKED | Follow-up has been scheduled and linked |
| CANCELLED | Visit or routing was cancelled according to policy |

## 9. Role Ownership Table

| Capability / Movement | GOPD Reception / Intake | Triage / Nursing | Doctor / Clinical Records | A&E Intake | Specialist Clinic Reception | Revenue Collection Desk | Pharmacy | Laboratory | Radiology | CMD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Patient lookup | Owns | View where authorized | View where authorized | View where authorized | View where authorized | No | No | No | No | Oversight only |
| Patient registration | Owns | No | No | Limited emergency support where authorized | No | No | No | No | No | Oversight only |
| OPD visit creation | Owns | Support | No | No | No | No | No | No | No | Oversight only |
| GOPD queue routing | Owns | Support | Receives queue | No | No | No | No | No | No | Oversight only |
| Triage routing | Initiates | Owns triage execution | Receives triage outcome | Support for escalation | No | No | No | No | No | Oversight only |
| Doctor assignment | Initiates/routs | Support | Owns clinical review | No | No | No | No | No | No | Oversight only |
| Operational reassignment | Owns before consultation | Support | Must not lose context | Receives if A&E target | Receives if specialist target | No | No | No | No | Oversight only |
| Internal referral | Initiates where policy permits | May recommend | Owns clinical referral decision | Receives when A&E target | Receives specialist intake | No | No | No | No | Oversight only |
| Emergency escalation | Initiates urgent movement | Supports/executes triage escalation | Receives/continues clinical context | Owns emergency intake after transfer | No | No | No | No | No | Oversight only |
| Admission conversion | No | Support | Owns decision | Support if emergency | No | Billing handoff only | Support medication supply | Support investigations | Support investigations | Oversight only |
| Payment collection | No | No | No | No | No | Owns collection | No | No | No | Oversight only |
| Pharmacy dispensing | No | No | No | No | No | No | Owns | No | No | Oversight only |
| Diagnostic execution | No | No | Orders only | No | No | No | No | Owns lab execution | Owns imaging execution | Oversight only |

## 10. Audit Requirements

Every GOPD intake action must preserve:

- patient identity
- MRN where available
- visit ID
- source department
- target department where movement occurs
- source queue state
- target queue state
- reason for movement
- actor identity
- actor role
- workstation / intake point
- timestamp
- purpose of use
- emergency flag where applicable
- follow-up linkage where applicable

Every reassignment, referral, escalation, and admission conversion must preserve:

- patient
- MRN
- visit ID
- source department
- target department
- reason
- actor
- role
- timestamp
- previous queue state
- new queue state

## 11. Second-Nature Adoption Strategy

The GOPD Intake Workspace must make common real-world corrections easy while preserving governance.

The system should guide users through:

- wrong department correction
- wrong queue correction
- patient needs specialist care
- urgent condition discovered
- follow-up patient arrived at GOPD
- patient already has an active visit
- patient arrived without complete details
- patient requires triage before doctor queue

The system must not force duplicate registration when an existing patient or active visit is found.

The intended adoption principle:

```text
Correct the patient journey without fragmenting the patient record.
```

## 12. Demo Vs Production Boundary

This specification is a governance target before GOPD Intake UI redesign.

Current Reception implementation may only partially support this model.

Future production implementation requires:

- backend state machine for intake and patient movement
- routing APIs
- reassignment APIs
- internal referral APIs
- emergency escalation APIs
- admission conversion integration
- active visit detection
- duplicate prevention
- immutable audit logging
- role-based authorization
- department queue APIs
- patient identity controls

Frontend demonstrations must clearly identify any simulated state or movement behavior until backend support exists.

## 13. Governance Constraint

No engineer, designer, or AI agent may implement GOPD Intake as isolated patient records, a separate patient system, or an independent department database.

GOPD Intake must remain a department intake workspace inside unified KSH Enterprise HIS with shared patient identity, shared EMR / Clinical Records, shared visit history, shared billing, and shared audit trail.

