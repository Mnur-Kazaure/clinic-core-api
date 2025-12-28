from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., example="doctor1")
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"