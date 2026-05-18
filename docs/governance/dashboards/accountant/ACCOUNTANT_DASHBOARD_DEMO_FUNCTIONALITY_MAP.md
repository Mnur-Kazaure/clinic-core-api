# ACCOUNTANT DASHBOARD DEMO FUNCTIONALITY MAP

## Purpose

This document maps the implemented Accountant Financial Control Center frontend demonstration to its approved capability, governance purpose, fake-data surface, and future backend/API requirements.

Architecture placement:

```text
KSH Enterprise HIS
→ Revenue & Financial Governance Domain
→ Accountant Financial Control Center
```

HIS is the parent enterprise platform. EMR / Clinical Records is a clinical subdomain inside HIS and is not the parent product for accountant, cashier, CMD, audit, or revenue workflows.

## Implementation Status

| Item | Status |
|---|---|
| Route | Implemented at `/accountant` |
| Interaction model | Sidebar-driven focused workspace |
| Data source | Frontend demonstration data |
| Backend/API integration | Not connected |
| Real reconciliation | Not implemented |
| Real approval execution | Not implemented |
| Real daily close | Not implemented |
| Financial posting | Not implemented |

## Implemented Premium Capability Layer

| Capability | Demo Capability Shown | Governance Meaning |
|---|---|---|
| Operational finance state | Finance state, close integrity, audit mode indicators | Gives accountant immediate financial-control posture |
| Micro-visualization layer | Metric bars, reconciliation movement, cashier variance heat, department revenue bars | Communicates financial intelligence without decorative charting |
| Guided reconciliation review | Step-based reconciliation panel and demo-only action buttons | Demonstrates evidence-first reconciliation workflow |
| Variance indicators | Outstanding variance, cashier variance, method variance, critical variance status | Prioritizes leakage and mismatch visibility |
| Payment distribution indicators | POS, Bank Transfer, Cash split | Shows settlement posture by authorized collection method |
| Close readiness posture | Blocked close, pending exceptions, checklist, accountant notes preview | Reinforces no clean close with unresolved critical variance |
| Audit-safe language | Immutable trace, evidence review, CMD/Admin visibility, secondary approval | Prevents casual or destructive financial-action framing |

## Workspace Functionality Map

| Workspace | Purpose | Demo Capability Shown | Key Fake Data Shown | What Accountant Can Understand | Future Backend/API Requirement | Status | Priority |
|---|---|---|---|---|---|---|---|
| Financial Control Overview | High-level accountant financial-control posture | Total collections, reconciled amount, variance, pending reviews, unmatched transfers, refund exposure, daily close status, critical exceptions | `₦8.42M` collections, `₦8.31M` reconciled, `₦110K` variance, `11` pending reviews, `3` critical exceptions | Whether finance operations are matched, blocked, or under review | Finance overview API, reconciliation summary API, exception feed | Implemented | Critical |
| Cashier Session Oversight | Cashier-by-cashier session control | Cashier matrix, shift status, collections, expected cash, declared cash, variance, receipt count, review state, variance heat indicators | Aisha Bello, Musa Abdullahi, Hauwa Sani, Ibrahim Lawal, Maryam Ali; A&E critical variance | Which cashier sessions are clean, pending, or high risk | Cashier session API, shift close API, till declaration API | Implemented | Critical |
| Revenue Reconciliation Intelligence | Reconciliation intelligence center | Total collections, matched receipts, unmatched transactions, suspicious adjustments, pending closures, source matrix, guided reconciliation | `176 / 184` matched receipts, `8` unmatched transactions, `3` suspicious adjustments | Which sources, cashiers, departments, and payment methods need reconciliation evidence | Reconciliation API, settlement matching API, receipt audit API | Implemented | Critical |
| Payment Verification | Transaction verification desk | Filters/search UI, receipt rows, patient/MRN, department, amount, method, reference, settlement state, verification state | Receipts `RCP-2026-00091` to `RCP-2026-00108` | Whether receipt/payment references look matched, reviewed, or escalated | Payment verification API, receipt lookup API, settlement reference API | Implemented | Critical |
| Refund & Reversal Governance | Sensitive approval governance | Controlled request queue, risk level, original receipt, amount, requested by, reason, approval posture, visual-only buttons | Duplicate charge, high-value cash correction, cancelled imaging service | Which refund/reversal requests require review, secondary approval, or CMD visibility | Refund approval API, reversal approval API, dual authorization workflow | Implemented | High |
| Waiver & Discount Review | Financial concession governance | Waiver/discount request cards, approval source, patient billing impact, justification, policy compliance | Social welfare concession, staff dependent discount, CMD-visible hardship waiver | Whether concessions are compliant, policy-pending, or high risk | Waiver approval API, discount policy API, concession audit trail | Implemented | High |
| Outstanding Bills Control | Unpaid balance governance | Outstanding KPIs and patient outstanding preview | Total outstanding `₦1.18M`, inpatient pending, discharge holds, pharmacy/lab pending, aging exposure | Which balances and discharge holds require financial-control review | Outstanding bills API, discharge clearance API, aging report API | Implemented | High |
| Department Revenue Control | Department/service-line revenue control | Revenue leaderboard, method split, transaction count, variance posture, traceability state, micro-bars | Pharmacy `₦2.14M`, Laboratory `₦1.38M`, OPD/GOPD `₦1.22M`, A&E `₦960K` | Which departments generate revenue and which show variance or traceability risk | Department revenue API, service-line revenue API, variance API | Implemented | High |
| Daily Close & Handover | Financial lockdown workflow | Close checklist, close readiness state, handover summary, accountant notes preview, blocked close posture | Close readiness blocked, `4 / 5` cashier sessions reviewed, `₦110K` unresolved variance | Whether daily close is clean, pending, blocked, or escalated | Daily close API, handover API, close approval workflow | Implemented | Critical |
| Financial Exceptions | Risk and anomaly control | Duplicate payments, voided receipts, delayed settlements, repeated variance, unmatched transfers, suspicious adjustments | `2` duplicate payments, `3` voided receipts, `4` delayed settlements, `3` suspicious adjustments | Which anomalies threaten close integrity or require escalation | Exception API, anomaly detection feed, escalation workflow | Implemented | Critical |
| Audit Trail & Reports | Immutable finance trace center | Activity timeline, actor trace rows, export-ready report cards | Receipt issued, cash variance detected, settlement evidence matched, critical variance escalated | Whether actions remain traceable by actor, receipt, evidence, and report state | Audit trail API, report export API, immutable event store | Implemented | High |
| Financial Control Preferences | Workstation configuration preview | Profile, approval preferences, report preferences, workstation controls, variance threshold preview, notification preferences | Amina Yusuf profile, secondary authorization, threshold preview | Which controls are intended for future accountant workstation configuration | Preferences API, RBAC-backed threshold settings, notification config API | Implemented | Low |

## Financial Authority Semantics

| Role | Primary Financial Responsibility |
|---|---|
| Cashier | Collect frontline payments and issue receipts at assigned pay points |
| Accountant | Verify, reconcile, approve where authorized, close, and review exceptions |
| CMD | Oversee institutional financial posture and interrogate executive financial intelligence |
| Admin/Super Admin | Configure policies, roles, and system controls where authorized |

The Accountant Financial Control Center is operational-financial governance infrastructure, not a cashier workstation and not an executive CMD intelligence console.

## Demo Boundary

All values, charts, rows, indicators, approval states, reconciliation states, report states, and close states are frontend demonstration data. They are suitable for workflow validation and contract demonstration, but they must not be described as live financial processing.
