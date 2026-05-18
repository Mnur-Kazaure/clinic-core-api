# SEALED CMD DASHBOARD GOVERNANCE SPECIFICATION

## KSH Enterprise HIS Executive Command Center

Version: v1.1  
Status: Sealed governance specification  
Audience: architects, engineers, product designers, auditors, implementation reviewers, and AI agents

## 1. Purpose

The Chief Medical Director dashboard is the executive command center for Specialist Hospital Kazaure. It exists to provide hospital-wide oversight, governance visibility, operational intelligence, financial traceability, and institutional accountability.

The CMD dashboard is not an operational data-entry workstation. It must help the CMD understand what is happening across the hospital without taking over the duties of reception, clinical, pharmacy, laboratory, cashier, accountant, HR, or platform administration teams.

Current implementation note: the CMD dashboard is a frontend demonstration workspace using approved demo data. It does not yet connect to live HIS telemetry, backend APIs, databases, biometric devices, payment processors, or reporting services.

The CMD dashboard is intentionally governance-oriented and must not evolve into a transactional operational workstation.

Architecture terminology: this dashboard belongs to the KSH Enterprise HIS. EMR/Clinical Records is a clinical subdomain inside the HIS and must not be treated as the parent platform.

## 2. Approved CMD Sections

The CMD dashboard is sealed around the following sections:

| Section | Ownership Purpose | First Deployment Priority |
|---|---|---|
| Executive Overview | Hospital-wide command snapshot and executive posture | Critical |
| Hospital Operations | Patient flow, admissions, ward activity, emergency pressure, and department performance | Critical |
| Financial Intelligence | Revenue, cashier collections, payment traceability, reconciliation, and financial exceptions | Critical |
| Pharmacy & Supply Governance | Pharmacy and commodity request oversight, stock risk, and approval visibility | High |
| Staff Governance | Attendance, biometric monitoring, shift posture, workforce analytics, and staffing visibility | Critical |
| Audit & Compliance | User activity, patient access, financial audit, clinical changes, sessions, permissions, and suspicious activity | Critical |
| Executive Reports | Executive reporting and export previews | Medium |
| Executive Settings | CMD preferences and executive profile preview | Low |

## 3. Approved Navigation Structure

```text
CMD Command Center
├── Executive Overview
├── Hospital Operations
├── Financial Intelligence
├── Pharmacy & Supply Governance
├── Staff Governance
├── Audit & Compliance
├── Executive Reports
└── Executive Settings
```

## 4. Approved Subsections

### 4.1 Executive Overview

Purpose: provide immediate hospital-wide executive visibility.

Approved subsections:

```text
Executive Overview
├── Hospital Snapshot
├── Critical Alerts
├── Operational KPIs
├── Daily Executive Summary
└── Operational Systems Status
```

CMD can see hospital status, emergency pressure, bed utilization, critical signals, active departments, patient movement, revenue posture, operational KPIs, and system status summaries.

### 4.2 Hospital Operations

Purpose: provide executive oversight of patient movement and departmental service pressure.

Approved subsections:

```text
Hospital Operations
├── Patient Flow Overview
├── Admission & Discharge Monitoring
├── Bed & Ward Utilization
├── Emergency Monitoring
├── Department Performance
└── Follow-Up Compliance
```

CMD can see patient flow, admission and discharge posture, bed and ward usage, emergency pressure, departmental bottlenecks, and follow-up compliance signals.

### 4.3 Financial Intelligence

Purpose: provide executive financial governance, revenue visibility, collection accountability, transaction traceability, and reconciliation intelligence.

Approved subsections:

```text
Financial Intelligence
├── Revenue Overview
├── Cashier Collections
├── Payment Traceability
├── Department Revenue
├── Revenue Reconciliation Intelligence
├── Outstanding Bills
├── Refund & Waiver Audit
└── Pharmacy Revenue & Traceability
```

Terminology:

