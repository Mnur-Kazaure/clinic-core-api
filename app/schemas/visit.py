# app/schemas/visit.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.shared.enums import VisitStatus


# ---------------------------
# Core Visit Response
# ---------------------------

class VisitResponse(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: Optional[str] = None
    clinic_id: UUID
    status: VisitStatus
    assigned_doctor_id: Optional[UUID]


    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------
# Transition Request
# ---------------------------

class VisitTransitionRequest(BaseModel):
    to_status: VisitStatus


# ---------------------------
# Allowed Transitions
# ---------------------------

class AllowedTransitionsResponse(BaseModel):
    allowed: List[VisitStatus]


# ---------------------------
# Timeline
# ---------------------------

class VisitTimelineEvent(BaseModel):
    id: UUID
    from_status: VisitStatus
    to_status: VisitStatus
    changed_by: UUID
    created_at: datetime


class VisitTimelineResponse(BaseModel):
    visit_id: UUID
    timeline: List[VisitTimelineEvent]

# ---------------------------
# Create Visit
# ---------------------------

class VisitCreateRequest(BaseModel):
    patient_id: UUID
    assigned_doctor_id: UUID


class VisitCreateResponse(VisitResponse):
    pass
