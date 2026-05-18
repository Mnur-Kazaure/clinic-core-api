# HIS Governance Documentation

This folder contains product, architecture, security, integration, workflow, compliance, and dashboard governance documents for the HIS platform.

Governance documents define approved system behavior, ownership boundaries, implementation constraints, and future integration requirements. They are intended to prevent documentation drift, role-boundary drift, and AI-agent implementation drift.

## Folder Structure

| Folder | Purpose |
|---|---|
| `dashboards/` | Sealed dashboard governance specs and dashboard implementation notes |
| `workflows/` | Healthcare workflow governance for outpatient, inpatient, follow-up, billing, pharmacy, lab, admissions, and discharge flows |
| `architecture/` | System architecture decisions, module boundaries, routing principles, and clean architecture guidance |
| `security/` | Authentication, authorization, RBAC, audit trail, patient data protection, and production security governance |
| `integrations/` | Biometric, payment, settlement, messaging, reporting, and external system integration governance |
| `compliance/` | Audit evidence, traceability, reporting controls, record access, retention, and institutional compliance governance |

Implementation must follow the relevant sealed governance documents unless architecture review approves a revised version.

Core platform terminology is governed by `architecture/SEALED_HIS_DOMAIN_ARCHITECTURE.md`: HIS is the parent enterprise platform, and EMR / Clinical Records is a clinical subdomain inside HIS.