| Term | Approved Use |
|---|---|
| Revenue | Hospital-wide, departmental, or pharmacy income visibility |
| Collections | Cashier-level money received by location, desk, and payment method |
| Transactions | Individual receipt/payment records |
| Reconciliation | Matching expected collections, receipts, payment methods, and reported revenue |
| Variance | Difference requiring financial review |

CMD can see revenue posture, cashier collections, receipt traceability, department revenue ranking, outstanding bills, refund/waiver exposure, pharmacy revenue, and guided reconciliation risk signals. The CMD dashboard must not become a cashier terminal or accountant transaction-entry screen.

#### Financial Demo Boundary

The current Financial Intelligence implementation is frontend demonstration data intended for CMD presentation and workflow validation.

No live payment processor, bank settlement service, POS terminal, reconciliation engine, or accounting ledger is currently connected.

All financial values, variances, reconciliation states, cashier collections, and transaction traces shown in the CMD dashboard are approved demo simulations pending backend integration.

### 4.4 Pharmacy & Supply Governance

Purpose: provide governance visibility over pharmacy supply requests, approval queues, stock risk, and commodity movement.

Approved subsections:

```text
Pharmacy & Supply Governance
├── Supply Approval Queue
├── Departmental Requests
├── Dispensing Unit Requests
├── Pharmacy Store Oversight
├── Stock Movement Audit
├── Critical Stock Alerts
├── High-Risk Commodity Monitoring
├── Supply Consumption Analytics
├── Approval History
└── Emergency Supply Requests
```

CMD can see approval queues, department requests, dispensing unit requests, stock movement signals, high-risk commodity monitoring, consumption analytics, and emergency supply requests. Operational inventory CRUD belongs to pharmacy and store workstations, not the CMD dashboard.

### 4.5 Staff Governance

Purpose: provide executive workforce accountability, biometric attendance visibility, shift posture, and department staffing oversight.

Approved subsections:

```text
Staff Governance
├── Attendance Intelligence
├── Biometric Monitoring
├── Shift Compliance
├── Workforce Analytics
└── Department Staffing Posture
```

CMD can see attendance intelligence, biometric device status, clock-in/clock-out capture posture, late/absent/early-departure exceptions, shift compliance, workforce pressure, and department-by-department staffing posture.

The CMD dashboard must remain an oversight surface. It must not become an HR enrollment screen, payroll screen, staff discipline screen, or device administration console.

### 4.6 Audit & Compliance

Purpose: provide traceability of user activity, patient record access, financial actions, clinical changes, sessions, permissions, and suspicious activity.

Approved subsections:

```text
Audit & Compliance
├── User Activity Audit
├── Patient Record Access Audit
├── Financial Audit Trail
├── Clinical Change History
├── Login & Session Audit
├── Permission Change Audit
├── Suspicious Activities
└── Compliance Reports
```

CMD can see audit visibility and compliance posture. The CMD dashboard must not expose raw engineering logs, database consoles, or security configuration tools.

### 4.7 Executive Reports

Purpose: provide executive report previews and export readiness for board-level and management review.

Approved subsections:

```text
Executive Reports
├── Operational Reports
├── Financial Reports
├── Audit Reports
├── Department Performance Reports
└── Executive Export Center
```

CMD can see report availability, export previews, and executive briefing readiness. Report generation must later be backed by authorized backend APIs and audit logging.

### 4.8 Executive Settings

Purpose: provide executive preference previews without exposing platform administration controls.

Approved subsections:

```text
Executive Settings
├── Dashboard Preferences
├── Notification Preferences
├── Report Preferences
└── Executive Profile
```

CMD can see preference previews and profile context. User provisioning, permission management, infrastructure settings, and deployment settings belong outside CMD.

## 5. Role Separation Rules

