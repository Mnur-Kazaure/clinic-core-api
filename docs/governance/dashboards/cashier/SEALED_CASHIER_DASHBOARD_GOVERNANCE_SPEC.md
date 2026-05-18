# SEALED CASHIER DASHBOARD GOVERNANCE SPECIFICATION

## Revenue Collection Desk

Version: v1.0  
Status: Sealed governance specification  
Audience: frontend engineers, backend engineers, revenue workflow reviewers, auditors, product designers, and AI agents

## 1. Purpose

The Revenue Collection Desk is the hospital cashier workstation for fast, safe, receipt-first payment execution.

It exists to support:

- reduction of billing/payment confusion
- minimization of cashier mistakes
- improved receipt traceability
- reduced payment disputes
- stronger shift accountability
- stronger audit readiness
- reduced unauthorized financial adjustments
- accelerated patient payment flow
- pending payment visibility
- patient bill lookup
- payment collection workflow preview
- receipt generation preview
- cashier-visible payment history
- shift and till accountability
- payment exception visibility
- mistake-resistant payment processing

The cashier dashboard is operational. It is not an executive analytics dashboard and not an accountant reconciliation/control dashboard.

## 2. Approved Role Boundary

The cashier role owns payment collection execution at an assigned pay point. The current frontend demonstration uses `A & E / Theater Pay Point` and cashier `Aisha Bello` as approved demo identity data.

The dashboard must reinforce that every cashier action is tied to:

- cashier identity
- assigned desk/pay point
- active shift
- receipt trace
- payment method
- exception review path

## 3. Approved Dashboard Name

```text
Revenue Collection Desk
```

## 4. Approved Sidebar Sections

```text
Revenue Collection Desk
├── Collection Overview
├── Pending Payments
├── Patient Bill Lookup
├── Process Payment
├── Receipt Center
├── Payment History
├── Shift Management
├── Cash Drawer / Till Summary
├── Payment Exceptions
└── Cashier Workstation Settings
```

## 5. Authorized Payment Methods

Approved cashier payment method labels:

- POS
- Bank Transfer
- Cash

`Split Payment` may be shown as a frontend demonstration selector for future workflow planning, but production split payment support requires backend payment allocation, validation, receipt, and audit implementation before use.

Production split payment support also requires:

- allocation validation
- payment balancing
- partial receipt logic
- reconciliation enforcement
- audit-safe allocation tracking

## 6. Cashier Can Do

The cashier workspace may allow the cashier to:

- view pending bills
- search patient bills
- process demonstration payments
- preview payment method selection
- generate demonstration receipts
- view cashier-visible payment history
- view own shift status
- view cash drawer/till summary
- flag payment exceptions for review
- preview receipt reprint readiness
- prepare shift handover notes

## 7. Cashier Must Not Do

The cashier workspace must not allow the cashier to:

- approve refunds
- approve reversals
- approve waivers
- perform hospital-wide reconciliation
- view CMD-level financial intelligence
- perform accountant close/reconciliation
- manage user roles
- edit clinical records
- modify backend payment records directly
- edit posted payment amounts after receipt issuance
- void receipts without approved workflow authority
- bypass supervisor/accountant review for sensitive exceptions

## 8. Role Separation

| Domain | Owner | Cashier Boundary |
|---|---|---|
| Payment collection | Cashier | Cashier may collect/preview payment and generate receipt in authorized workflows. |
| Refund approval | Accountant/Admin | Cashier may view or flag; cashier must not approve. |
| Reversal approval | Accountant/Admin | Cashier may view or flag; cashier must not approve. |
| Waiver approval | Accountant/Admin/CMD policy | Cashier must not approve. |
| Reconciliation | Accountant | Cashier may see own shift/till posture only. |
| Executive financial intelligence | CMD | Cashier must not see hospital-wide executive analytics. |
| Clinical records | Clinical workstations | Cashier must not edit clinical records. |
| User access | Admin/Super Admin | Cashier must not manage users or roles. |

## 9. First Deployment Priority

| Section | Priority | Reason |
|---|---|---|
| Collection Overview | Critical | Cashier needs immediate shift and collection posture. |
| Pending Payments | Critical | Core queue for bills awaiting payment. |
| Patient Bill Lookup | Critical | Reduces patient/payment lookup friction. |
| Process Payment | Critical | Core cashier payment workflow. |
| Receipt Center | Critical | Receipt-first traceability is mandatory. |
| Shift Management | Critical | Cashier session accountability. |
| Cash Drawer / Till Summary | High | Cash accountability and variance prevention. |
| Payment Exceptions | High | Controlled visibility for failed, duplicate, unmatched, voided, and reversal-related events. |
| Payment History | High | Cashier-visible trace of posted/previewed transactions. |
| Cashier Workstation Settings | Low | Workstation configuration preview. |

## 10. Immutable Receipt Traceability Principle

Every generated receipt must remain traceable to:

- cashier identity
- active shift
- desk/pay point
- payment method
- patient
- invoice/bill source
- timestamp
- transaction reference

Receipt traceability must be immutable after issuance. Corrections, voids, reversals, refunds, and adjustments require controlled workflows with supervisor/accountant authorization and audit evidence.

## 11. Frontend Demonstration Workspace Boundary

The current Revenue Collection Desk is a frontend demonstration workspace. It uses approved fake data and local UI state only.

The current implementation does not connect to:

- live billing/invoice APIs
- live payment posting APIs
- real POS terminals
- bank transfer settlement services
- payment gateways
- production receipt generation services
- printer devices
- cash drawer hardware
- backend shift/till services
- production audit logging

All payment values, receipt numbers, transaction rows, shift data, till data, and exception rows are demonstration simulations pending backend integration.

## 12. Production Financial Controls

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

## 13. Production Requirements Before Live Use

Before production cashier use, the system requires:

- authenticated and authorized backend endpoints
- cashier pay-point assignment enforcement
- billing/invoice retrieval
- payment posting and validation
- receipt number generation and persistence
- payment method reference validation
- receipt printing/reprint controls
- cashier shift open/close workflows
- cash drawer/till declaration workflows
- exception flagging and supervisor/accountant review workflows
- immutable audit logging
- error handling, idempotency, and duplicate payment prevention

No engineer or AI agent should describe the current frontend demonstration as live payment processing.
