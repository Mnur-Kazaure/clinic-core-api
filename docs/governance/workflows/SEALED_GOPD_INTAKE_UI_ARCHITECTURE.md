# SEALED GOPD INTAKE UI ARCHITECTURE

Version: v1.0
Status: Sealed UI/UX architecture target before frontend implementation
Audience: architects, engineers, designers, clinical operations reviewers, auditors, and AI agents

## 1. Purpose

This document defines the enterprise UI/UX architecture for the GOPD Intake Workspace.

This is not an implementation plan and not a React component specification. It governs how the future GOPD Intake interface should behave visually, operationally, and clinically before frontend redesign begins.

GOPD Intake is high-volume outpatient intake infrastructure, patient movement workspace, intake/routing workstation, and operational continuity system inside KSH Enterprise HIS.

## 2. Workspace Identity

Approved names:

- GOPD Intake Workspace
- GOPD Operational Intake
- General Outpatient Intake

Rejected names:

- Reception Dashboard
- Front Desk Dashboard
- Registration Page
- Generic Reception

The name must communicate department-specific intake ownership without implying independent patient records or isolated department systems.

## 3. Workspace Philosophy

The GOPD Intake Workspace must prioritize:

- intake-first workflow
- queue-oriented operations
- fast scan efficiency
- minimal registration friction
- patient continuity preservation
- reassignment safety
- operational speed
- second-nature adoption
- active visit awareness
- duplicate registration prevention
- governed routing and escalation

The system should help staff correct patient movement quickly without losing the patient's shared identity, MRN, active visit, EMR / Clinical Records linkage, billing context, or audit trail.

## 4. Workspace Layout Architecture

### Left Sidebar

The left sidebar should provide:

- intake navigation
- queue switching
- routing tools
- reassignment/referral actions
- emergency escalation access
- follow-up arrival access
- intake audit access

The sidebar should be compact, operational, and built for repeated daily use. It should not feel like a marketing navigation panel or executive command-center sidebar.

Approved navigation:

```text
GOPD Intake Workspace
|-- Intake Overview
|-- Patient Lookup
|-- Patient Registration
|-- Start OPD Visit
|-- GOPD Queue
|-- Triage Routing
|-- Doctor Assignment
|-- Reassignment / Rerouting
|-- Internal Referral
|-- Emergency Escalation
|-- Follow-Up Arrival
`-- Intake Audit Trail
```

### Top Operational Bar

The top operational bar should expose live intake posture:

- active intake load
- waiting patients
- triage pressure
- emergency escalation indicators
- follow-up arrivals
- active referrals
- reassignment review count
- current desk / department context

This bar should be compact and operational, not a hero banner.

### Main Workspace

The center workspace renders the selected intake view:

- queue views
- patient lookup results
- patient registration form
- start OPD visit flow
- routing flows
- reassignment workflow
- referral workflow
- escalation workflow
- follow-up arrival workflow

Main workspace content must switch by navigation selection and must not become a long scrolling collection of every intake function.

### Right Context Panel

The right context panel should remain available when a patient or visit is selected.

It should show:

- selected patient summary
- MRN
- active visit
- alerts
- previous visits
- active follow-up linkage
- referral/escalation status
- current queue state
- duplicate/active visit warning

The right panel is critical for preventing duplicate registration, lost visits, and patient context fragmentation.

## 5. Visual Design Direction

The GOPD Intake Workspace should feel:

- operational
- fast
- clinical
- structured
- calm
- efficient
- high-throughput
- non-cinematic
- non-financial
- patient-flow focused

Use:

- clean clinical surfaces
- calm blue/cyan accents
- controlled urgency colors
- queue-focused hierarchy
- operational density
- clear row/card separation
- readable patient identifiers
- compact filter/search controls

Avoid:

- CMD cinematic atmosphere
- Accountant finance workstation feel
- oversized hero sections
- marketing cards
- decorative gradients
- excessive glow
- dashboard widgets unrelated to intake

## 6. Queue Design Principles

GOPD queue surfaces must provide fast scan visibility for:

- patient name
- MRN
- arrival time
- waiting time
- visit state
- triage state
- emergency flag
- follow-up flag
- doctor assignment
- reassignment/referral status
- active visit warning
- department routing context

Queue rows should support quick differentiation between:

- new arrival
- waiting triage
- triaged
- waiting doctor
- assigned doctor
- emergency escalation
- follow-up arrival
- reassignment pending
- internal referral pending

Queue surfaces must be compact enough for high-volume use while preserving patient safety and readability.

## 7. Reassignment / Referral UX

Reassignment and referral are high-risk patient movement workflows. They must be visible, easy to initiate when needed, and audit-safe.

### Wrong Department Correction Flow

Use for operational mistakes before consultation:

```text
Select patient
-> Open Reassignment / Rerouting
-> Choose target department/queue
-> Enter reason
-> Confirm movement
-> Preserve source and target queue trace
```

The interface must prevent silent queue movement.

### Internal Referral Flow

Use for patient movement to another department or specialty:

```text
Select patient
-> Open Internal Referral
-> Choose target department/specialty
-> Select reason/category
-> Add supporting note where required
-> Route to target department intake/queue
```

The UX must distinguish internal referral from simple operational reassignment.

### Emergency Escalation Flow

Use when urgent condition is discovered:

```text
Select patient
-> Open Emergency Escalation
-> Confirm emergency reason
-> Mark urgent priority
-> Route to A&E intake/triage
-> Preserve GOPD source context
```

Emergency escalation should be visually urgent but not chaotic. It must require reason capture and preserve audit trace.

### Admission Conversion Visibility

Admission conversion is usually a clinical decision, not GOPD intake ownership.

The GOPD workspace may show:

- admission requested state
- admission handoff status
- receiving ward/bed pending state where available

It must not let GOPD intake staff make clinical admission decisions.

## 8. Second-Nature Adoption UX

The workspace should anticipate real hospital conditions:

- patient is in the wrong department
- patient is in the wrong queue
- patient needs specialist care
- urgent condition is discovered at intake
- follow-up patient arrives at GOPD
- patient already has an active visit
- patient cannot provide complete details immediately

The UI should guide staff toward the correct next action without forcing duplicate registration.

Core adoption rule:

```text
Correct the patient journey without fragmenting the patient record.
```

## 9. Mobile / Compressed Strategy

The GOPD Intake Workspace is desktop-first and laptop-optimized.

Responsive behavior should support:

- queue compaction
- stacked patient context panel on tablet/mobile
- persistent patient identity visibility
- collapsible sidebar on smaller screens
- compressed operational bar
- readable queue rows without horizontal overflow

On smaller screens, the priority order is:

1. patient identity
2. active visit / queue state
3. emergency and triage status
4. primary intake action
5. reassignment/referral/escalation context

## 10. Accessibility And Safety Requirements

- MRN and patient identity must remain readable.
- Emergency status must not depend on color alone.
- Reassignment/referral confirmation must include target and reason.
- Search inputs must have clear labels.
- Queue rows must support keyboard navigation in production.
- Critical actions must not be hidden behind hover-only interactions.

## 11. Demo Vs Production Boundary

This document defines UI/UX architecture before frontend implementation.

Frontend demonstrations may simulate queues, referrals, reassignment, escalation, and active visit warnings, but must not imply production backend behavior exists until routing APIs, state machine enforcement, authorization, and audit logging are implemented.

## 12. Governance Constraint

No engineer, designer, or AI agent may implement GOPD Intake as a generic reception dashboard, isolated patient system, or page of unrelated cards.

GOPD Intake must be implemented as a governed high-volume patient movement workspace inside unified KSH Enterprise HIS.

