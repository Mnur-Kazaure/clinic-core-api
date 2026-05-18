# Dashboard Governance Documentation

This folder contains sealed governance specifications and implementation notes for role-based HIS dashboards.

Each dashboard has its own folder so engineers, auditors, designers, and AI agents can identify:

- approved dashboard purpose
- approved sections and subsections
- ownership boundaries
- demonstration-only versus production functionality
- implementation constraints
- future backend integration requirements

Current dashboard folders:

| Folder | Governance Status | Purpose |
|---|---|---|
| `cmd/` | Sealed | Chief Medical Director executive command center governance and demo documentation |
| `accountant/` | Sealed | Accountant Financial Control Center governance, reconciliation ownership, daily close integrity, and anti-leakage controls |
| `cashier/` | Sealed | Revenue Collection Desk governance, receipt-first workflow, shift/till accountability, and payment exception visibility |
| `reception/` | Sealed specification | Reception dashboard governance specification |

These documents prevent AI-agent and implementation drift. Application changes must follow the sealed specifications unless an architecture review approves a revised governance version.

Dashboard governance documents are sealed specifications.

Implementation changes affecting workflow, permissions, financial controls, reconciliation behavior, receipt logic, or exception handling must update the corresponding governance specification before production approval.
