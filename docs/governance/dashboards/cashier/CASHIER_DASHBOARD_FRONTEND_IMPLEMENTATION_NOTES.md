# Revenue Collection Desk Frontend Implementation Notes

## Purpose

This document helps engineers and AI agents understand the current `/cashier` frontend implementation, its boundaries, and its future backend integration requirements.

## Route and Files

| Item | Current Value |
|---|---|
| Route path | `/cashier` |
| Page file | `clinic-app/src/app/cashier/page.tsx` |
| Layout file | `clinic-app/src/app/cashier/layout.tsx` |
| Dashboard name | Revenue Collection Desk |
| Current implementation scope | Frontend demonstration workspace |

## Current Implementation Boundary

The current `/cashier` page is a frontend demonstration workspace using local fake data and local component state.

It does not currently perform:

- backend billing/invoice lookup
- backend payment posting
- real receipt persistence
- payment gateway processing
- POS terminal communication
- bank transfer settlement matching
- printer integration
- cash drawer hardware integration
- backend shift/till posting
- production audit logging

Important migration note: the previous backend-connected workflow on `/cashier` is no longer active on this route after the frontend demonstration rebuild. The route now presents the approved demonstration workspace for contract and workflow validation.

## Layout and Auth Guard

`clinic-app/src/app/cashier/layout.tsx` remains responsible for cashier route access:

- runs `authGuard()`
- applies `roleContextGuard(user.role, pathname)`
- permits role `CASHIER`
- redirects unauthenticated users to `/login`
- redirects unauthorized users to `/confirm-access`
- wraps children with `DashboardUserProvider`

Production APIs must still enforce server-side authorization. The client layout guard alone must not be treated as production data protection.

## Sidebar-Driven Workspace Model

The page uses a local active workspace state. Default workspace:

```text
Collection Overview
```

Approved workspaces:

- Collection Overview
- Pending Payments
- Patient Bill Lookup
- Process Payment
- Receipt Center
- Payment History
- Shift Management
- Cash Drawer / Till Summary
- Payment Exceptions
- Cashier Workstation Settings

Clicking a sidebar item switches the main content to the focused workspace. The page must not become a long-scroll dashboard containing all workspaces at once.

## Fake Data Strategy

The current demo data uses realistic hospital cashier examples:

- cashier: `Aisha Bello`
- desk/pay point: `A & E / Theater Pay Point`
- shift opened: `07:45 AM`
- supervisor: `Finance Lead`
- shift status: `Open`
- today's collections: `₦1.85M`
- receipts issued: `42`
- POS collections: `₦820K`
- bank transfer collections: `₦610K`
- cash collections: `₦420K`
- opening cash balance: `₦50,000`
- expected cash: `₦470,000`
- cash variance: `₦0`

Patient, receipt, transaction, and exception rows are demonstration data only.

## UI-Ready Controls

The following controls are present for demonstration but are not wired to backend behavior:

- search fields
- filter dropdowns
- process payment buttons
- payment method selector
- amount received field
- payment reference field
- confirm payment and generate receipt button
- receipt reprint readiness
- exception flag/review buttons
- shift close/handover preview
- cashier workstation settings

## UX Principles

### Receipt-First Workflow

Every payment path must visually reinforce that cashier collection ends in a traceable receipt.

The dashboard should make receipt number, patient, MRN, amount, method, cashier, time, status, and reference visible wherever payment traceability matters.

### Immutable Receipt Traceability Principle

Every generated receipt must remain traceable to:

- cashier identity
- active shift
- desk/pay point
- payment method
- patient
- invoice/bill source
- timestamp
- transaction reference

Production workflows must not allow posted payment amounts to be edited after receipt issuance. Corrections, voids, reversals, refunds, and adjustments require controlled approval workflows and audit evidence.

### Shift and Till Accountability

Cashier actions must be tied to cashier identity, assigned pay point, shift status, supervisor, cash drawer/till posture, and receipt trace.

The cashier accountability strip exists to reinforce operational ownership and reduce denial or ambiguity.

### Mistake-Resistant Operation

The cashier dashboard should be:

- compact
- readable
- fast to scan
- operationally dense
- status-driven
- clear about primary actions
- explicit about exceptions and review boundaries

## Role Boundary with Accountant and CMD

| Capability | Cashier | Accountant | CMD |
|---|---|---|---|
| Collect payment | Yes | Review/control role, not primary cashier flow | No |
| Generate receipt | Yes, after authorized payment workflow | Review/audit visibility | Oversight visibility only |
| Approve refund/reversal | No | Yes, where authorized | Oversight/escalation only |
| Reconcile cashier sessions | No | Yes | Oversight visibility only |
| View hospital-wide financial intelligence | No | Limited finance-control views | Yes |
| Manage user roles | No | No | No, unless separately authorized |
| Edit clinical records | No | No | No |

## Future Backend Integration Areas

Production implementation requires:

- billing/invoice API
- patient bill lookup API
- payment posting API
- payment method validation
- POS terminal integration
- bank transfer confirmation/settlement integration
- receipt generation API
- receipt search/reprint API
- cashier shift API
- cash drawer/till API
- payment exception API
- printer integration
- immutable audit logging
- role-based backend authorization
- duplicate payment prevention and idempotency
- supervisor/accountant review workflow

Production split payment support also requires allocation validation, payment balancing, partial receipt logic, reconciliation enforcement, and audit-safe allocation tracking.

## Production Financial Controls

Production deployment requires:

- immutable audit logging
- idempotent payment posting
- duplicate payment prevention
- receipt number uniqueness enforcement
- cashier shift enforcement
- supervisor/accountant approval workflows
- payment exception escalation
- role-based financial authorization
- transaction traceability
- reconciliation integrity

## Explicit Demo-Only Statements

- Payment buttons are demo-only.
- Receipt generation is demo-only.
- Filters/search are UI-ready only.
- Exception buttons are flag/review previews only.
- Refunds and reversals remain outside cashier authority.
- No real payment gateway support is currently implemented by this frontend page.
- No production receipt posting is currently implemented by this frontend page.

## Validation Commands

Use these commands after cashier frontend implementation changes:

```bash
pnpm --dir clinic-app exec eslint src/app/cashier/page.tsx src/app/cashier/layout.tsx
pnpm --dir clinic-app exec tsc --noEmit
pnpm --dir clinic-app build
```

For documentation-only changes, use:

```bash
find docs/governance -maxdepth 4 -type f | sort
git status --short
```
