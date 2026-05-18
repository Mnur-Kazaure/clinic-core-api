# SEALED HIS DOMAIN ARCHITECTURE

Version: v1.0  
Status: Sealed architecture decision  
Audience: architects, engineers, designers, auditors, product reviewers, and AI agents

## 1. Architecture Decision

The platform is a unified Hospital Information System (HIS).

```text
HIS = Parent Enterprise Platform
EMR = Clinical Records Subdomain inside HIS
```

EMR must not be separated, branded, routed, or documented as an independent hospital platform/product inside this repository. EMR naming is approved only where the feature concerns clinical records, consultation documentation, patient care history, orders, notes, diagnosis, medication history, or other clinical-record workflows.

## 2. Approved Enterprise Domain Structure

```text
KSH Enterprise HIS
├── EMR / Clinical Records
├── Outpatient Management
├── Inpatient & Ward Management
├── Laboratory
├── Radiology
├── Pharmacy
├── Billing & Revenue Cycle
├── Cashier Operations
├── Audit & Compliance
├── Workforce & Attendance
├── Executive Intelligence (CMD)
└── Administration & Governance
```

## 3. Navigation Hierarchy Standard

The platform navigation and dashboard language should follow enterprise hospital operational grouping:

| Group | Approved Domains |
|---|---|
| Clinical Operations | EMR / Clinical Records, OPD, Consultation, Follow-up, Inpatient, Nursing, Ward |
| Diagnostic Services | Laboratory, Radiology |
| Revenue & Financial Governance | Cashier, Accountant, Billing, Revenue Intelligence |
| Executive Governance | CMD Command Center, Audit, Operational Intelligence, Workforce Oversight |
| Administration | User Management, RBAC, Attendance, Settings |

## 4. Approved Naming Patterns

Use:

- KSH Enterprise HIS
- Hospital Information System
- Clinical Records Workspace
- EMR / Clinical Records
- Executive Intelligence
- Accountant Financial Control Center
- Revenue Collection Desk

Avoid:

- using EMR as the umbrella platform name
- describing cashier, accountant, pharmacy, lab, CMD, administration, or workforce workflows as EMR modules
- mixing `EMR/HIS` as if both are equivalent parent platforms
- branding the system as a clinic-only system when the product represents hospital operations

## 5. Domain Boundary Rules

- HIS owns enterprise hospital operations across clinical, revenue, diagnostic, supply, workforce, audit, executive, and administration domains.
- EMR owns clinical records and patient-care documentation only.
- CMD dashboards remain executive oversight and intelligence workspaces.
- Accountant dashboards remain financial control and reconciliation workspaces.
- Cashier dashboards remain receipt-first collection workspaces.
- Reception dashboards remain front desk, patient intake, queue, visit coordination, and appointment/follow-up workspaces.
- Pharmacy, laboratory, radiology, ward, and nursing workflows remain HIS operational domains unless the workflow directly concerns clinical record documentation.

## 6. Implementation Constraint

No engineer, designer, or AI agent may rename the whole platform to EMR or split EMR into a standalone product without a formal architecture review and governance update.

Terminology changes must preserve existing routes and workflows unless a separate migration plan explicitly approves routing changes.
