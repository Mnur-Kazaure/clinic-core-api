from __future__ import annotations

from collections import defaultdict
from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.service_line import ServiceLine
from app.shared.enums import ServiceLineKind


_UNSET = object()


class ServiceLineService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, *, clinic_id: UUID, service_line_id: UUID) -> ServiceLine | None:
        return (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.id == service_line_id,
                ServiceLine.clinic_id == clinic_id,
            )
            .first()
        )

    def get_or_404(self, *, clinic_id: UUID, service_line_id: UUID) -> ServiceLine:
        line = self.get_by_id(clinic_id=clinic_id, service_line_id=service_line_id)
        if line is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service line not found",
            )
        return line

    def list_for_clinic(
        self,
        *,
        clinic_id: UUID,
        include_inactive: bool = False,
        service_line_kind: ServiceLineKind | None = None,
    ) -> list[ServiceLine]:
        query = self.db.query(ServiceLine).filter(ServiceLine.clinic_id == clinic_id)
        if not include_inactive:
            query = query.filter(ServiceLine.is_active == True)
        if service_line_kind is not None:
            query = query.filter(ServiceLine.service_line_kind == service_line_kind)
        return query.order_by(ServiceLine.parent_id.asc().nullsfirst(), ServiceLine.name.asc()).all()

    def list_tree(
        self,
        *,
        clinic_id: UUID,
        include_inactive: bool = False,
        department_id: UUID | None = None,
        include_global_roots: bool = True,
        service_line_kind: ServiceLineKind | None = None,
    ) -> list[dict]:
        lines = self.list_for_clinic(
            clinic_id=clinic_id,
            include_inactive=include_inactive,
            service_line_kind=service_line_kind,
        )
        children_by_parent: dict[UUID | None, list[ServiceLine]] = defaultdict(list)
        by_id: dict[UUID, ServiceLine] = {}
        for line in lines:
            by_id[line.id] = line
            children_by_parent[line.parent_id].append(line)

        def build_node(item: ServiceLine) -> dict:
            children = [
                build_node(child)
                for child in sorted(children_by_parent.get(item.id, []), key=lambda c: c.name.lower())
            ]
            return {
                "id": item.id,
                "clinic_id": item.clinic_id,
                "name": item.name,
                "parent_id": item.parent_id,
                "department_id": item.department_id,
                "default_child_id": item.default_child_id,
                "requires_doctor": item.requires_doctor,
                "service_line_kind": item.service_line_kind,
                "is_active": item.is_active,
                "children": children,
            }

        roots = sorted(children_by_parent.get(None, []), key=lambda c: c.name.lower())
        if department_id is not None:
            roots = [
                root
                for root in roots
                if root.department_id == department_id
                or (include_global_roots and root.department_id is None)
            ]

        return [build_node(root) for root in roots]

    def create(
        self,
        *,
        clinic_id: UUID,
        name: str,
        parent_id: UUID | None,
        department_id: UUID | None,
        default_child_id: UUID | None,
        requires_doctor: bool,
        service_line_kind: ServiceLineKind,
        is_active: bool,
    ) -> ServiceLine:
        parent = None
        if parent_id is not None:
            parent = self.get_or_404(clinic_id=clinic_id, service_line_id=parent_id)

        line = ServiceLine(
            clinic_id=clinic_id,
            name=name.strip(),
            parent_id=parent.id if parent else None,
            department_id=department_id,
            default_child_id=default_child_id,
            requires_doctor=requires_doctor,
            service_line_kind=service_line_kind,
            is_active=is_active,
        )
        self._validate_default_child(clinic_id=clinic_id, line=line)
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
        return line

    def update(
        self,
        *,
        clinic_id: UUID,
        service_line_id: UUID,
        name: str | None | object = _UNSET,
        parent_id: UUID | None | object = _UNSET,
        department_id: UUID | None | object = _UNSET,
        default_child_id: UUID | None | object = _UNSET,
        requires_doctor: bool | object = _UNSET,
        service_line_kind: ServiceLineKind | object = _UNSET,
        is_active: bool | object = _UNSET,
    ) -> ServiceLine:
        line = self.get_or_404(clinic_id=clinic_id, service_line_id=service_line_id)

        if name is not _UNSET:
            if name is None or not str(name).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="name cannot be empty",
                )
            line.name = str(name).strip()

        if parent_id is not _UNSET:
            if parent_id is None:
                line.parent_id = None
            else:
                if parent_id == line.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="parent_id cannot reference the same service line",
                    )
                parent = self.get_or_404(clinic_id=clinic_id, service_line_id=parent_id)
                self._ensure_no_cycle(start_id=line.id, new_parent_id=parent.id)
                line.parent_id = parent.id

        if department_id is not _UNSET:
            line.department_id = department_id

        if default_child_id is not _UNSET:
            line.default_child_id = default_child_id

        if requires_doctor is not _UNSET:
            line.requires_doctor = bool(requires_doctor)

        if service_line_kind is not _UNSET:
            line.service_line_kind = service_line_kind

        if is_active is not _UNSET:
            line.is_active = bool(is_active)

        self._validate_default_child(clinic_id=clinic_id, line=line)
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
        return line

    def soft_delete(self, *, clinic_id: UUID, service_line_id: UUID) -> ServiceLine:
        line = self.get_or_404(clinic_id=clinic_id, service_line_id=service_line_id)
        line.is_active = False
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
        return line

    def get_path(self, *, clinic_id: UUID, service_line_id: UUID) -> list[ServiceLine]:
        line = self.get_or_404(clinic_id=clinic_id, service_line_id=service_line_id)
        path: list[ServiceLine] = []
        visited: set[UUID] = set()
        current = line
        while current is not None:
            if current.id in visited:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Service line hierarchy contains a cycle",
                )
            visited.add(current.id)
            path.append(current)
            if current.parent_id is None:
                break
            current = self.get_by_id(clinic_id=clinic_id, service_line_id=current.parent_id)
            if current is None:
                break
        return path

    def resolve_root(self, *, clinic_id: UUID, service_line_id: UUID) -> ServiceLine:
        path = self.get_path(clinic_id=clinic_id, service_line_id=service_line_id)
        return path[-1]

    def resolve_department_id(self, *, clinic_id: UUID, service_line_id: UUID) -> UUID | None:
        # Prefer closest explicit department mapping in the path.
        for line in self.get_path(clinic_id=clinic_id, service_line_id=service_line_id):
            if line.department_id is not None:
                return line.department_id
        return None

    def resolve_requires_doctor(self, *, clinic_id: UUID, service_line_id: UUID) -> bool:
        return any(
            line.requires_doctor
            for line in self.get_path(clinic_id=clinic_id, service_line_id=service_line_id)
        )

    def is_leaf(self, *, clinic_id: UUID, service_line_id: UUID) -> bool:
        child = (
            self.db.query(ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.parent_id == service_line_id,
                ServiceLine.is_active == True,
            )
            .first()
        )
        return child is None

    def _validate_default_child(self, *, clinic_id: UUID, line: ServiceLine) -> None:
        if line.default_child_id is None:
            return
        if line.default_child_id == line.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="default_child_id cannot reference the same service line",
            )
        default_child = self.get_or_404(
            clinic_id=clinic_id,
            service_line_id=line.default_child_id,
        )
        if default_child.parent_id != line.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="default_child_id must reference a direct child",
            )

    def _ensure_no_cycle(self, *, start_id: UUID, new_parent_id: UUID) -> None:
        visited: set[UUID] = set()
        current_id: UUID | None = new_parent_id
        while current_id is not None:
            if current_id == start_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid hierarchy cycle",
                )
            if current_id in visited:
                break
            visited.add(current_id)
            row = (
                self.db.query(ServiceLine.parent_id)
                .filter(ServiceLine.id == current_id)
                .first()
            )
            if row is None:
                break
            current_id = row.parent_id


def leaf_service_line_ids(lines: Iterable[ServiceLine]) -> set[UUID]:
    by_parent: dict[UUID, int] = {}
    all_ids: set[UUID] = set()
    for line in lines:
        all_ids.add(line.id)
        if line.parent_id:
            by_parent[line.parent_id] = by_parent.get(line.parent_id, 0) + 1
    return {line_id for line_id in all_ids if by_parent.get(line_id, 0) == 0}
