# app/schemas/clinic.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.shared.enums import UserRole
from typing import Optional
from uuid import UUID

class ClinicRegistrationRequest(BaseModel):
    clinic_name: str = Field(..., min_length=2)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)



class StaffCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole


class StaffUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    specialty: Optional[str] = None
    department: Optional[str] = None
    room_label: Optional[str] = None
    availability_status: Optional[str] = None


class StaffResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    full_name: Optional[str]
    email: EmailStr
    role: UserRole
    is_active: bool
    specialty: Optional[str] = None
    department: Optional[str] = None
    room_label: Optional[str] = None
    availability_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicProfileResponse(BaseModel):
    id: UUID
    name: str
    logo_url: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2)
    logo_url: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    description: Optional[str] = None
