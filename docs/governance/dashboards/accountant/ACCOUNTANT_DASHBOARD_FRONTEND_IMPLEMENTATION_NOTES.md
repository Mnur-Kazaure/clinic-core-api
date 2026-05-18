# ACCOUNTANT DASHBOARD FRONTEND IMPLEMENTATION NOTES

## Purpose

This document helps engineers and AI agents understand the implemented Accountant Financial Control Center frontend, its current boundaries, and its future backend integration requirements.

Architecture placement:

```text
KSH Enterprise HIS
→ Revenue & Financial Governance Domain
→ Accountant Financial Control Center
```

HIS is the parent enterprise platform. EMR / Clinical Records is a clinical records subdomain and must not be used as the umbrella term for accountant, cashier, CMD, audit, or financial governance workflows.

## Route and Files

| Item | Current Value |
|---|---|
| Route path | `/accountant` |
| Page file | `clinic-app/src/app/accountant/page.tsx` |
| Layout file | `clinic-app/src/app/accountant/layout.tsx` |
| Dashboard name | Accountant Financial Control Center |
| Domain | Revenue & Financial Governance |
| Current scope | Frontend demonstration workspace |

## Current Implementation Boundary

The current `/accountant` page is a frontend demonstration workspace using local fake data and local component state.

It does not currently perform:

- backend financial overview loading
- backend cashier session reconciliation
- backend payment verification
- real settlement verification
- real POS settlement matching
- real bank transfer matching
- real cash handover posting
- real refund approval
- real reversal approval
- real waiver approval
- real daily close approval
- real report export
- production audit logging
- production financial posting

Buttons, guided workflow steps, review actions, export actions, reconciliation actions, approval actions, and close actions are visual governance demonstrations only.

## Layout and Auth Guard

`clinic-app/src/app/accountant/layout.tsx` remains responsible for accountant route access:

- runs `authGuard()`
- applies `roleContextGuard(user.role, pathname)`
- permits role `ACCOUNTANT`
- redirects unauthenticated users to `/login`
- redirects unauthorized users to `/confirm-access`
- wraps children with `DashboardUserProvider`

Production APIs must still enforce server-side authorization. The client layout guard must not be treated as production financial data protection.

## Sidebar-Driven Workspace Model

The page uses local active workspace state. Default workspace:

```text
Financial Control Overview
```

Approved workspaces:

- Financial Control Overview
- Cashier Session Oversight
- Revenue Reconciliation Intelligence
- Payment Verification
- Refund & Reversal Governance
- Waiver & Discount Review
- Outstanding Bills Control
- Department Revenue Control
- Daily Close & Handover
- Financial Exceptions
- Audit Trail & Reports
- Financial Control Preferences

Clicking a sidebar item switches the main content to the focused workspace. The page must not become a long-scroll dashboard containing all workspaces at once.

## Implemented Premium UI/UX Reality

The Accountant Financial Control Center currently implements:

- enterprise financial control shell
- operational finance workspace framing
- compact financial control sidebar
- premium financial authority identity card
- high-density finance panels
- controlled slate, steel, cyan, emerald, amber, rose, and indigo semantics
- operational finance state indicators
- micro-visualization layer
- cashier variance heat indicators
- payment distribution indicators
- revenue movement micro-bars
- reconciliation source matrix
- guided reconciliation review
- close readiness posture
- audit timeline and report readiness
- financial exception posture
- visual-only approval and escalation controls

The workstation is intentionally stricter and denser than CMD. It must feel like a finance-control workstation, not an executive command center and not a cashier desk.

## Visual and Interaction Principles

### Accountant Workstation Design Principles

- operational density over decorative whitespace
- finance-first hierarchy
- audit-safe terminology
- controlled visual language
- high-trust enterprise palette
- fast scan efficiency
- institutional readability
- reconciliation-centered workflow design
- variance visibility prioritization
- financial governance before convenience

### Color Semantics

| Color Family | Intended Use |
|---|---|
| Slate / Steel | Institutional financial control surfaces |
| Cyan | Financial intelligence and reconciliation telemetry |
| Emerald | Matched, verified, clean evidence |
| Amber | Pending review, watch, unresolved but not critical |
| Rose | Critical variance, suspicious activity, CMD/Admin visibility |
| Indigo / Graphite | Close integrity and audit/governance posture |

## Embedded Governance Semantics

The UI copy and states intentionally reinforce:

- no untraceable financial action
- no destructive financial mutation
- no reconciliation without evidence
- no clean close with unresolved critical variance
- no sensitive approval without authority
- no financial exception without audit visibility
- no settlement verification without reference evidence
- no financial control outside immutable auditability

## Fake Data Strategy

The current demo data uses realistic hospital finance examples:

- total collections: `₦8.42M`
- reconciled amount: `₦8.31M`
- outstanding variance: `₦110K`
- matched receipts: `176 / 184`
- unmatched transactions: `8`
- suspicious adjustments: `3`
- pending cashier closures: `2`
- accountant: `Amina Yusuf`
- role: `Senior Accountant`

Cashier, receipt, transaction, department revenue, outstanding bill, refund/reversal, waiver, close, exception, audit, and report rows are demonstration data only.

## Future Backend Integration Areas

Production implementation requires:

- accountant overview API
- cashier session API
- cashier shift close/handover API
- payment verification API
- receipt audit API
- settlement verification API
- reconciliation API
- refund/reversal approval API
- waiver/discount review API
- outstanding bills API
- department revenue API
- daily close API
- financial exceptions API
- audit trail API
- report export API
- immutable audit logging
- RBAC enforcement
- idempotency controls
- duplicate payment prevention
- variance threshold configuration and audit
- CMD/Admin escalation workflow

## Role Boundary Reminder

| Role | Boundary |
|---|---|
| Cashier | Collect and receipt frontline payments |
| Accountant | Verify, reconcile, approve where authorized, close, and review exceptions |
| CMD | Oversee institutional financial posture and interrogate executive financial intelligence |

The Accountant Financial Control Center must not become:

- cashier payment processing
- CMD executive intelligence
- clinical records workflow
- pharmacy inventory CRUD
- patient registration
- user/role administration

## Validation Commands

Recommended frontend validation after implementation changes:

```bash
pnpm --dir clinic-app exec eslint src/app/accountant/page.tsx src/app/accountant/layout.tsx
pnpm --dir clinic-app exec tsc --noEmit
pnpm --dir clinic-app build
```

Documentation-only changes do not require frontend rebuild unless application files are modified.
