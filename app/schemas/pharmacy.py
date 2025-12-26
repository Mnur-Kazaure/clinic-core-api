# app/schemas/pharmacy.py
from pydantic import BaseModel, UUID4


# -----------------------------
# Request
# -----------------------------

class DispenseCreate(BaseModel):
    pharmacist_id: UUID4
    quantity: int


# -----------------------------
# Response
# -----------------------------

class DispenseResponse(BaseModel):
    id: UUID4
    prescription_id: UUID4
    pharmacist_id: UUID4
    quantity: int

    class Config:
        from_attributes = True
