# app/schemas/attendance.py

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class AttendancePunchRequest(BaseModel):
    user_id: UUID
    punch_type: str  # "PUNCH_IN" or "PUNCH_OUT"
    hardware_ref: Optional[str] = None
    location: Optional[str] = None
    device_metadata: Optional[dict] = None

class AttendanceLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    punch_type: str
    punched_at: datetime
    hardware_ref: Optional[str]
    location: Optional[str]

    model_config = ConfigDict(from_attributes=True)
