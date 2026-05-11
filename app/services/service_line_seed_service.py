from __future__ import annotations

from uuid import UUID

from app.models.department import Department
from app.models.doctor_service_line import DoctorServiceLine
from app.models.service_line import ServiceLine


class ServiceLineSeedService:
    def __init__(self, db):
        self.db = db

    def seed_default_structure(self, *, clinic_id: UUID) -> None:
        gopd_dep = self._ensure_department(clinic_id=clinic_id, name="GOPD")
        specialist_dep = self._ensure_department(clinic_id=clinic_id, name="Specialist")
        maternity_dep = self._ensure_department(clinic_id=clinic_id, name="Maternity")
        ae_dep = self._ensure_department(clinic_id=clinic_id, name="A&E")

        gopd_root = self._ensure_service_line(
            clinic_id=clinic_id,
            name="GOPD",
            parent_id=None,
            department_id=gopd_dep.id,
            requires_doctor=True,
        )
        consultation = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Consultation",
            parent_id=gopd_root.id,
            department_id=None,
            requires_doctor=True,
        )
        gopd_root.default_child_id = consultation.id
        self.db.add(gopd_root)

        specialist = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Specialist",
            parent_id=None,
            department_id=specialist_dep.id,
            requires_doctor=True,
        )
        self._ensure_service_line(
            clinic_id=clinic_id,
            name="Cardiology",
            parent_id=specialist.id,
            department_id=None,
            requires_doctor=True,
        )
        self._ensure_service_line(
            clinic_id=clinic_id,
            name="Orthopaedics",
            parent_id=specialist.id,
            department_id=None,
            requires_doctor=True,
        )

        mch = self._ensure_service_line(
            clinic_id=clinic_id,
            name="Maternal & Child Health",
            parent_id=None,
            department_id=maternity_dep.id,
            requires_doctor=True,
        )
        self._ensure_service_line(
            clinic_id=clinic_id,
            name="ANC",
            parent_id=mch.id,
            department_id=None,
            requires_doctor=True,
        )
        self._ensure_service_line(
            clinic_id=clinic_id,
            name="Maternity",
            parent_id=mch.id,
            department_id=None,
            requires_doctor=True,
        )

        self._ensure_service_line(
            clinic_id=clinic_id,
            name="A&E",
            parent_id=None,
            department_id=ae_dep.id,
            requires_doctor=False,
        )
        self._ensure_service_line(
            clinic_id=clinic_id,
            name="Legacy / Unspecified",
            parent_id=None,
            department_id=None,
            requires_doctor=False,
        )
        self.db.flush()

    def link_owner_to_all_leaf_service_lines(self, *, clinic_id: UUID, owner_user_id: UUID) -> None:
        all_lines = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.is_active == True,
                ServiceLine.requires_doctor == True,
            )
            .all()
        )
        children = {line.parent_id for line in all_lines if line.parent_id is not None}
        leaf_ids = [line.id for line in all_lines if line.id not in children]
        for leaf_id in leaf_ids:
            existing = (
                self.db.query(DoctorServiceLine)
                .filter(
                    DoctorServiceLine.doctor_id == owner_user_id,
                    DoctorServiceLine.service_line_id == leaf_id,
                )
                .first()
            )
            if existing:
                continue
            self.db.add(
                DoctorServiceLine(
                    doctor_id=owner_user_id,
                    service_line_id=leaf_id,
                )
            )

    def _ensure_department(self, *, clinic_id: UUID, name: str) -> Department:
        existing = (
            self.db.query(Department)
            .filter(
                Department.clinic_id == clinic_id,
                Department.name.ilike(name),
            )
            .first()
        )
        if existing:
            return existing
        department = Department(
            clinic_id=clinic_id,
            name=name,
        )
        self.db.add(department)
        self.db.flush()
        return department

    def _ensure_service_line(
        self,
        *,
        clinic_id: UUID,
        name: str,
        parent_id: UUID | None,
        department_id: UUID | None,
        requires_doctor: bool,
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
        if existing:
            existing.department_id = department_id
            existing.requires_doctor = requires_doctor
            existing.is_active = True
            self.db.add(existing)
            self.db.flush()
            return existing

        line = ServiceLine(
            clinic_id=clinic_id,
            name=name,
            parent_id=parent_id,
            department_id=department_id,
            requires_doctor=requires_doctor,
            is_active=True,
        )
        self.db.add(line)
        self.db.flush()
        return line
