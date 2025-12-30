# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field

# Current AUth implementationn
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Added now
class ClinicRegistrationRequest(BaseModel):
    clinic_name: str = Field(..., min_length=2)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)