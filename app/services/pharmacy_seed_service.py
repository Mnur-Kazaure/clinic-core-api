from __future__ import annotations

from uuid import UUID

from app.models.cashier_pay_point import CashierPayPoint
from app.models.department import Department
from app.models.pharmacy_routing_rule import PharmacyRoutingRule
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.service_line import ServiceLine
from app.shared.enums import PharmacyUnitCategory, ServiceLineKind, VisitServiceLine


class PharmacySeedService:
    def __init__(self, db):
        self.db = db

    def seed_kazaure_structure(self, *, clinic_id: UUID, commit: bool = True) -> None:
        pharmacy_root = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Pharmacy Department",
            parent_id=None,
            department_id=None,
        )
        store = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Store",
            parent_id=pharmacy_root.id,
            department_id=None,
        )
        adult = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Adult Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="GOPD"),
        )
        pediatric = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Pediatric Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="GOPD"),
        )
        nhis = self._ensure_service_line(
            clinic_id=clinic_id,
            name="NHIS Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="GOPD"),
        )
        gopd = self._ensure_service_line(
            clinic_id=clinic_id,
            name="GOPD Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="GOPD"),
        )
        maternity = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Maternity Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="Maternity"),
        )
        ae = self._ensure_service_line(
            clinic_id=clinic_id,
            name="A&E Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="A&E"),
        )
        specialist = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Specialist Pharmacy",
            parent_id=pharmacy_root.id,
            department_id=self._resolve_department_id(clinic_id=clinic_id, name="Specialist"),
        )

        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=store,
            category=PharmacyUnitCategory.STORE,
            linked_visit_service_line=None,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=adult,
            category=PharmacyUnitCategory.DISPENSING,
            linked_visit_service_line=VisitServiceLine.OPD,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=pediatric,
            category=PharmacyUnitCategory.DISPENSING,
            linked_visit_service_line=VisitServiceLine.OPD,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=nhis,
            category=PharmacyUnitCategory.DISPENSING,
            linked_visit_service_line=VisitServiceLine.OPD,
            scheme_type="NHIS",
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=gopd,
            category=PharmacyUnitCategory.SATELLITE,
            linked_visit_service_line=VisitServiceLine.OPD,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=maternity,
            category=PharmacyUnitCategory.SATELLITE,
            linked_visit_service_line=VisitServiceLine.MATERNITY,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=ae,
            category=PharmacyUnitCategory.SATELLITE,
            linked_visit_service_line=None,
            scheme_type=None,
        )
        self._ensure_unit_profile(
            clinic_id=clinic_id,
            service_line=specialist,
            category=PharmacyUnitCategory.SATELLITE,
            linked_visit_service_line=VisitServiceLine.OPD,
            scheme_type=None,
        )

        pharmacy_pay_point = self._ensure_pay_point(
            clinic_id=clinic_id,
            code="PHARMACY",
            name="Pharmacy Pay Point",
            description="Dedicated pharmacy department cashier pay point",
        )
        specialist_pay_point = self._ensure_pay_point(
            clinic_id=clinic_id,
            code="SPECIALIST",
            name="Specialist Pay Point",
            description="Specialist department cashier pay point",
        )
        ward_pay_point = self._ensure_pay_point(
            clinic_id=clinic_id,
            code="WARDS",
            name="Wards Pay Point",
            description="Male, female, and Gany wards pay point",
        )
        ae_pay_point = self._ensure_pay_point(
            clinic_id=clinic_id,
            code="AE_THEATER",
            name="A&E / Theater Pay Point",
            description="A&E and theater cashier pay point",
        )
        lab_maternity_pay_point = self._ensure_pay_point(
            clinic_id=clinic_id,
            code="LAB_MATERNITY",
            name="Lab & Maternity Pay Point",
            description="Shared laboratory and maternity cashier pay point",
        )

        consultation = self._find_service_line(clinic_id=clinic_id, name="Consultation")
        specialist_root = self._find_service_line(clinic_id=clinic_id, name="Specialist")
        ae_root = self._find_service_line(clinic_id=clinic_id, name="A&E")

        if consultation is not None:
            self._ensure_rule(
                clinic_id=clinic_id,
                name="GOPD pediatric route",
                priority=10,
                visit_service_line=VisitServiceLine.OPD,
                visit_service_line_id=consultation.id,
                min_age_years=None,
                max_age_years=15,
                dispensing_unit_id=pediatric.id,
                cashier_pay_point_id=pharmacy_pay_point.id,
                is_fallback=False,
            )
            self._ensure_rule(
                clinic_id=clinic_id,
                name="GOPD adult route",
                priority=20,
                visit_service_line=VisitServiceLine.OPD,
                visit_service_line_id=consultation.id,
                min_age_years=16,
                max_age_years=None,
                dispensing_unit_id=adult.id,
                cashier_pay_point_id=pharmacy_pay_point.id,
                is_fallback=False,
            )

        if specialist_root is not None:
            self._ensure_rule(
                clinic_id=clinic_id,
                name="Specialist route",
                priority=30,
                visit_service_line=VisitServiceLine.OPD,
                visit_service_line_id=specialist_root.id,
                min_age_years=None,
                max_age_years=None,
                dispensing_unit_id=specialist.id,
                cashier_pay_point_id=specialist_pay_point.id,
                is_fallback=False,
            )

        self._ensure_rule(
            clinic_id=clinic_id,
            name="Maternity route",
            priority=40,
            visit_service_line=VisitServiceLine.MATERNITY,
            visit_service_line_id=None,
            min_age_years=None,
            max_age_years=None,
            dispensing_unit_id=maternity.id,
            cashier_pay_point_id=lab_maternity_pay_point.id,
            is_fallback=False,
        )

        if ae_root is not None:
            self._ensure_rule(
                clinic_id=clinic_id,
                name="A&E route",
                priority=50,
                visit_service_line=None,
                visit_service_line_id=ae_root.id,
                min_age_years=None,
                max_age_years=None,
                dispensing_unit_id=ae.id,
                cashier_pay_point_id=ae_pay_point.id,
                is_fallback=False,
            )

        self._ensure_rule(
            clinic_id=clinic_id,
            name="Fallback adult route",
            priority=999,
            visit_service_line=None,
            visit_service_line_id=None,
            min_age_years=None,
            max_age_years=None,
            dispensing_unit_id=adult.id,
            cashier_pay_point_id=pharmacy_pay_point.id,
            is_fallback=True,
        )

        if commit:
            self.db.commit()
        else:
            self.db.flush()

    def _ensure_service_line(
        self,
        *,
        clinic_id: UUID,
        name: str,
        parent_id: UUID | None,
        department_id: UUID | None,
    ) -> ServiceLine:
        existing = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.name.ilike(name),
                ServiceLine.parent_id.is_(parent_id) if parent_id is None else ServiceLine.parent_id == parent_id,
            )
            .first()
        )
        if existing is not None:
            existing.department_id = department_id
            existing.service_line_kind = ServiceLineKind.PHARMACY_UNIT
            existing.requires_doctor = False
            existing.is_active = True
            self.db.add(existing)
            self.db.flush()
            return existing

        line = ServiceLine(
            clinic_id=clinic_id,
            name=name,
            parent_id=parent_id,
            department_id=department_id,
            requires_doctor=False,
            service_line_kind=ServiceLineKind.PHARMACY_UNIT,
            is_active=True,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def _ensure_unit_profile(
        self,
        *,
        clinic_id: UUID,
        service_line: ServiceLine,
        category: PharmacyUnitCategory,
        linked_visit_service_line: VisitServiceLine | None,
        scheme_type: str | None,
    ) -> None:
        profile = (
            self.db.query(PharmacyUnitProfile)
            .filter(PharmacyUnitProfile.service_line_id == service_line.id)
            .first()
        )
        if profile is None:
            profile = PharmacyUnitProfile(
                clinic_id=clinic_id,
                service_line_id=service_line.id,
                unit_category=category,
                linked_visit_service_line=linked_visit_service_line,
                scheme_type=scheme_type,
            )
        else:
            profile.unit_category = category
            profile.linked_visit_service_line = linked_visit_service_line
            profile.scheme_type = scheme_type
        self.db.add(profile)
        self.db.flush()

    def _ensure_pay_point(
        self,
        *,
        clinic_id: UUID,
        code: str,
        name: str,
        description: str,
    ) -> CashierPayPoint:
        pay_point = (
            self.db.query(CashierPayPoint)
            .filter(
                CashierPayPoint.clinic_id == clinic_id,
                CashierPayPoint.code == code,
            )
            .first()
        )
        if pay_point is None:
            pay_point = CashierPayPoint(
                clinic_id=clinic_id,
                code=code,
                name=name,
                description=description,
                is_active=True,
            )
        else:
            pay_point.name = name
            pay_point.description = description
            pay_point.is_active = True
        self.db.add(pay_point)
        self.db.flush()
        return pay_point

    def _ensure_rule(
        self,
        *,
        clinic_id: UUID,
        name: str,
        priority: int,
        visit_service_line: VisitServiceLine | None,
        visit_service_line_id: UUID | None,
        min_age_years: int | None,
        max_age_years: int | None,
        dispensing_unit_id: UUID,
        cashier_pay_point_id: UUID,
        is_fallback: bool,
    ) -> None:
        rule = (
            self.db.query(PharmacyRoutingRule)
            .filter(
                PharmacyRoutingRule.clinic_id == clinic_id,
                PharmacyRoutingRule.name == name,
            )
            .first()
        )
        if rule is None:
            rule = PharmacyRoutingRule(
                clinic_id=clinic_id,
                name=name,
                priority=priority,
                visit_service_line=visit_service_line,
                visit_service_line_id=visit_service_line_id,
                min_age_years=min_age_years,
                max_age_years=max_age_years,
                dispensing_unit_id=dispensing_unit_id,
                cashier_pay_point_id=cashier_pay_point_id,
                is_fallback=is_fallback,
                is_active=True,
            )
        else:
            rule.priority = priority
            rule.visit_service_line = visit_service_line
            rule.visit_service_line_id = visit_service_line_id
            rule.min_age_years = min_age_years
            rule.max_age_years = max_age_years
            rule.dispensing_unit_id = dispensing_unit_id
            rule.cashier_pay_point_id = cashier_pay_point_id
            rule.is_fallback = is_fallback
            rule.is_active = True
        self.db.add(rule)
        self.db.flush()

    def _resolve_department_id(self, *, clinic_id: UUID, name: str) -> UUID | None:
        department = (
            self.db.query(Department.id)
            .filter(
                Department.clinic_id == clinic_id,
                Department.name.ilike(name),
            )
            .first()
        )
        return department.id if department is not None else None

    def _find_service_line(self, *, clinic_id: UUID, name: str) -> ServiceLine | None:
        return (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.name.ilike(name),
                ServiceLine.is_active == True,
            )
            .first()
        )
