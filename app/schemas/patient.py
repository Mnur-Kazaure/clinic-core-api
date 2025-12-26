# app/schemas/patient.py
from pydantic import BaseModel, constr
from typing import Literal
from datetime import date


# app/schemas/patient.py
class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    gender: Literal["MALE", "FEMALE", "OTHER"]
    date_of_birth: date
    address: str
    phone: constr(min_length=7)