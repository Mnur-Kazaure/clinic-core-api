# app/schemas/user.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class DoctorListSchema(BaseModel):
    id: UUID
    full_name: Optional[str]
    email: str
    specialty: Optional[str] = None
    department: Optional[str] = None
    room_label: Optional[str] = None
    availability_status: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
