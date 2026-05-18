# CMD Dashboard Demo Functionality Map

## Purpose

This document maps the implemented CMD frontend demonstration workspace to the approved governance sections and subsections. It is written for engineers, auditors, reviewers, and AI agents who need to understand what the CMD demo currently shows, what remains demonstration-only, and what backend integration is required for production.

Current implementation status: sidebar-driven frontend demonstration workspace using local data in `clinic-app/src/app/cmd/page.tsx`. No live backend, biometric device, payment gateway, audit service, reporting service, or database integration is connected yet.

## Interaction Model

| Capability | Current Demo Behavior | Backend Requirement |
|---|---|---|
| Sidebar-driven workspace | Implemented. CMD clicks a section/subsection and the main workspace switches to that focused view. | Persist user preferences if needed; optionally route-deep-link selected subsection later. |
| Active section/subsection state | Implemented with local state. Default view is `Executive Overview -> Hospital Snapshot`. | No backend required for current interaction. |
| Demo badges | Implemented in focused demo areas to clarify frontend demonstration state. | Replace or augment with live data provenance after API integration. |
| Filters/search controls | UI-ready but not functional. | Connect to query APIs, validation, pagination, access rules, and audit logging. |
| Action/export buttons | Demonstration-only visual affordances. | Connect to authorized backend workflows and immutable audit trails. |

## Executive Overview

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Hospital Snapshot | Hospital command summary. | Hospital status, emergency pressure, bed utilization, critical signals, active departments, executive KPI cards, activity feed, trust signals. | Overall hospital posture at a glance. | Hospital summary API, department census, bed, revenue, staff, and alert aggregation. | Implemented | Critical |
| Critical Alerts | Escalation visibility. | Alert-focused preview with CMD risk signals. | Which signals require executive attention. | Alerting API, severity rules, acknowledgement workflow, audit trail. | Implemented | Critical |
| Operational KPIs | Executive KPI tracking. | KPI cards and telemetry-style executive signals. | Current operational performance and movement. | KPI aggregation API and historical metrics. | Implemented | High |
| Daily Executive Summary | Daily briefing. | Executive activity/timeline preview. | Day-level hospital summary for leadership review. | Daily summary service, report generation, sign-off workflow. | Implemented | High |
| Operational Systems Status | Operational systems posture summary. | Frontend operational-systems preview. | Whether the hospital-facing platform capabilities appear operational from CMD perspective. | Health check API, uptime monitoring, incident status feed. | Placeholder | High |

## Hospital Operations

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Patient Flow Overview | Patient movement oversight. | Focused operational intelligence preview with patient flow trend. | Bottlenecks and patient movement pressure. | Visit, queue, triage, consultation, lab, pharmacy, and discharge APIs. | Placeholder | Critical |
| Admission & Discharge Monitoring | Inpatient movement oversight. | Admission/discharge posture preview. | Admission load and discharge clearance risk. | Admission, ward, bed, discharge, billing clearance APIs. | Placeholder | Critical |
| Bed & Ward Utilization | Bed capacity oversight. | Ward utilization signal preview. | Bed pressure and ward occupancy posture. | Bed registry, ward census, transfer, and occupancy APIs. | Placeholder | Critical |
| Emergency Monitoring | A&E pressure oversight. | Emergency pressure signal preview. | Emergency load and escalation need. | Emergency visit, triage acuity, admission request, and staffing APIs. | Placeholder | High |
| Department Performance | Department performance oversight. | Department-level operational preview. | Which departments are stable or under pressure. | Department activity, SLA, service volume, and outcome APIs. | Placeholder | High |
| Follow-Up Compliance | Continuity-of-care oversight. | Follow-up compliance preview. | Whether patient follow-up pathways are being honored. | Appointment, visit outcome, follow-up booking, and no-show APIs. | Placeholder | Medium |

