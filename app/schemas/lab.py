# app/schemas/lab.py

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime


class LabResultCreate(BaseModel):
    result_value: str = Field(min_length=1)
    result_unit: str | None = None
    reference_range: str | None = None
    technician_id: UUID


class LabResultResponse(BaseModel):
    id: UUID
    lab_request_id: UUID
    result_value: str
    result_unit: str
    reference_range: str
    technician_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
