from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cashier_pay_point import CashierPayPoint
from app.models.cashier_pay_point_access import CashierPayPointAccess
from app.models.user import User
from app.shared.enums import UserRole


class CashierPayPointAccessService:
    def __init__(self, db: Session):
        self.db = db

    def list_user_pay_points(self, *, clinic_id: UUID, user_id: UUID) -> list[CashierPayPoint]:
        explicit_pay_points = (
            self.db.query(CashierPayPoint)
            .join(
                CashierPayPointAccess,
                CashierPayPointAccess.cashier_pay_point_id == CashierPayPoint.id,
            )
            .filter(
                CashierPayPoint.clinic_id == clinic_id,
                CashierPayPoint.is_active == True,
                CashierPayPointAccess.user_id == user_id,
                CashierPayPointAccess.is_active == True,
            )
            .order_by(CashierPayPoint.name.asc())
            .all()
        )
        if explicit_pay_points:
            return explicit_pay_points

        # Legacy compatibility: older cashier accounts may predate explicit
        # pay-point assignment rows. In that case, expose active clinic pay
        # points until explicit scope is configured.
        return (
            self.db.query(CashierPayPoint)
            .filter(
                CashierPayPoint.clinic_id == clinic_id,
                CashierPayPoint.is_active == True,
            )
            .order_by(CashierPayPoint.name.asc())
            .all()
        )

    def resolve_selected_pay_point(
        self,
        *,
        clinic_id: UUID,
        user: User,
        selected_pay_point_id: UUID | None,
    ) -> CashierPayPoint:
        try:
            role = UserRole(user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cashier access required",
            )

        if role != UserRole.CASHIER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operational pay-point access is only available to cashiers",
            )

        pay_points = self.list_user_pay_points(clinic_id=clinic_id, user_id=user.id)
        if not pay_points:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No cashier pay point is configured for this account",
            )

        if selected_pay_point_id is None:
            default_access = (
                self.db.query(CashierPayPointAccess.cashier_pay_point_id)
                .filter(
                    CashierPayPointAccess.user_id == user.id,
                    CashierPayPointAccess.is_active == True,
                    CashierPayPointAccess.is_default == True,
                )
                .first()
            )
            selected_pay_point_id = (
                default_access.cashier_pay_point_id
                if default_access is not None
                else pay_points[0].id
            )

        pay_points_by_id = {row.id: row for row in pay_points}
        resolved = pay_points_by_id.get(selected_pay_point_id)
        if resolved is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected cashier pay point is outside your allowed scope",
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

        if role != UserRole.CASHIER:
            return None, [], []

        pay_points = self.list_user_pay_points(clinic_id=clinic_id, user_id=user.id)
        allowed_ids = [row.id for row in pay_points]
        default_row = (
            self.db.query(CashierPayPointAccess.cashier_pay_point_id)
            .filter(
                CashierPayPointAccess.user_id == user.id,
                CashierPayPointAccess.is_active == True,
                CashierPayPointAccess.is_default == True,
            )
            .first()
        )
        default_id = (
            default_row.cashier_pay_point_id if default_row is not None else (allowed_ids[0] if allowed_ids else None)
        )
        return default_id, allowed_ids, [
            {"id": row.id, "name": row.name} for row in pay_points
        ]

    def sync_user_pay_points(
        self,
        *,
        clinic_id: UUID,
        user: User,
        role: UserRole,
        allowed_pay_point_ids: list[UUID] | None,
        default_pay_point_id: UUID | None,
    ) -> None:
        normalized_ids = list(dict.fromkeys(allowed_pay_point_ids or []))
        if role != UserRole.CASHIER:
            self._clear_user_pay_points(user_id=user.id)
            return

        if not normalized_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cashier staff must have at least one assigned pay point",
            )

        pay_points = (
            self.db.query(CashierPayPoint)
            .filter(
                CashierPayPoint.clinic_id == clinic_id,
                CashierPayPoint.id.in_(normalized_ids),
                CashierPayPoint.is_active == True,
            )
            .all()
        )
        pay_point_ids = {row.id for row in pay_points}
        if len(pay_point_ids) != len(normalized_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One or more selected cashier pay points are invalid or inactive",
            )

        resolved_default = default_pay_point_id or normalized_ids[0]
        if resolved_default not in pay_point_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Default cashier pay point must be one of the assigned pay points",
            )

        existing = (
            self.db.query(CashierPayPointAccess)
            .filter(CashierPayPointAccess.user_id == user.id)
            .all()
        )
        existing_by_id = {row.cashier_pay_point_id: row for row in existing}

        for row in existing:
            if row.cashier_pay_point_id not in pay_point_ids:
                self.db.delete(row)

        for pay_point_id in pay_point_ids:
            row = existing_by_id.get(pay_point_id)
            if row is None:
                row = CashierPayPointAccess(
                    clinic_id=clinic_id,
                    user_id=user.id,
                    cashier_pay_point_id=pay_point_id,
                )
            row.is_active = True
            row.is_default = pay_point_id == resolved_default
            self.db.add(row)

    def _clear_user_pay_points(self, *, user_id: UUID) -> None:
        (
            self.db.query(CashierPayPointAccess)
            .filter(CashierPayPointAccess.user_id == user_id)
            .delete(synchronize_session=False)
        )
