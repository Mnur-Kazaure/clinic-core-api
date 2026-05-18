# SEALED ACCOUNTANT DASHBOARD GOVERNANCE SPECIFICATION

## Accountant Financial Control Center

Version: v2.1  
Status: Sealed governance specification after premium frontend implementation  
Audience: architects, backend engineers, frontend engineers, healthcare finance reviewers, auditors, product designers, and AI agents

## 1. Purpose

The Accountant Financial Control Center is the finance-control workstation for KSH Enterprise HIS revenue governance.

Architecture placement:

```text
KSH Enterprise HIS
→ Revenue & Financial Governance Domain
→ Accountant Financial Control Center
```

Architecture terminology: this dashboard belongs to the KSH Enterprise HIS. EMR/Clinical Records is a clinical subdomain inside the HIS and must not be treated as the parent platform.

It is responsible for:

- reduction of financial leakage
- strengthened reconciliation integrity
- reduced cashier variance risk
- improved settlement visibility
- strengthened refund/reversal governance
- improved audit readiness
- prevention of untraceable financial adjustments
- improved daily close integrity
- institutionally dependable financial oversight
- cashier session oversight
- revenue reconciliation
- payment verification
- refund, reversal, and waiver governance
- daily financial close
- settlement verification
- variance detection
- financial exception review
- audit readiness
- financial control reporting
- revenue leakage prevention

The accountant dashboard must feel strict, controlled, authoritative, auditable, and financially intelligent. It must read as enterprise financial governance infrastructure, not a generic admin dashboard, cashier extension, analytics dashboard, or billing page.

The Accountant Financial Control Center is operational-financial governance infrastructure, not a cashier workstation and not an executive CMD intelligence console.

Core role separation:

```text
Cashier = collect and receipt
Accountant = control, reconcile, approve, close
CMD = oversee and interrogate financial posture
```

## 2. Approved Accountant Dashboard Name

```text
Accountant Financial Control Center
```

## 3. Approved Role Boundary

The accountant owns financial control and reconciliation. The accountant verifies whether hospital revenue, receipts, cashier shifts, payment methods, refunds, reversals, waivers, and daily close records are financially consistent and audit-ready.

The accountant:

- does not perform frontline cashier collection as the primary workflow
- does not replace CMD oversight
- does not manage clinical records
- does not bypass immutable audit logs
- does not act as platform super admin unless separately authorized
- does not conceal cashier variance or settlement mismatch

## 4. Accountant Can Do

The accountant may:

- review cashier collections
- review cashier shifts
- verify payment postings
- reconcile POS, Bank Transfer, and Cash collections
- review unmatched transfers
- approve or reject refunds where authorized
- approve or reject reversals where authorized
- review waiver requests where authorized
- monitor variance thresholds
- prepare daily close
- generate accountant financial reports
- flag suspicious financial activity
- escalate financial risks to CMD/Admin
- review department revenue control posture
- review outstanding bills and discharge financial holds

## 5. Accountant Must Not Do

The accountant must not:

- edit issued receipt amounts directly
- delete receipts
- delete payment transactions
- bypass cashier identity and shift traceability
- bypass immutable audit logs
- approve own suspicious transaction without secondary review
- override CMD-restricted controls
- modify clinical documentation
- manage user roles unless separately authorized
- conceal cashier variance or settlement mismatch
- approve reversals/refunds without policy authority and audit reason
- alter settlement evidence after reconciliation

## 6. Approved Accountant Sections

```text
Accountant Financial Control Center
├── Financial Control Overview
├── Cashier Session Oversight
├── Revenue Reconciliation Intelligence
├── Payment Verification
├── Refund & Reversal Governance
├── Waiver & Discount Review
├── Outstanding Bills Control
├── Department Revenue Control
├── Daily Close & Handover
├── Financial Exceptions
├── Audit Trail & Reports
└── Financial Control Preferences
```

## 7. Section Ownership Definitions