## Financial Intelligence

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Revenue Overview | Hospital-wide financial command summary. | Total Revenue Today `NGN 8.42M`, POS `NGN 3.62M`, Bank Transfer `NGN 2.88M`, Cash `NGN 1.92M`, Pharmacy Revenue `NGN 2.14M`, Outstanding Bills `NGN 1.18M`, Refund/Waiver Exposure `NGN 86K`, Total Receipts `184`. | Daily revenue posture, payment method split, top revenue departments, and financial exposure. | Revenue aggregation API, receipt API, department/service-line revenue API, payment method reconciliation. | Implemented | Critical |
| Cashier Collections | Cashier-by-cashier collection performance. | Aisha Bello, Musa Abdullahi, Hauwa Sani, Ibrahim Lawal, and Maryam Ali collections by location and payment method; filters/search UI. | Which cashier/location collected what, shift state, receipt count, variance posture, and last receipt time. | Cashier shift API, collections API, payment method totals, variance detection, filters/search. | Implemented | Critical |
| Payment Traceability | Transaction-level receipt/payment audit trail. | Receipt rows with patient, MRN, department, service line, requested by, cashier, payment method, amount, reference, receipt time, and verified/matched state. | Every visible payment can be traced to cashier, patient, department, service, and reference. | Transaction API, receipt API, MRN lookup, payment gateway/bank matching, audit logging. | Implemented | Critical |
| Department Revenue | Department/service-line revenue ranking. | Pharmacy `NGN 2.14M`, Laboratory `NGN 1.38M`, OPD/GOPD `NGN 1.22M`, A&E `NGN 960K`, Radiology `NGN 890K`, Maternity `NGN 620K`, Theatre `NGN 540K`, Pediatrics `NGN 310K`. | Revenue contribution by department and service line. | Department revenue API, service catalog integration, reporting aggregation. | Implemented | High |
| Revenue Reconciliation Intelligence | Executive reconciliation and variance detection. | Total Collections `NGN 8.42M`, Reconciled Amount `NGN 8.31M`, Variance `NGN 110K`, Matched Receipts `176/184`, Unmatched Transactions `8`, Suspicious Adjustments `3`, Pending Cashier Closures `2`; cashier matrix, payment method reconciliation, department reconciliation, risk signals, guided review. | Whether every naira is traceable, which cashier/location requires review, and where settlement or receipt variances exist. | Reconciliation API, receipt matching, POS/bank settlement ingestion, cashier closure workflow, adjustment audit trail. | Implemented | Critical |
| Outstanding Bills | Unpaid balance visibility. | Outstanding bills panel with inpatient, pharmacy, lab, discharge clearance, aging, and patient preview. | Unpaid balances and pending financial clearance exposure. | Billing API, invoice API, patient balance API, discharge clearance workflow. | Implemented | High |
| Refund & Waiver Audit | Sensitive financial exception oversight. | Refund requests, approved/rejected refunds, waivers, discounts, adjustment history, suspicious adjustment signals. | Whether controlled financial exceptions require review. | Refund/waiver workflow API, approval rules, audit trail, exception reporting. | Implemented | High |
| Pharmacy Revenue & Traceability | Pharmacy-specific financial visibility. | Pharmacy revenue today, dedicated pharmacy cashier, receipts, dispensing unit revenue, voided receipts, high-value medicine transactions, method split. | Pharmacy as a financial hub, with receipt and dispensing traceability. | Pharmacy dispensing API, pharmacy cashier API, medicine transaction API, void/refund audit. | Implemented | Critical |

## Pharmacy & Supply Governance

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Supply Approval Queue | Approval oversight. | Supply request signal preview. | Requests awaiting authority. | Approval workflow API and role-based approval rules. | Placeholder | High |
| Departmental Requests | Department request visibility. | Department commodity request preview. | Which departments are requesting supplies. | Department request API and stock catalog integration. | Placeholder | High |
| Dispensing Unit Requests | Dispensing unit governance. | Dispensing request preview. | Demand from pharmacy dispensing units. | Dispensing unit request API. | Placeholder | High |
| Pharmacy Store Oversight | Store-level stock posture. | Pharmacy store oversight preview. | Store risk and stock posture. | Stock ledger, store issue, receipt, and adjustment APIs. | Placeholder | High |
| Stock Movement Audit | Movement traceability. | Stock movement audit preview. | Whether stock movement can be traced. | Inventory ledger API and immutable audit trail. | Placeholder | High |
| Critical Stock Alerts | Stockout risk oversight. | Critical stock alert preview. | Which items require urgent attention. | Stock threshold API and alerting service. | Placeholder | High |
| High-Risk Commodity Monitoring | Controlled commodity oversight. | High-risk commodity preview. | Sensitive commodities needing governance. | Controlled item registry, issue approvals, and audit trail. | Placeholder | High |
| Supply Consumption Analytics | Supply trend oversight. | Consumption analytics preview. | Usage patterns and abnormal consumption. | Consumption analytics API and historical stock data. | Placeholder | Medium |
| Approval History | Approval traceability. | Approval history preview. | Who approved what and when. | Approval audit API. | Placeholder | High |
| Emergency Supply Requests | Urgent supply escalation. | Emergency request preview. | Urgent supply risk requiring CMD visibility. | Emergency request workflow API and escalation rules. | Placeholder | High |