| Role or Workstation | Must Own | Must Not Be Moved Into CMD |
|---|---|---|
| Super Admin / Platform Operations | system reliability, infrastructure, deployment, backups, database health, security operations | raw infrastructure tools, server management, database administration |
| Hospital Admin | operational configuration and institutional setup | full platform engineering controls |
| Accountant | financial processing, posting, reconciliation operations, close processes | CMD-only executive governance posture |
| Cashier | payment collection, receipt issuance, cashier shift operations | hospital-wide executive financial authority |
| Reception / Records | registration, patient records intake, visit initiation | CMD oversight dashboards |
| Doctor | consultation, diagnosis, orders, clinical notes | hospital-wide audit and financial control |
| Nurse | triage, nursing notes, ward observations, medication administration support | executive governance controls |
| Pharmacy | dispensing, stock operations, inventory management | CMD-level pharmacy governance summary only |
| Laboratory | sample handling, investigations, result workflows | CMD-level service pressure visibility only |
| HR / Attendance Admin | staff enrollment, attendance device operations, roster setup | CMD-level biometric and staffing oversight only |
| Auditor / Compliance | deep compliance review and evidence handling | CMD summary and escalation visibility only |
| IT Support | device support and technical issue resolution | CMD-facing system posture only |

## 6. CMD Must Not Do

The CMD dashboard must not contain:

- clinical data entry forms
- prescription entry
- nursing documentation forms
- patient registration forms
- cashier payment entry forms
- refund execution forms
- inventory CRUD operations
- biometric enrollment operations
- payroll actions
- staff disciplinary actions
- server, database, deployment, or DNS administration
- raw engineering observability consoles

## 7. First-Deployment Critical Subsections

The following subsections are critical for the CMD presentation and first controlled deployment:

| Area | Critical Subsections |
|---|---|
| Executive Overview | Hospital Snapshot, Critical Alerts, Operational KPIs, Operational Systems Status |
| Hospital Operations | Patient Flow Overview, Admission & Discharge Monitoring, Bed & Ward Utilization, Emergency Monitoring |
| Financial Intelligence | Revenue Overview, Cashier Collections, Payment Traceability, Revenue Reconciliation Intelligence, Pharmacy Revenue & Traceability |
| Staff Governance | Attendance Intelligence, Biometric Monitoring, Shift Compliance, Department Staffing Posture |
| Audit & Compliance | User Activity Audit, Patient Record Access Audit, Financial Audit Trail, Login & Session Audit, Suspicious Activities |
| Pharmacy & Supply Governance | Supply Approval Queue, Stock Movement Audit, Critical Stock Alerts, High-Risk Commodity Monitoring, Approval History |

## 8. Frontend Demonstration Boundary

The current CMD dashboard demonstration is approved as a frontend demonstration workspace. It may show realistic demo data and backend-ready controls, but it must not claim live production capability until the relevant APIs, database models, integrations, and audit trails exist.

Demonstration-only items include:

- KPI values and trend signals
- attendance and biometric events
- cashier collections and transaction traces
- reconciliation variance signals
- supply approval signals
- audit timeline previews
- filters, searches, export buttons, and action buttons

Future production implementation must connect these views to authorized backend APIs, role-guarded data access, immutable audit logging, validation, and controlled export services.

## 9. Executive Adoption Strategy

The CMD dashboard follows a second-nature adoption strategy:

- executive visibility without operational overload
- guided intelligence instead of raw system complexity
- focused workspaces instead of dense operational screens
- traceability-first financial and workforce governance
- fast executive comprehension under pressure conditions

The goal is to make executive oversight feel natural, trusted, and institutionally dependable.

## 10. Architecture Governance

The CMD dashboard must remain:

- sidebar-driven and subsection-focused
- executive oversight oriented
- role-bound to CMD access
- separated from operational workstations
- auditable by design
- honest about the frontend demonstration state until integrations are implemented

No engineer, AI agent, or implementation team should add or remove CMD sections, rename sealed subsections, or shift operational responsibilities into the CMD dashboard without architecture review and approval.
