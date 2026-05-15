from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cashier_pay_point import CashierPayPoint
from app.models.patient import Patient
from app.models.pharmacy_routing_rule import PharmacyRoutingRule
from app.models.service_line import ServiceLine
from app.models.visit import Visit


@dataclass(frozen=True)
class PharmacyRoutingDecision:
    dispensing_unit: ServiceLine
    cashier_pay_point: CashierPayPoint
    matched_rule: PharmacyRoutingRule


class PharmacyRoutingService:
    def __init__(self, db: Session):
        self.db = db

    def resolve_assignment(
        self,
        *,
        clinic_id: UUID,
        visit: Visit,
        patient: Patient,
        scheme_type: str | None = None,
    ) -> PharmacyRoutingDecision:
        rules = (
            self.db.query(PharmacyRoutingRule)
            .filter(
                PharmacyRoutingRule.clinic_id == clinic_id,
                PharmacyRoutingRule.is_active == True,
            )
            .order_by(
                PharmacyRoutingRule.is_fallback.asc(),
                PharmacyRoutingRule.priority.asc(),
                PharmacyRoutingRule.created_at.asc(),
            )
            .all()
        )
        if not rules:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No active pharmacy routing rules are configured",
            )

        path_ids = self._service_line_path_ids(clinic_id=clinic_id, service_line_id=visit.service_line_id)
        age_years = self._calculate_age_in_years(patient.date_of_birth)

        for rule in rules:
            if rule.visit_service_line is not None and rule.visit_service_line != visit.service_line:
                continue
            if rule.visit_service_line_id is not None and rule.visit_service_line_id not in path_ids:
                continue
            if rule.scheme_type is not None:
                if scheme_type is None or rule.scheme_type.strip().lower() != scheme_type.strip().lower():
                    continue
            if rule.min_age_years is not None and age_years < rule.min_age_years:
                continue
            if rule.max_age_years is not None and age_years > rule.max_age_years:
                continue

            dispensing_unit = self._get_service_line(
                clinic_id=clinic_id,
                service_line_id=rule.dispensing_unit_id,
                detail="Configured dispensing unit was not found",
            )
            cashier_pay_point = self._get_pay_point(
                clinic_id=clinic_id,
                pay_point_id=rule.cashier_pay_point_id,
            )
            return PharmacyRoutingDecision(
                dispensing_unit=dispensing_unit,
                cashier_pay_point=cashier_pay_point,
                matched_rule=rule,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No pharmacy routing rule matched this prescription context",
        )

    def _get_service_line(self, *, clinic_id: UUID, service_line_id: UUID, detail: str) -> ServiceLine:
        line = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.id == service_line_id,
                ServiceLine.is_active == True,
            )
            .first()
        )
        if line is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        return line

    def _get_pay_point(self, *, clinic_id: UUID, pay_point_id: UUID) -> CashierPayPoint:
        pay_point = (
            self.db.query(CashierPayPoint)
            .filter(
                CashierPayPoint.clinic_id == clinic_id,
                CashierPayPoint.id == pay_point_id,
                CashierPayPoint.is_active == True,
            )
            .first()
        )
        if pay_point is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Configured cashier pay point was not found",
            )
        return pay_point

    def _service_line_path_ids(
        self,
        *,
        clinic_id: UUID,
        service_line_id: UUID | None,
    ) -> set[UUID]:
        if service_line_id is None:
            return set()

        ids: set[UUID] = set()
        current_id = service_line_id
        for _ in range(20):
            if current_id in ids:
                break
            ids.add(current_id)
            row = (
                self.db.query(ServiceLine.parent_id)
                .filter(
                    ServiceLine.clinic_id == clinic_id,
                    ServiceLine.id == current_id,
                )
                .first()
            )
            if row is None or row.parent_id is None:
                break
            current_id = row.parent_id
        return ids

    @staticmethod
    def _calculate_age_in_years(date_of_birth: date) -> int:
        today = date.today()
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return max(age, 0)
