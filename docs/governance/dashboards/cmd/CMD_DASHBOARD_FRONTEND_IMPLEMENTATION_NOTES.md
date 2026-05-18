# CMD Dashboard Frontend Implementation Notes

## Purpose

This document explains the current frontend implementation boundaries for the CMD dashboard so engineers, auditors, and AI agents can safely continue development without drifting from the sealed governance specification.

## Current Route and Files

| Item | Current Value |
|---|---|
| Dashboard route | `/cmd` |
| Primary page file | `clinic-app/src/app/cmd/page.tsx` |
| Route layout file | `clinic-app/src/app/cmd/layout.tsx` |
| Framework pattern | Next.js App Router |
| Current scope | Frontend demonstration workspace |

## Modified Implementation Files

The current CMD dashboard implementation is contained in:

- `clinic-app/src/app/cmd/page.tsx`
- `clinic-app/src/app/cmd/layout.tsx`

Documentation changes must not modify these files unless an implementation task explicitly asks for code changes.

## Access Guard Boundary

`clinic-app/src/app/cmd/layout.tsx` preserves a client-side CMD access guard:

- runs `authGuard()`
- applies `roleContextGuard(user.role, pathname)`
- allows only role `CMD`
- redirects unauthenticated users to `/login`
- redirects unauthorized role context to `/confirm-access`
- wraps authorized content with `DashboardUserProvider`

This is a frontend guard and must be backed by server/API authorization in production. No documentation should claim that the frontend guard alone is sufficient for production data security.

## Sidebar-Driven Interaction Model

The CMD dashboard uses a local active navigation model:

- `activeSection`
- `activeSubsection`
- default section: `Executive Overview`
- default subsection: `Hospital Snapshot`

The sidebar renders approved `navigationGroups`. Clicking a section sets the first subsection for that section. Clicking a subsection switches the main workspace to that subsection only.

Expected behavior:

```text
Click sidebar subsection
-> update active section/subsection state
-> render focused subsection content in the main workspace
-> do not render every subsection as one long page
```

## Current Navigation Ownership

The approved section/subsection data lives in `navigationGroups` inside `clinic-app/src/app/cmd/page.tsx`.

Current major workspace handlers include:

- `ExecutiveOverviewWorkspace`
- `StaffGovernanceWorkspace`
- `FinancialIntelligenceWorkspace`
- `GenericWorkspace`
- `WorkspaceContent`

Staff Governance and Financial Intelligence contain the strongest custom frontend demonstration views. Other sections use focused preview workspaces and should be upgraded incrementally without changing the sealed navigation structure.

Naming alignment note: the frontend navigation and sealed governance language use `Operational Systems Status` and `Department Staffing Posture`.

## Frontend Demonstration Data Strategy

The current dashboard uses realistic but fake frontend data to demonstrate capability. This includes:

- hospital status and KPI signals
- patient-flow and operational pressure previews
- cashier collections and transaction traces
- revenue reconciliation variance signals
- pharmacy revenue and traceability previews
- attendance records and biometric events
- shift compliance and staffing posture
- audit, reports, and settings previews

The data is intended for CMD presentation readiness only. It must not be described as live data, production telemetry, connected biometric attendance, connected payment processing, or operational reporting.

## UI-Ready but Nonfunctional Controls

The following controls are visual demonstration controls until backend integration exists:

- search fields
- filter dropdowns
- date, department, cashier, status, and payment method filters
- export buttons
- guided reconciliation buttons
- supervisor notification buttons
- escalation buttons
- mark-for-review buttons
- preference controls

Future implementation must connect these controls to authorized APIs with validation, loading states, empty states, error handling, pagination where needed, and audit logging.

## Visual Design Principles

The CMD dashboard visual system must remain:

- executive and institutional
- dark, cinematic, and healthcare-enterprise aligned
- sidebar-driven and focused
- premium without becoming flashy
- readable under presentation conditions
- distinct from departmental workstations
- calm but capable of showing operational pressure
- domain-colored without visual noise

Domain color ownership:

| Domain | Visual Direction |
|---|---|
| Finance | cool cyan/blue with emerald verification and amber/rose risk states |
| Staff governance | teal/emerald workforce posture with amber/rose exceptions |
| Alerts | restrained amber/rose urgency |
| Audit | steel blue and controlled risk signals |
| Supply governance | teal/emerald with amber stock-risk signals |

## Current Demo Highlights

### Staff Governance

Implemented frontend demonstration views:

- Attendance Intelligence: staff attendance trace rows with phone, department, role, shift, clock-in/out, status, lateness, device, and review state.
- Biometric Monitoring: biometric device health, sync state, event stream, failed attempts, unmatched identities, and workflow demonstration.
- Shift Compliance: roster coverage, shift windows, compliance percentages, exceptions, and timeline.
- Workforce Analytics: trend signals, department pressure, exception patterns, risk forecast, and CMD insights.
- Department Staffing Posture: all 12 hospital departments with required staff, staff on duty, coverage, status, risk, and CMD visibility.

### Financial Intelligence

Implemented frontend demonstration views:

- Revenue Overview
- Cashier Collections
- Payment Traceability
- Department Revenue
- Revenue Reconciliation Intelligence
- Outstanding Bills
- Refund & Waiver Audit
- Pharmacy Revenue & Traceability

The financial demo uses revenue, collections, transactions, reconciliation, variance, matched, verified, review required, and receipt traceability terminology. Avoid "sales" except in genuine pharmacy retail context; prefer "Pharmacy Revenue".

## Known Future Backend Integration Areas

Production implementation requires:

- hospital summary API
- patient flow and visit APIs
- admission, ward, bed, and discharge APIs
- billing, invoice, receipt, and payment APIs
- cashier shift and collection APIs
- POS and bank transfer settlement ingestion
- revenue reconciliation API
- pharmacy dispensing and revenue APIs
- supply request and inventory ledger APIs
- staff directory, roster, attendance, and biometric event APIs
- audit log API with actor, role, timestamp, entity, and session metadata
- report generation and secure export APIs
- notification and escalation workflow APIs
- authorization middleware on all backend endpoints
- immutable audit logging for sensitive operations

## Validation Commands

Use these commands after CMD frontend implementation changes:

```bash
pnpm --dir clinic-app exec eslint src/app/cmd/page.tsx src/app/cmd/layout.tsx
pnpm --dir clinic-app exec tsc --noEmit
pnpm --dir clinic-app build
```

For documentation-only changes, the required validation is:

```bash
find docs/governance -maxdepth 4 -type f | sort
git status --short
```

## Implementation Guardrails

Do not:

- add backend claims to frontend demonstration content
- move cashier, accountant, HR, pharmacy, lab, doctor, nurse, or reception operations into CMD
- rename sealed sections or subsections without governance review
- replace the sidebar-driven workspace with a long scrolling page
- connect demo buttons to actions without authorization and audit logging
- weaken or bypass the CMD route guard
- introduce generic admin UI patterns that reduce executive authority

All future changes must preserve the sealed governance structure unless an architecture review approves a new version of the CMD governance spec.
