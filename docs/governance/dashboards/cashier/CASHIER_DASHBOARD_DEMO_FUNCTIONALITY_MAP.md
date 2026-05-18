# Revenue Collection Desk Demo Functionality Map

## Purpose

This document maps every implemented Revenue Collection Desk section to its frontend demonstration capability. It clarifies current demo scope, fake data, user understanding, and future backend/API needs.

Current implementation status: frontend demonstration workspace at `/cashier`. No live backend payment posting, payment gateway, receipt persistence, printer, shift/till, or reconciliation integration is connected.

## Workspace Map

| Section | Purpose | Demo Capability Shown | Key Fake Data Shown | What Cashier Can Understand | Future Backend/API Requirement | Status | Priority |
|---|---|---|---|---|---|---|---|
| Collection Overview | Daily cashier operational summary. | Summary cards, payment method split, recent transactions, quick actions, shift status. | Today's Collections `₦1.85M`, Receipts Issued `42`, Pending Payments `18`, POS `₦820K`, Bank Transfer `₦610K`, Cash `₦420K`, Shift `Open`. | Current desk collections, pending workload, payment method posture, and recent receipt activity. | Cashier dashboard summary API, cashier session API, receipt count API, payment method totals. | Implemented | Critical |
| Pending Payments | Bills awaiting cashier action. | Payment queue by patient with process payment action preview and filters. | Abba Nura, Muhammad Nura, Sani Umar, Fatima Kabir; MRNs, departments, service lines, amount due, requested by, priority, status. | Which patient bills are ready or awaiting payment and who requested the charge. | Billing queue API, invoice API, service line filters, patient lookup, pagination. | Implemented | Critical |
| Patient Bill Lookup | Fast patient/payment search. | MRN, patient name, phone, visit ID, invoice search surfaces; patient summary; active bill summary; unpaid items. | Abba Nura, MRN `0000001-9`, phone preview, pharmacy unpaid items. | How a cashier would verify patient, invoice, and unpaid items before collection. | Patient billing search API, invoice API, visit API, payment readiness rules. | Implemented | Critical |
| Process Payment | Core cashier payment execution flow. | Selected patient/invoice, bill item breakdown, payment method selector, amount received, payment reference, validation summary, receipt preview, confirm button. | Sani Umar, MRN `0000003-7`, invoice `INV-2026-093`, amount `₦25,000`, methods POS/Bank Transfer/Cash/Split Payment. | The safe sequence for verifying invoice, selecting method, entering reference, and generating receipt. | Payment posting API, idempotency, payment method validation, receipt API, audit logging. | Implemented | Critical |
| Receipt Center | Receipt generation and traceability surface. | Generated receipts, official receipt preview, receipt status, reprint readiness, receipt audit note. | Receipt numbers `RCP-2026-00091` to `RCP-2026-00094`, patient/MRN, amount, method, cashier, time, status. | Receipts are traceable and reprints/voids require controlled audit posture. | Receipt generation API, receipt search API, printer integration, reprint audit notes. | Implemented | Critical |
| Payment History | Cashier-visible transaction history. | Compact transaction rows, receipt trace action, payment method badges, status badges. | Receipt, patient, MRN, department/service, amount, method, time, verified/issued states. | Recent cashier payment records and traceability of each receipt. | Transaction history API, filters/search, pagination, receipt trace endpoint. | Implemented | High |
| Shift Management | Cashier shift accountability. | Shift control flow, active shift summary, handover note preview, supervisor review status. | Cashier `Aisha Bello`, desk `A & E / Theater Pay Point`, shift opened `07:45 AM`, collections `₦1.85M`, receipts `42`, status `Open`. | Own shift posture, close/handover readiness, and supervisor review boundary. | Cashier shift API, open/close shift workflow, handover notes, supervisor review API. | Implemented | Critical |
| Cash Drawer / Till Summary | Cash-specific accountability. | Opening balance, cash collected, expected cash, declared cash, variance, cash handover. | Opening Balance `₦50,000`, Cash Collected `₦420,000`, Expected Cash `₦470,000`, Declared Cash `₦470,000`, Variance `₦0`. | Cash drawer accountability and variance posture. | Cash drawer/till API, declaration workflow, variance rules, handover audit. | Implemented | High |
| Payment Exceptions | Controlled exception visibility. | Failed payments, duplicate alerts, unmatched transfers, voided receipt visibility, supervisor review, payment reversal request visibility. | Failed Payments `4`, Duplicate Alerts `1`, Unmatched Transfers `2`, Supervisor Review `3`; exception cards. | Exceptions are visible but cashier cannot approve sensitive financial changes. | Payment exception API, supervisor/accountant review workflow, reversal/refund approval workflow, audit trail. | Implemented | High |
| Cashier Workstation Settings | Workstation configuration preview. | Cashier profile, desk identity, printer status, default payment method, notification preferences, biometric session status, reprint note requirement. | Aisha Bello, `A & E / Theater Pay Point`, printer online, POS default, biometric session verified. | Workstation context and configuration requirements for cashier operations. | User profile API, pay-point assignment API, printer status API, preference API, session security API. | Implemented | Low |

## Cross-Workspace Demonstration Features

| Feature | Current Demo Behavior | Production Requirement |
|---|---|---|
| Sidebar-driven workspace | Implemented. Clicking a nav item switches the focused workspace. | Optional deep linking and persisted user preferences. |
| Cashier accountability strip | Implemented at top of main workspace. | Live cashier session, pay-point, supervisor, and shift state API. |
| Filters/search | UI-ready only. | Query APIs, validation, loading states, pagination, access control. |
| Payment buttons | Demonstration-only. | Authorized payment posting API and payment method validation. |
| Receipt generation | Demonstration-only preview. | Receipt persistence, numbering, print/reprint controls, audit logging. |
| Exception flagging | Demonstration-only preview. | Exception workflow API with supervisor/accountant review. |

## Demo Boundary

Implemented means the frontend demonstration exists and is presentation-ready as a visual capability preview. It does not mean production payment posting, receipt persistence, printer integration, shift/till posting, or payment gateway integration is complete.
