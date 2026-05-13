from __future__ import annotations
# app/schemas/cmd_oversight.py - CMD Intelligence Schemas

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class ExecutiveStatsResponse(BaseModel):
    daily_revenue_minor: int
    patient_throughput: int
    total_patients_count: int
    staff_compliance_count: int
    system_health: str
    opd_active_count: int
    anc_active_count: int
    maternity_active_count: int
    latest_attendance: List[dict]
    admissions_today: int
    discharges_today: int
    outstanding_payments_minor: int
    bed_occupancy_percent: int
    emergency_alerts_count: int
    pending_approvals_count: int
    suspicious_activities_count: int
    long_waiting_count: int
    delayed_consultations_count: int
    doctor_workload_percent: int
    follow_ups_today: int
    missed_follow_ups: int
    chronic_monitoring_count: int

class ActivityFeedItem(BaseModel):
    id: UUID
    event_type: str
    actor_id: Optional[UUID]
    actor_role: str
    patient_id: Optional[UUID]
    created_at: datetime
    payload: str

class StaffPerformanceItem(BaseModel):
    user_id: UUID
    full_name: str
    role: str
    punch_count: int
    clinical_action_count: int

class VisitBrief(BaseModel):
    id: UUID
    started_at: datetime
    service_line: str
    status: str

class PatientProfileResponse(BaseModel):
    id: UUID
    full_name: str
    date_of_birth: str
    gender: str
    phone_number: Optional[str]
    address: Optional[str]
    total_visits: int
    active_admission: bool
    latest_visits: List[VisitBrief]
