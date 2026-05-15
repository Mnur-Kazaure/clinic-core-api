from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.models.lab_user_unit_access import LabUserUnitAccess
from app.models.service_line import ServiceLine
from app.models.user import User
from app.shared.enums import LAB_WORKFORCE_ROLES, ServiceLineKind, UserRole


class LabUnitAccessService:
    def __init__(self, db: Session):
        self.db = db

    def list_user_units(self, *, clinic_id: UUID, user_id: UUID) -> list[ServiceLine]:
        return (
            self.db.query(ServiceLine)
            .join(LabUserUnitAccess, LabUserUnitAccess.service_line_id == ServiceLine.id)
            .filter(
                LabUserUnitAccess.user_id == user_id,
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
                ServiceLine.is_active == True,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )

    def allowed_unit_ids(self, *, clinic_id: UUID, user_id: UUID) -> list[UUID]:
        rows = (
            self.db.query(LabUserUnitAccess.service_line_id)
            .join(ServiceLine, ServiceLine.id == LabUserUnitAccess.service_line_id)
            .filter(
                LabUserUnitAccess.user_id == user_id,
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
                ServiceLine.is_active == True,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )
        return [row.service_line_id for row in rows]

    def sync_user_units(
        self,
        *,
        clinic_id: UUID,
        user: User,
        role: UserRole,
        allowed_unit_ids: list[UUID] | None,
        default_unit_id: UUID | None,
    ) -> None:
        normalized_ids = list(dict.fromkeys(allowed_unit_ids or []))
        is_lab_manager = role == UserRole.LAB_MANAGER
        is_lab_workforce = role in LAB_WORKFORCE_ROLES

        if not is_lab_workforce:
            self._clear_user_units(user=user)
            return

        if is_lab_manager:
            self._clear_user_units(user=user)
            user.default_lab_unit_id = None
            return

        if not normalized_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Lab staff must have at least one allowed lab unit",
            )

        active_units = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.id.in_(normalized_ids),
                ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
                ServiceLine.is_active == True,
            )
            .all()
        )
        active_unit_ids = {unit.id for unit in active_units}
        if len(active_unit_ids) != len(normalized_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One or more selected lab units are invalid or inactive",
            )
        for unit in active_units:
            has_active_child = self.db.query(
                exists().where(
                    ServiceLine.clinic_id == clinic_id,
                    ServiceLine.parent_id == unit.id,
                    ServiceLine.is_active == True,
                )
            ).scalar()
            if has_active_child:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Lab unit assignments must target active leaf service lines",
                )

        resolved_default = default_unit_id or normalized_ids[0]
        if resolved_default not in active_unit_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Default lab unit must be one of the allowed lab units",
            )

        existing = (
            self.db.query(LabUserUnitAccess)
            .filter(LabUserUnitAccess.user_id == user.id)
            .all()
        )
        existing_ids = {row.service_line_id for row in existing}

        for row in existing:
            if row.service_line_id not in active_unit_ids:
                self.db.delete(row)

        for unit_id in active_unit_ids - existing_ids:
            self.db.add(
                LabUserUnitAccess(
                    user_id=user.id,
                    service_line_id=unit_id,
                )
            )

        user.default_lab_unit_id = resolved_default

    def context_for_user(
        self,
        *,
        clinic_id: UUID,
        user: User,
    ) -> tuple[UUID | None, list[UUID], list[dict]]:
        try:
            role = UserRole(user.role)
        except ValueError:
            role = None

        if role not in LAB_WORKFORCE_ROLES:
            return None, [], []

        if role == UserRole.LAB_MANAGER:
            return None, [], []

        units = self.list_user_units(clinic_id=clinic_id, user_id=user.id)
        allowed_unit_ids = [unit.id for unit in units]
        default_unit_id = user.default_lab_unit_id
        if default_unit_id is None and allowed_unit_ids:
            default_unit_id = allowed_unit_ids[0]
        return default_unit_id, allowed_unit_ids, [
            {"id": unit.id, "name": unit.name} for unit in units
        ]

    def resolve_selected_unit(
        self,
        *,
        clinic_id: UUID,
        user: User,
        selected_unit_id: UUID | None,
    ) -> ServiceLine:
        try:
            role = UserRole(user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab access required",
            )

        if role == UserRole.LAB_MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operational lab unit access is not available for lab manager accounts",
            )

        units = self.list_user_units(clinic_id=clinic_id, user_id=user.id)
        if not units:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No allowed lab units are configured for this account",
            )

        units_by_id = {unit.id: unit for unit in units}
        resolved_id = selected_unit_id or user.default_lab_unit_id or units[0].id
        resolved = units_by_id.get(resolved_id)
        if resolved is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected lab unit is outside your allowed lab-unit scope",
            )
        return resolved

    def _clear_user_units(self, *, user: User) -> None:
        (
            self.db.query(LabUserUnitAccess)
            .filter(LabUserUnitAccess.user_id == user.id)
            .delete(synchronize_session=False)
        )
        user.default_lab_unit_id = None
