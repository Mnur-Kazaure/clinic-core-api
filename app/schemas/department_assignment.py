from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DepartmentResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserDepartmentAssignRequest(BaseModel):
    department_id: UUID
    is_primary: bool = False


class UserDepartmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    department_id: UUID
    is_primary: bool

    model_config = ConfigDict(from_attributes=True)


class DoctorServiceLineAssignRequest(BaseModel):
    service_line_id: UUID


class DoctorServiceLineResponse(BaseModel):
    id: UUID
    doctor_id: UUID
    service_line_id: UUID

    model_config = ConfigDict(from_attributes=True)
