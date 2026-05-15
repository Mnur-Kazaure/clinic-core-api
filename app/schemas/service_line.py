from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.shared.enums import ServiceLineKind


class ServiceLineBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    parent_id: UUID | None = None
    department_id: UUID | None = None
    default_child_id: UUID | None = None
    requires_doctor: bool = False
    service_line_kind: ServiceLineKind = ServiceLineKind.GENERAL
    is_active: bool = True


class ServiceLineCreateRequest(ServiceLineBase):
    pass


class ServiceLineUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    parent_id: UUID | None = None
    department_id: UUID | None = None
    default_child_id: UUID | None = None
    requires_doctor: bool | None = None
    service_line_kind: ServiceLineKind | None = None
    is_active: bool | None = None


class ServiceLineResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    parent_id: UUID | None = None
    department_id: UUID | None = None
    default_child_id: UUID | None = None
    requires_doctor: bool
    service_line_kind: ServiceLineKind
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ServiceLineTreeNode(ServiceLineResponse):
    children: list["ServiceLineTreeNode"] = Field(default_factory=list)


ServiceLineTreeNode.model_rebuild()