## Staff Governance

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Attendance Intelligence | Staff attendance traceability. | Expected Staff `142`, Staff On Duty `126`, Clock-Ins Today `118`, Late Arrivals `3`, Absent Staff `2`, Early Departures `1`, Attendance Compliance `91%`; staff rows show name, staff ID, phone, department, role, shift, clock-in/out, status, lateness, device, and review state. | Who clocked in, when, where, whether late/absent/early departure, and what needs review. | Attendance API, staff directory API, biometric event ingestion, filters/search, pagination, export, audit logging. | Implemented | Critical |
| Biometric Monitoring | Biometric infrastructure and event monitoring. | Active Devices `8/8`, Last Sync `11:42 AM`, Events Captured Today `118`, Failed Attempts `4`, Unmatched Identities `2`, Sync Latency `12 sec`, Offline Devices `0`, Coverage `94%`; device health grid, event stream, risk panel, workflow strip. | Whether devices are online, events are syncing, and unmatched/failed attempts exist. | Biometric device API, sync event API, identity matching service, device status monitoring. | Implemented | Critical |
| Shift Compliance | Roster coverage and shift posture. | Overall Shift Compliance `91%`, Morning `88%`, Afternoon `96%`, Night `93%`, Late Arrival Impact `3 departments`, Understaffed Units `2`, Supervisor Reviews `4`, Roster Exceptions `6`; shift windows, department compliance, exceptions, timeline. | Whether departments are covered according to roster and which shift windows need review. | Roster API, shift assignment API, attendance-rule engine, supervisor review workflow. | Implemented | Critical |
| Workforce Analytics | Executive workforce trends and pressure signals. | Departments Covered `10/12`, Workforce Pressure `Moderate`, Exception Pattern `13`, Understaffed Units `2`, Attendance Trend `+8%`, Overtime Risk `Medium`, Coverage Stability `91%`, Review Required `4 units`; trend chart, comparison, exception pattern, risk forecast, CMD insights. | Workforce trends, department pressure, exception concentrations, and future risk posture. | Workforce analytics API, historical attendance data, forecasting model, workload integration. | Implemented | High |
| Department Staffing Posture | Department-by-department staffing posture. | All 12 departments: GOPD, A&E, Specialist Clinics, Maternity, Pediatrics, Gynecology, Male Ward, Female Ward, Theatre, Laboratory, Radiology, Pharmacy; required staff, on-duty staff, coverage percentage, status, risk, and CMD visibility priority. | Which departments are covered, under pressure, or understaffed. | Department staffing API, roster integration, real-time attendance, escalation workflow. | Implemented | Critical |

## Audit & Compliance

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| User Activity Audit | User action traceability. | User activity audit preview. | Which users are active and what actions require oversight. | Audit event API with actor, role, timestamp, entity, IP/session metadata. | Placeholder | Critical |
| Patient Record Access Audit | Patient access traceability. | Patient record access preview. | Who accessed patient records and whether access looks appropriate. | Patient access audit API and consent/privacy rules. | Placeholder | Critical |
| Financial Audit Trail | Financial action traceability. | Financial audit preview. | Financial events requiring governance review. | Payment, refund, adjustment, receipt, and reconciliation audit APIs. | Placeholder | Critical |
| Clinical Change History | Clinical record change visibility. | Clinical change preview. | Whether clinical changes are traceable. | Clinical audit API with before/after values and authorization metadata. | Placeholder | High |
| Login & Session Audit | Authentication traceability. | Session/login preview. | Login/logout and session anomalies. | Auth/session audit API, IP/device logging. | Placeholder | Critical |
| Permission Change Audit | Authorization change traceability. | Permission change preview. | Changes to role/access boundaries. | RBAC audit API and approval workflow. | Placeholder | High |
| Suspicious Activities | Risk signal escalation. | Suspicious activity preview. | Events requiring compliance attention. | Risk scoring, anomaly rules, compliance escalation API. | Placeholder | Critical |
| Compliance Reports | Compliance reporting. | Compliance report preview. | Governance evidence readiness. | Report API, export service, retention policy. | Placeholder | Medium |

## Executive Reports

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Operational Reports | Operational report preview. | Operational report rows. | Operational reporting scope. | Report generation API and scheduled report jobs. | Placeholder | High |
| Financial Reports | Financial report preview. | Financial report rows. | Financial reporting scope. | Financial report API and reconciliation data source. | Placeholder | High |
| Audit Reports | Audit report preview. | Audit report rows. | Audit evidence scope. | Audit report API and export service. | Placeholder | High |
| Department Performance Reports | Department performance report preview. | Department report rows. | Department accountability reporting. | Department metrics API and report export. | Placeholder | Medium |
| Executive Export Center | Export readiness preview. | Export center preview. | Future export capability for CMD briefings. | Secure export API, authorization, watermarking, audit logging. | Placeholder | Medium |

## Executive Settings

| Subsection | Purpose | Demo Capability and Key Fake Data | What CMD Can Understand | Future Backend/API Requirement | Demo Status | Priority |
|---|---|---|---|---|---|---|
| Dashboard Preferences | Dashboard preference preview. | Preference preview only. | Future personalization scope. | User preference API. | Placeholder | Low |
| Notification Preferences | Notification preference preview. | Preference preview only. | Future alert delivery controls. | Notification API and delivery channels. | Placeholder | Low |
| Report Preferences | Report preference preview. | Preference preview only. | Future report formatting and schedule preferences. | Report preference API. | Placeholder | Low |
| Executive Profile | CMD profile preview. | Profile preview only. | Executive profile context. | User profile API and access-controlled update workflow. | Placeholder | Low |

## Demo Boundary

Implemented means the frontend demonstration exists and is presentation-ready as a visual capability preview. It does not mean the production backend, database, integrations, workflows, exports, or immutable audit trails are complete.

Production implementation requires API contracts, database models, authorization checks, validation, pagination, filtering, audit logging, monitoring, and deployment governance before any view should be considered live operational software.
