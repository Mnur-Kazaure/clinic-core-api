from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_user_unit_access import PharmacyUserUnitAccess
from app.models.service_line import ServiceLine
from app.models.user import User
from app.shared.enums import PharmacyUnitCategory, ServiceLineKind, UserRole


class PharmacyUnitAccessService:
    def __init__(self, db: Session):
        self.db = db

    def list_user_units(self, *, clinic_id: UUID, user_id: UUID) -> list[ServiceLine]:
        return (
            self.db.query(ServiceLine)
            .join(PharmacyUserUnitAccess, PharmacyUserUnitAccess.service_line_id == ServiceLine.id)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                PharmacyUserUnitAccess.user_id == user_id,
                PharmacyUserUnitAccess.is_active == True,
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.service_line_kind == ServiceLineKind.PHARMACY_UNIT,
                ServiceLine.is_active == True,
                PharmacyUnitProfile.unit_category != PharmacyUnitCategory.STORE,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )

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
                detail="Pharmacy access required",
            )

        if role != UserRole.PHARMACY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operational dispensing access is only available to pharmacy staff",
            )

        units = self.list_user_units(clinic_id=clinic_id, user_id=user.id)
        if not units:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No assigned pharmacy dispensing units are configured for this account",
            )

        if selected_unit_id is None:
            default_access = (
                self.db.query(PharmacyUserUnitAccess.service_line_id)
                .filter(
                    PharmacyUserUnitAccess.user_id == user.id,
                    PharmacyUserUnitAccess.is_active == True,
                    PharmacyUserUnitAccess.is_default == True,
                )
                .first()
            )
            selected_unit_id = (
                default_access.service_line_id if default_access is not None else units[0].id
            )

        units_by_id = {unit.id: unit for unit in units}
        resolved = units_by_id.get(selected_unit_id)
        if resolved is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected pharmacy unit is outside your allowed dispensing scope",
            )
        return resolved

    def context_for_user(
        self,
        *,
        clinic_id: UUID,
        user: User,
    ) -> tuple[UUID | None, list[UUID], list[dict]]:
        try:
            role = UserRole(user.role)
        except ValueError:
            return None, [], []

        if role != UserRole.PHARMACY:
            return None, [], []

        units = self.list_user_units(clinic_id=clinic_id, user_id=user.id)
        allowed_unit_ids = [unit.id for unit in units]
        default_row = (
            self.db.query(PharmacyUserUnitAccess.service_line_id)
            .filter(
                PharmacyUserUnitAccess.user_id == user.id,
                PharmacyUserUnitAccess.is_active == True,
                PharmacyUserUnitAccess.is_default == True,
            )
            .first()
        )
        default_unit_id = (
            default_row.service_line_id if default_row is not None else (allowed_unit_ids[0] if allowed_unit_ids else None)
        )
        return default_unit_id, allowed_unit_ids, [
            {"id": unit.id, "name": unit.name} for unit in units
        ]

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
        if role != UserRole.PHARMACY:
            self._clear_user_units(user_id=user.id)
            return

        if not normalized_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Pharmacy staff must have at least one assigned dispensing unit",
            )

        units = (
            self.db.query(ServiceLine)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.id.in_(normalized_ids),
                ServiceLine.service_line_kind == ServiceLineKind.PHARMACY_UNIT,
                ServiceLine.is_active == True,
                PharmacyUnitProfile.unit_category != PharmacyUnitCategory.STORE,
            )
            .all()
        )
        unit_ids = {unit.id for unit in units}
        if len(unit_ids) != len(normalized_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One or more selected pharmacy units are invalid or inactive",
            )

        for unit in units:
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
                    detail="Pharmacy assignments must target active leaf dispensing units",
                )

        resolved_default = default_unit_id or normalized_ids[0]
        if resolved_default not in unit_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Default pharmacy unit must be one of the assigned units",
            )

        existing = (
            self.db.query(PharmacyUserUnitAccess)
            .filter(PharmacyUserUnitAccess.user_id == user.id)
            .all()
        )
        existing_by_unit = {row.service_line_id: row for row in existing}

        for row in existing:
            if row.service_line_id not in unit_ids:
                self.db.delete(row)

        for unit_id in unit_ids:
            row = existing_by_unit.get(unit_id)
            if row is None:
                row = PharmacyUserUnitAccess(
                    clinic_id=clinic_id,
                    user_id=user.id,
                    service_line_id=unit_id,
                )
            row.is_active = True
            row.is_default = unit_id == resolved_default
            self.db.add(row)

    def _clear_user_units(self, *, user_id: UUID) -> None:
        (
            self.db.query(PharmacyUserUnitAccess)
            .filter(PharmacyUserUnitAccess.user_id == user_id)
            .delete(synchronize_session=False)
        )
