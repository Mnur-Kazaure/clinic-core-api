# SEALED CLINICAL RECORDS UI ARCHITECTURE

Version: v1.0
Status: Sealed UI/UX architecture target before frontend implementation
Audience: architects, engineers, designers, clinical operations reviewers, auditors, and AI agents

## 1. Purpose

This document defines enterprise EMR / Clinical Records workspace UI architecture for KSH Enterprise HIS.

This is not an implementation plan and not a React component specification. It governs how the future Clinical Records interface should preserve patient context, encounter continuity, clinical safety, and workflow speed before frontend redesign begins.

The Clinical Records Workspace is a persistent clinical workspace, longitudinal patient continuity system, and encounter-centered clinical workstation.

## 2. Workspace Identity

Approved names:

- Clinical Records Workspace
- Clinical Care Workspace
- EMR / Clinical Records

Rejected names:

- Doctor Dashboard
- Consultation Page
- Doctor Portal
- Generic EMR Page

The name must communicate clinical documentation and care decision ownership inside the HIS, not a standalone EMR platform.

## 3. Workspace Philosophy

The Clinical Records Workspace must prioritize:

- persistent patient context
- encounter-centered workflow
- longitudinal continuity
- clinical safety
- minimal context loss
- rapid doctor navigation
- low cognitive interruption
- patient-first continuity
- signed-record integrity
- cross-domain handoff visibility

The workspace must reduce clinical context switching and avoid making doctors repeatedly reopen the same patient context from disconnected modals.

## 4. Clinical Workspace Shell

### Left Sidebar

The left sidebar should provide:

- consultation navigation
- clinical sections
- queue switching
- review workflows
- patient chart access
- orders/results/prescriptions access
- admission/discharge access
- clinical audit access

Approved navigation:

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

### Top Patient Context Header

The top patient context header is the permanent clinical anchor once a patient or encounter is selected.

It should show:

- patient identity
- MRN
- age / sex
- active encounter
- active visit
- department
- priority
- allergies/alerts
- admission state
- follow-up state
- emergency flag where applicable

It must remain visible while the doctor moves between notes, orders, results, prescriptions, admission, discharge, and follow-up.

### Center Workspace

The center workspace renders the selected clinical function:

- notes
- orders
- results
- prescriptions
- chart review
- OPD consultation
- follow-up review
- inpatient review
- emergency consultation
- admission flow
- discharge summary flow

The center workspace should not force every task into modal windows. Persistent workspace layouts are preferred for primary clinical work.

### Right Clinical Context Rail

The right context rail should preserve longitudinal clinical context:

- encounter timeline
- previous visits
- admissions
- orders
- prescriptions
- follow-up history
- investigation history
- signed records
- active alerts

The rail should help the doctor understand where the current encounter sits in the patient's history.

## 5. Persistent Clinical Context Principle

Doctor must never lose:

- patient identity
- active encounter
- longitudinal context

while switching between:

- notes
- results
- orders
- prescriptions
- admission
- discharge
- follow-up

The clinical shell must preserve:

- selected patient
- selected encounter
- active visit state
- department context
- priority/emergency state
- current workflow state

## 6. Visual Design Direction

The Clinical Records Workspace should feel:

- clinically focused
- calm
- intelligent
- safe
- structured
- high-trust
- operationally dense
- medically professional
- fast to scan

Use:

- clinical white/slate surfaces
- calm blue and teal accents
- restrained urgent colors
- strong patient identity hierarchy
- compact clinical rows
- readable forms
- clear signed/draft state separation
- persistent context framing

Avoid:

- excessive cinematic effects
- generic dashboard cards
- excessive modal interruptions
- financial dashboard aesthetics
- marketing-style hero sections
- decorative surfaces that compete with patient data

## 7. Clinical Documentation UX

### Note-Writing Posture

Clinical notes should support structured, fast documentation:

- vitals
- presenting complaint
- history
- examination
- diagnosis
- plan
- follow-up decision
- admission/discharge decision where applicable

Draft and signed states must be visually distinct.

### Results Review Flow

Results review should show:

- source order
- result status
- abnormal flags
- collection/result time
- reviewing doctor
- acknowledgement/review state
- link back to encounter

### Prescription Flow

Prescription workflow should show:

- medication
- dose
- route
- frequency
- duration
- instructions
- pharmacy handoff status
- allergy/alert visibility where available

### Order Workflow

Orders should show:

- order type
- indication
- priority
- target department
- status
- requester
- linked encounter

### Discharge Flow

Discharge summary UX should preserve:

- admission context
- diagnosis
- hospital course
- treatment
- discharge medications
- discharge instructions
- follow-up plan
- signed summary state

### Follow-Up Workflow

Follow-up UX should show:

- original encounter
- follow-up reason
- due date
- missed/rescheduled state
- current review outcome
- next follow-up plan

## 8. Patient Chart UX

The patient chart should provide:

- longitudinal timeline
- encounter grouping
- active encounter prominence
- signed-record distinction
- investigation visibility
- medication visibility
- prescription status
- admission/discharge history
- follow-up history

The active encounter must be visually prominent and separate from historical records.

Signed records must be visually distinct from editable drafts and must not appear casually editable.

## 9. Clinical Safety UX

The Clinical Records Workspace must support safety visibility for:

- allergy visibility
- urgent flags
- emergency state
- abnormal result visibility
- duplicate order prevention posture
- context-loss prevention
- active admission state
- active follow-up linkage

Critical warnings must not depend on color alone. Text labels and structured warning hierarchy are required.

## 10. Modal Governance

Modals must not become the primary clinical workflow.

Approved modal uses:

- short confirmations
- focused detail previews
- controlled secondary actions
- safety acknowledgements
- contextual quick view where it does not interrupt active encounter continuity

Avoid:

- full consultation workflow primarily in modal
- lab order workflow only in modal when a persistent order workspace is needed
- prescription workflow disconnected from patient context
- clinical note editing detached from patient chart
- modals that hide active encounter identity

Persistent workspace layouts are preferred for core clinical work.

## 11. Enterprise Clinical Feel

The Clinical Records Workspace should be inspired by enterprise EMR continuity patterns such as:

- persistent chart shell
- encounter timeline
- clinical task rail
- structured documentation
- high-speed clinical review
- safety flags
- signed-record integrity

It must not visually clone any vendor.

The target is a modern, hospital-grade Clinical Records Workspace that feels coherent, safe, and operationally powerful inside KSH Enterprise HIS.

## 12. Mobile / Compressed Strategy

Clinical work is desktop-first and laptop-optimized.

Responsive behavior should preserve:

- patient identity
- active encounter
- emergency/allergy alerts
- active clinical task
- key longitudinal context

On smaller screens:

- sidebar may collapse
- right context rail may stack or become a drawer
- patient context header must remain readable
- primary clinical content must remain usable
- critical warnings must remain visible

## 13. Demo Vs Production Boundary

This document defines UI/UX architecture before frontend implementation.

Frontend demonstrations may simulate patient chart shells, encounter rails, notes, orders, results, prescriptions, admission, discharge, and follow-up views, but must not imply production backend behavior exists until APIs, clinical authorization, signed-record locking, and immutable audit logging are implemented.

## 14. Governance Constraint

No engineer, designer, or AI agent may implement the Clinical Records Workspace as a generic doctor dashboard, modal-heavy consultation page, or disconnected form collection.

The Clinical Records Workspace must preserve persistent clinical context, encounter continuity, and patient-first longitudinal history inside KSH Enterprise HIS.

