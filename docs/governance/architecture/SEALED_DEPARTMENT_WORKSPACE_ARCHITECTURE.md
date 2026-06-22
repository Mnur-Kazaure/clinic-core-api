# SEALED DEPARTMENT WORKSPACE ARCHITECTURE

Version: v1.0
Status: Sealed architecture decision
Audience: architects, engineers, designers, auditors, product reviewers, and AI agents

## 1. Purpose

This document defines the approved Department Workspace Architecture for KSH Enterprise HIS.

The purpose is to prevent dashboard fragmentation, preserve enterprise operational ownership, and ensure that future department and unit workspaces remain aligned with the unified Hospital Information System architecture.

## 2. Architecture Decision

KSH Enterprise HIS uses a Department Workspace Architecture.

```text
Department = primary operational ownership
Unit = focused operational sub-workspace inside department
```

This is a sealed architecture decision.

Department workspaces are the primary operational surfaces. Unit workspaces must exist as governed sub-workspaces inside their parent department unless enterprise complexity requires formally approved independent operational separation.

## 3. What This Prevents

The Department Workspace Architecture explicitly prevents:

- isolated dashboard sprawl
- disconnected unit dashboards
- random workstation duplication
- inconsistent navigation models
- department/unit ownership confusion
- clinical, diagnostic, pharmacy, and ward workflow fragmentation

## 4. HIS Parent Architecture Alignment

KSH Enterprise HIS remains the unified enterprise hospital platform.

```text
KSH Enterprise HIS
|-- Executive Governance
|-- Revenue & Financial Governance
|-- Clinical Operations
|-- Diagnostic Services
|-- Pharmacy & Supply
|-- Workforce Governance
`-- Administration & Compliance
```

EMR / Clinical Records remains a clinical subdomain inside HIS. EMR must not be treated as the umbrella platform.

## 5. Approved Department Grouping

### Clinical Operations

- Reception
- Doctor / Clinical Records
- Nursing / Ward
- General Outpatient Department (GOPD)
- Accident & Emergency (A&E)
- Specialist Clinics
- Maternity
- Pediatrics
- Gynecology
- Male Ward
- Female Ward
- Theatre

### Diagnostic Services

- Laboratory
- Radiology

### Pharmacy & Supply

- Pharmacy Workspace
- Dispensing Units
- Supply Requests
- Inventory Governance

### Revenue & Financial Governance

- Revenue Collection Desk
- Accountant Financial Control Center
- Billing & Revenue Cycle
- Revenue Intelligence

### Executive Governance

- CMD Command Center
- Operational Intelligence
- Audit Oversight
- Workforce Oversight

### Workforce Governance

- Attendance Intelligence
- Biometric Monitoring
- Shift Compliance
- Workforce Analytics
- Department Staffing Posture

### Administration & Compliance

- User Management
- RBAC
- System Settings
- Compliance Controls

## 6. Department Workspace Principle

Department dashboards are the primary operational workspaces.

Units must exist as governed operational sub-workspaces inside department workspaces unless enterprise complexity requires independent operational separation.

Approved pattern:

```text
Department Workspace
|-- Department-level queue / dashboard
|-- Unit sub-workspace
|-- Department-specific workflow actions
|-- Department reports
`-- Department audit / traceability
```

Avoid:

```text
Unit Dashboard A
Unit Dashboard B
Unit Dashboard C
Unit Dashboard D
```

unless an architecture review confirms that the unit has independent staffing, workflow ownership, queue management, reporting, audit boundary, and operational complexity.

## 7. Reception Principle

Reception is an operational intake capability, not necessarily a single dashboard.

Each major department may operate one of the following intake patterns:

- centralized reception
- department reception
- intake / registration point
- triage-linked intake point

Examples:

- GOPD Reception
- A&E Intake
- Specialist Clinic Reception
- Maternity Reception
- Radiology Booking / Intake
- Laboratory Sample Reception

Reception ownership must remain traceable to the patient, visit, department, staff actor, timestamp, and intake context.

## 8. Example Workspace Models

### Pharmacy Workspace

```text
Pharmacy Workspace
|-- Main Pharmacy Store
|-- OPD Dispensing Unit
|-- Ward Dispensing Unit
|-- Maternity Dispensing Unit
|-- Dispensing Queue
|-- Stock Requests
|-- Revenue Traceability
`-- Inventory Audit
```

### Laboratory Workspace

```text
Laboratory Workspace
|-- Sample Reception
|-- Hematology Unit
|-- Chemistry Unit
|-- Microbiology Unit
|-- Result Entry
|-- Validation Queue
`-- Released Results
```

### Radiology Workspace

```text
Radiology Workspace
|-- Imaging Requests
|-- X-Ray Unit
|-- Ultrasound Unit
|-- CT / Advanced Imaging
|-- Reporting Queue
|-- Completed Studies
`-- Radiology Reports
```

### Accident & Emergency Workspace

```text
Accident & Emergency Workspace
|-- Emergency Intake
|-- Triage
|-- Emergency Queue
|-- Resuscitation Bay
|-- Observation
|-- Admission Requests
|-- Emergency Billing
`-- Emergency Discharge
```

### Ward Workspace

```text
Ward Workspace
|-- Male Ward
|-- Female Ward
|-- Bed Management
|-- Admitted Patients
|-- Medication Administration
|-- Nursing Notes
|-- Doctor Review Requests
`-- Discharge Preparation
```

## 9. Workflow Governance Principles

The Department Workspace Architecture is governed by the following principles:

- department ownership before unit separation
- minimize dashboard fragmentation
- preserve operational traceability
- keep enterprise navigation consistent
- separate role-based workstations from department workspaces
- preserve HIS-wide governance integrity
- support scalable unit expansion
- maintain future multi-facility readiness
- preserve patient, visit, actor, department, and timestamp traceability
- keep clinical records inside the EMR / Clinical Records subdomain

## 10. Criteria For Independent Unit Separation

A unit may become an independent operational workspace only when at least one of the following is true:

- the unit has a separate queue requiring direct ownership
- the unit has separate staffing and supervisory accountability
- the unit has separate inventory, equipment, or result-validation workflow
- the unit has high-risk audit or compliance boundaries
- the unit requires different role authorization from the parent department
- the unit has measurable operational volume that justifies independent navigation

The default remains department-first design.

## 11. Implementation Constraint

No engineer, designer, or AI agent may create new standalone unit dashboards without checking this architecture decision.

Future dashboards must follow:

```text
HIS parent platform
-> enterprise domain
-> department workspace
-> unit sub-workspace where required
```

Changes that affect department ownership, unit separation, workflow routing, role permissions, or navigation hierarchy require architecture review before implementation.
