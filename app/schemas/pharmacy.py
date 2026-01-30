# app/schemas/pharmacy.py
from pydantic import BaseModel, UUID4, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)
