# app/schemas/auth.py
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from app.shared.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


# Alias — NOT a new schema
RefreshTokenResponse = TokenResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    refresh_token: str




class MeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    role: UserRole
    clinic_id: UUID
    current_department_id: UUID | None = None
    allowed_department_ids: list[UUID] = Field(default_factory=list)
    current_department_name: str | None = None
    allowed_departments: list["DepartmentContextResponse"] = Field(default_factory=list)
    default_lab_unit_id: UUID | None = None
    allowed_lab_unit_ids: list[UUID] = Field(default_factory=list)
    allowed_lab_units: list["LabUnitContextResponse"] = Field(default_factory=list)
    default_pharmacy_unit_id: UUID | None = None
    allowed_pharmacy_unit_ids: list[UUID] = Field(default_factory=list)
    allowed_pharmacy_units: list["PharmacyUnitContextResponse"] = Field(default_factory=list)
    default_cashier_pay_point_id: UUID | None = None
    allowed_cashier_pay_point_ids: list[UUID] = Field(default_factory=list)
    allowed_cashier_pay_points: list["CashierPayPointContextResponse"] = Field(default_factory=list)
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SwitchDepartmentRequest(BaseModel):
    department_id: UUID


class SwitchDepartmentResponse(BaseModel):
    detail: str
    current_department_id: UUID
    allowed_department_ids: list[UUID] = Field(default_factory=list)


class DepartmentContextResponse(BaseModel):
    id: UUID
    name: str
    is_primary: bool = False


class LabUnitContextResponse(BaseModel):
    id: UUID
    name: str


class PharmacyUnitContextResponse(BaseModel):
    id: UUID
    name: str


class CashierPayPointContextResponse(BaseModel):
    id: UUID
    name: str


MeResponse.model_rebuild()