| Section | Ownership Definition | First Deployment Priority |
|---|---|---|
| Financial Control Overview | High-level accountant posture for collections, pending reconciliation, exceptions, variances, and close readiness. | Critical |
| Cashier Session Oversight | Cashier-by-cashier review of shift collections, receipt counts, declared cash, expected cash, variance, open/closed status, and supervisor review. | Critical |
| Revenue Reconciliation Intelligence | Guided reconciliation of total collections, matched receipts, payment method settlement, cashier variance, department reconciliation, and risk signals. | Critical |
| Payment Verification | Verification of POS, Bank Transfer, Cash, and payment references against posted receipts/invoices. | Critical |
| Refund & Reversal Governance | Controlled approval/rejection workflow for refunds and payment reversals where accountant authority is configured. | High |
| Waiver & Discount Review | Review of financial concessions, discounts, waivers, approval source, policy compliance, and audit reason. | High |
| Outstanding Bills Control | Visibility into unpaid balances, discharge clearance holds, inpatient pending bills, and department debt exposure. | High |
| Department Revenue Control | Department/service-line revenue control, traceability, variance posture, and revenue leakage monitoring. | High |
| Daily Close & Handover | End-of-day financial close, shift aggregation, cash handover, reconciliation summary, and close approval status. | Critical |
| Financial Exceptions | Suspicious financial activity, duplicate payments, unmatched transfers, voided receipts, variance flags, and delayed settlement. | Critical |
| Audit Trail & Reports | Immutable accountant-facing audit trail and export-ready reports. | High |
| Financial Control Preferences | Accountant profile, approval preferences, report preferences, and workstation controls. | Low |

## 7.1 Implemented Premium Workstation Reality

The current frontend implementation is a premium enterprise demonstration workstation. It implements:

- enterprise financial control shell
- operational finance workspace model
- sidebar-driven focused workspaces
- operational finance state indicators
- premium financial color semantics
- micro-visualization layer for reconciliation, variance, payment distribution, and department revenue posture
- guided reconciliation review workflow
- cashier oversight matrix
- close readiness and blocked-close posture
- refund/reversal governance posture
- financial exception posture
- audit-safe operational language
- high-density financial UI without cashier workflow drift

The implementation remains frontend demonstration scope. It does not perform real payment posting, settlement verification, reconciliation posting, refund approval, reversal approval, waiver approval, daily close completion, or audit persistence.

## 8. Financial Authority Matrix

| Capability | Cashier | Accountant | CMD | Admin/Super Admin |
|---|---|---|---|---|
| Collect payment | Yes, at assigned pay point | No, except explicitly authorized emergency continuity workflow | No | No |
| Issue receipt | Yes, after authorized payment collection | View/review; not primary issue workflow | View trace only | Configuration/support only |
| Reprint receipt | Request/perform if policy allows with audit note | Review/control reprint logs | Oversight visibility | Configure policy |
| Void receipt | No approval authority | Approve/reject where authorized | Oversight for critical cases | Configure authority/policy |
| Approve refund | No | Yes, where authorized | Oversight/exception visibility | Configure authority/policy |
| Approve reversal | No | Yes, where authorized | Oversight/exception visibility | Configure authority/policy |
| Approve waiver | No | Review/approve where authorized | Oversight/approval policy visibility | Configure authority/policy |
| Reconcile cashier session | No | Yes | Oversight visibility | Support/configuration only |
| Approve daily close | No | Yes | Visibility for critical exceptions | Configure close policy |
| View hospital-wide financial posture | No | Finance-control scope | Yes, executive scope | System/configuration scope |
| Manage financial configuration | No | Limited preferences only unless authorized | No, unless separately authorized | Yes |
| Manage users/roles | No | No, unless separately authorized | No, unless separately authorized | Yes |

## 9. Reconciliation Governance

Revenue reconciliation must follow these rules:

- all collections must reconcile to receipts
- all receipts must reconcile to cashier shift
- all cashier shifts must reconcile to payment method totals
- POS must reconcile to settlement/reference
- Bank Transfer must reconcile to reference/matching evidence
- Cash must reconcile to declared handover
- Department revenue must reconcile to posted receipts and service lines
- Refunds and reversals must reconcile to original receipts and correcting entries
- Waivers and discounts must reconcile to approval authority and reason
- Variance must be flagged
- Unresolved variance must block clean daily close

Reconciliation must preserve evidence. Manual reconciliation notes must include actor, timestamp, reason, and review outcome.

## 10. Financial Event Traceability

Every financial event must remain traceable across:

- patient
- invoice
- receipt
- cashier session
- department
- payment method
- settlement reference
- reversal/refund linkage
- reconciliation state
- daily close state

## 11. Variance Threshold Rules

Recommended governance/demo thresholds:

| Variance | Classification | Required Action |
|---|---|---|
| `₦0` | Matched | Eligible for clean close if no other exceptions exist. |
| `₦1-₦5,000` | Minor variance | Accountant review required. |
| `₦5,001-₦50,000` | Significant variance | Supervisor/accountant review required. |
| Above `₦50,000` | Critical variance | CMD/Admin visibility required. |
| Any repeated variance pattern | Suspicious activity | Suspicious financial activity review required. |

Variance thresholds may be configurable in production, but threshold changes must be audit-logged and controlled by authorized policy owners.

## 12. Immutable Financial Audit Requirements

Financial auditability rules:

- receipts must not be deleted
- posted payment amounts must not be edited directly
- refunds/reversals must create linked correcting entries
- waiver approval must preserve actor, time, reason, and authority
- voided receipts must remain visible with actor, reason, timestamp, and linked replacement/correction where applicable
- cashier shift records must preserve cashier identity, desk/pay point, opening time, close time, declared cash, expected cash, and variance
- all financial actions require actor, role, workstation, timestamp, request ID, and reason where applicable
- settlement verification must preserve reference/evidence used for matching
- audit records must be immutable after creation

## 13. Daily Close Governance

Daily close requires:

- all cashier sessions closed or explicitly flagged
- cash declared and matched or variance flagged
- POS settlement reviewed
- Bank Transfer references reviewed
- refunds/reversals reviewed
- waivers reviewed
- receipt voids reviewed
- unresolved exceptions listed
- accountant close summary generated
- critical exceptions routed to CMD/Admin visibility
- close approval status recorded
- close actor, role, workstation, timestamp, and reason captured

Daily close must not be marked clean while unresolved critical variance, unmatched settlement, unreviewed reversal, unapproved refund, or missing cashier session closure exists.

Close integrity rule:

Daily close approval must preserve the exact financial posture reviewed at close time.

Post-close modifications must:

- preserve correction traceability
- reopen reconciliation state where required
- generate audit-visible adjustment records

## 14. Dual Authorization Principle

High-risk financial actions may require secondary authorization.

Examples include:

- high-value refunds
- critical reversals
- large waivers
- unresolved significant variance closure
- settlement override approvals

Production implementation may require:

- secondary accountant approval
- finance supervisor approval
- CMD/Admin visibility
- immutable approval traceability

## 15. Refund, Reversal, Waiver, and Discount Governance

Refunds, reversals, waivers, and discounts are sensitive financial exceptions.

Required controls:

- original receipt/invoice must remain traceable
- correcting entry must be linked to original transaction
- actor, role, timestamp, reason, and authority must be preserved
- accountant approval must be role-authorized
- suspicious or high-value exceptions must be escalated
- self-approval of suspicious or self-originated transactions requires secondary review
- CMD/Admin visibility is required for critical exceptions based on policy thresholds

## 16. Demo Boundary

This governance specification may define target behavior before implementation.

Any frontend implementation must clearly identify demonstration data as frontend demonstration workspace data until backend APIs exist.

No implementation may claim production reconciliation, receipt auditability, refund approval, reversal approval, waiver approval, settlement verification, or daily close completion until backend APIs, persistence, audit logging, RBAC, and validation are implemented.

## 17. Production Backend Requirements

Production implementation requires:

- cashier session API
- payment posting API
- receipt audit API
- reconciliation API
- refund/reversal approval API
- waiver approval API
- settlement verification API
- daily close API
- report export API
- immutable audit logging
- RBAC enforcement
- idempotency controls
- duplicate payment prevention
- variance threshold configuration and audit
- notification/escalation workflow for critical exceptions
- export controls and report audit trail

## 18. First Deployment Priority

### Critical

- Financial Control Overview
- Cashier Session Oversight
- Revenue Reconciliation Intelligence
- Payment Verification
- Daily Close & Handover
- Financial Exceptions

### High

- Refund & Reversal Governance
- Waiver & Discount Review
- Outstanding Bills Control
- Department Revenue Control
- Audit Trail & Reports

### Low

- Financial Control Preferences

## 19. Strict Governance Rules

The Accountant Financial Control Center must not contain:

- clinical workflows
- prescription entry
- nursing documentation
- patient registration workflows
- frontline cashier collection as the primary workflow
- CMD executive command-center modules
- pharmacy inventory CRUD
- engineering infrastructure consoles
- biometric administration
- user/role administration unless separately authorized

## 20. Financial Integrity Principles

The Accountant Financial Control Center is governed by the following principles:

- no untraceable financial action
- no destructive financial mutation
- no reconciliation without evidence
- no clean close with unresolved critical variance
- no sensitive approval without authority
- no financial exception without audit visibility
- no settlement verification without reference evidence
- no financial control outside immutable auditability

## 21. Accountant Workstation Design Principles

The Accountant Financial Control Center must follow these design principles:

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
- role separation before workflow speed
- traceability before destructive correction
- close integrity before daily completion

## 22. Final Governance Verdict

This specification is:

- healthcare-finance aligned
- reconciliation-oriented
- anti-leakage focused
- auditability-focused
- authority-boundary strict
- daily-close aware
- HIS architecture aligned
- frontend implementation aligned
- production-governance ready

No engineer, designer, or AI agent should drift outside this specification without architecture and finance governance review.
