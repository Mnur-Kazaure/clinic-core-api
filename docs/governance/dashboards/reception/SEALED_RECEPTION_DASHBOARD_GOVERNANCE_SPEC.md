# 🔒 APPROVED RECEPTION DASHBOARD NAVIGATION

## KSH Enterprise HIS — Front Desk & Patient Intake Workspace

Architecture terminology: Reception belongs to the KSH Enterprise HIS operational platform. EMR/Clinical Records remains a clinical records subdomain and must not be used as the umbrella name for front desk, billing, pharmacy, lab, executive, or administration workflows.

### Status: APPROVED FOR DEMO IMPLEMENTATION

The Reception Dashboard should behave as:

```text id="5oqkmj"
Patient Intake
Visit Coordination
Queue Management
Appointment & Follow-Up Coordination
Front Desk Operations
```

NOT:

* cashier dashboard
* clinical dashboard
* inpatient ward console
* pharmacy console
* CMD governance dashboard

---

# ✅ APPROVED RECEPTION SIDEBAR STRUCTURE

```text id="rl7ahd"
Reception Dashboard
├── Overview
├── Patient Registration
├── Patient Search
├── Start Visit
├── OPD Queue
├── Follow-Up Appointments
├── Appointment Scheduling
├── Visit History
├── Emergency Intake
└── Reception Settings
```

---

# 1. 🏠 Overview

## Purpose

Provides front-desk operational visibility.

## Receptionist Can See

```text id="7tdj6z"
Queue totals
Waiting patients
Emergency flagged patients
Recent registrations
Recent activity
Assigned desks
Daily visit summary
```

## Approved Widgets

```text id="i4w3iv"
Queue Summary
Recent Registrations
Emergency Alerts
Recent Activity
Quick Actions
```

## Critical for First Demo

✅ YES — REQUIRED

---

# 2. 👤 Patient Registration

## Purpose

Handles new patient onboarding and demographic capture.

## Receptionist Can See

```text id="owrqf2"
New patient form
MRN generation
Demographics
Contact information
Next-of-kin
Basic patient search validation
```

## Approved Subsections

```text id="p1v1rt"
Patient Registration
├── Register New Patient
├── Demographic Capture
├── Next-of-Kin Details
└── Registration Audit
```

## Critical for First Demo

✅ YES — HIGHEST PRIORITY

---

# 3. 🔍 Patient Search

## Purpose

Allows patient lookup before visit creation.

## Receptionist Can See

```text id="r8k7v7"
MRN search
Phone number search
Visit history lookup
Patient demographics
Previous visits
```

## Approved Subsections

```text id="z6kt1k"
Patient Search
├── Search Patient
├── Patient Profile Summary
├── Previous Visits
└── Active Visits
```

## Critical for First Demo

✅ YES — REQUIRED

---

# 4. 🩺 Start Visit

## Purpose

Creates outpatient visit and routes patient into workflow.

## Receptionist Can See

```text id="14ak6i"
Department assignment
Doctor assignment
Visit type
Priority level
Visit initiation
```

## Approved Subsections

```text id="mg8m8k"
Start Visit
├── New OPD Visit
├── Assign Department
├── Assign Doctor
├── Visit Priority
└── Visit Intake Summary
```

## Critical for First Demo

✅ YES — HIGHEST PRIORITY

---

# 5. 🧾 OPD Queue

## Purpose

Monitors active outpatient visit movement.

## Receptionist Can See

```text id="9g1w17"
Waiting patients
Patients in consultation
Lab-requested visits
Completed visits
Delayed visits
Queue duration
```

## Approved Subsections

```text id="odnnv5"
OPD Queue
├── Waiting Queue
├── In Consultation
├── Lab Requested
├── Pharmacy Pending
├── Payment Pending
└── Completed Visits
```

## Critical for First Demo

✅ YES — HIGHEST PRIORITY

---

# 6. 🔄 Follow-Up Appointments

## Purpose

Handles return-visit continuity and follow-up coordination.

## Receptionist Can See

```text id="jlwm55"
Upcoming follow-ups
Missed follow-ups
Doctor follow-up schedules
Return visit tracking
```

## Approved Subsections

```text id="vd7m3g"
Follow-Up Appointments
├── Upcoming Follow-Ups
├── Missed Follow-Ups
├── Follow-Up Check-In
└── Follow-Up Queue
```

## Critical for First Demo

✅ YES — REQUIRED

---

# 7. 📅 Appointment Scheduling

## Purpose

Manages clinic appointment coordination.

## Receptionist Can See

```text id="f0u2pq"
Clinic schedules
Doctor availability
Booked appointments
Rescheduled appointments
Appointment calendar
```

## Approved Subsections

```text id="8t4x7s"
Appointment Scheduling
├── Book Appointment
├── Reschedule Appointment
├── Clinic Calendar
├── Doctor Availability
└── Appointment History
```

## Critical for First Demo

⚠ OPTIONAL

---

# 8. 📖 Visit History

## Purpose

Provides historical patient visit visibility.

## Receptionist Can See

```text id="20k9gv"
Past visits
Visit dates
Departments visited
Visit outcomes
```

## Approved Subsections

```text id="u6w6q4"
Visit History
├── Previous Visits
├── Visit Timeline
├── Department History
└── Visit Outcome Summary
```

## Critical for First Demo

⚠ OPTIONAL

---

# 9. 🚨 Emergency Intake

## Purpose

Provides rapid patient intake for A&E routing.

## Receptionist Can See

```text id="r5kh04"
Emergency registration
Emergency prioritization
Fast-track routing
Emergency queue alerts
```

## Approved Subsections

```text id="aev7gx"
Emergency Intake
├── Register Emergency Case
├── Emergency Queue
├── Priority Flagging
└── Emergency Routing
```

## Critical for First Demo

⚠ IMPORTANT IF A&E DEMO IS REQUIRED

---

# 10. ⚙ Reception Settings

## Purpose

Allows receptionist-level workspace preferences.

## Approved Subsections

```text id="3vb64s"
Reception Settings
├── Profile
├── Notification Preferences
└── Desk Preferences
```

## Critical for First Demo

❌ LOW PRIORITY

---

# 🚫 RECEPTION DASHBOARD MUST NOT CONTAIN

```text id="wif0sv"
Clinical consultation forms
Prescription entry
Lab result approval
Pharmacy dispensing
Cashier reconciliation
Financial audit tools
CMD governance modules
Engineering/system monitoring
```

These belong to other dashboards.

---

# ✅ FIRST DEMO PRIORITY MATRIX

# MUST EXIST BEFORE PRESENTATION

```text id="k7p0lg"
Overview
Patient Registration
Patient Search
Start Visit
OPD Queue
Follow-Up Appointments
```

---

# SHOULD EXIST IF TIME ALLOWS

```text id="2c5l3x"
Emergency Intake
Appointment Scheduling
Visit History
```

---

# 🔒 FINAL ARCHITECTURAL VERDICT

This Reception Dashboard is now:

✅ hospital front-desk aligned
✅ workflow-oriented
✅ outpatient-ready
✅ follow-up-ready
✅ scalable for real HIS implementation
✅ enterprise-separation compliant
✅ demo-presentation ready

This structure is professionally suitable for Specialist Hospital Kazaure demonstration purposes and future production evolution.
