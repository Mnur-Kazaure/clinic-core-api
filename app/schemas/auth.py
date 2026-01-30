# app/schemas/auth.py
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from pydantic import BaseModel
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
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
