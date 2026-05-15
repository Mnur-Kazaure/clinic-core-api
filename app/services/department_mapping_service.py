from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.doctor_service_line import DoctorServiceLine
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.user_department import UserDepartment
from app.shared.enums import UserRole


class DepartmentMappingService:
    def __init__(self, db: Session):
        self.db = db

    def list_departments(self, *, clinic_id: UUID) -> list[Department]:
        return (
            self.db.query(Department)
            .filter(Department.clinic_id == clinic_id)
            .order_by(Department.name.asc())
            .all()
        )

    def list_user_departments(self, *, clinic_id: UUID, user_id: UUID) -> list[UserDepartment]:
        self._get_user_in_clinic(clinic_id=clinic_id, user_id=user_id)
        return (
            self.db.query(UserDepartment)
            .join(Department, Department.id == UserDepartment.department_id)
            .filter(
                UserDepartment.user_id == user_id,
                Department.clinic_id == clinic_id,
            )
            .order_by(UserDepartment.is_primary.desc(), UserDepartment.created_at.asc())
            .all()
        )

    def assign_user_department(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        department_id: UUID,
        is_primary: bool,
    ) -> UserDepartment:
        self._get_user_in_clinic(clinic_id=clinic_id, user_id=user_id)
        self._get_department_in_clinic(clinic_id=clinic_id, department_id=department_id)

        existing = (
            self.db.query(UserDepartment)
            .filter(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == department_id,
            )
            .first()
        )

        if existing:
            assignment = existing
            if is_primary:
                self._clear_existing_primary(user_id=user_id)
                assignment.is_primary = True
        else:
            should_be_primary = is_primary or not self._has_primary(user_id=user_id)
            if should_be_primary:
                self._clear_existing_primary(user_id=user_id)

            assignment = UserDepartment(
                id=uuid.uuid4(),
                user_id=user_id,
                department_id=department_id,
                is_primary=should_be_primary,
            )
            self.db.add(assignment)

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def remove_user_department(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        department_id: UUID,
    ) -> None:
        self._get_user_in_clinic(clinic_id=clinic_id, user_id=user_id)
        assignment = (
            self.db.query(UserDepartment)
            .join(Department, Department.id == UserDepartment.department_id)
            .filter(
                UserDepartment.user_id == user_id,
                UserDepartment.department_id == department_id,
                Department.clinic_id == clinic_id,
            )
            .first()
        )
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User department assignment not found",
            )

        was_primary = assignment.is_primary
        self.db.delete(assignment)
        self.db.flush()

        if was_primary:
            replacement = (
                self.db.query(UserDepartment)
                .join(Department, Department.id == UserDepartment.department_id)
                .filter(
                    UserDepartment.user_id == user_id,
                    Department.clinic_id == clinic_id,
                )
                .order_by(UserDepartment.created_at.asc())
                .first()
            )
            if replacement:
                replacement.is_primary = True
                self.db.add(replacement)

        self.db.commit()

    def list_doctor_service_lines(
        self,
        *,
        clinic_id: UUID,
        doctor_id: UUID,
    ) -> list[DoctorServiceLine]:
        self._get_clinical_owner_in_clinic(clinic_id=clinic_id, doctor_id=doctor_id)
        return (
            self.db.query(DoctorServiceLine)
            .join(ServiceLine, ServiceLine.id == DoctorServiceLine.service_line_id)
            .filter(
                DoctorServiceLine.doctor_id == doctor_id,
                ServiceLine.clinic_id == clinic_id,
            )
            .order_by(DoctorServiceLine.created_at.asc())
            .all()
        )

    def assign_doctor_service_line(
        self,
        *,
        clinic_id: UUID,
        doctor_id: UUID,
        service_line_id: UUID,
    ) -> DoctorServiceLine:
        self._get_clinical_owner_in_clinic(clinic_id=clinic_id, doctor_id=doctor_id)
        self._get_service_line_in_clinic(clinic_id=clinic_id, service_line_id=service_line_id)

        existing = (
            self.db.query(DoctorServiceLine)
            .filter(
                DoctorServiceLine.doctor_id == doctor_id,
                DoctorServiceLine.service_line_id == service_line_id,
            )
            .first()
        )
        if existing:
            return existing

        mapping = DoctorServiceLine(
            id=uuid.uuid4(),
            doctor_id=doctor_id,
            service_line_id=service_line_id,
        )
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def remove_doctor_service_line(
        self,
        *,
        clinic_id: UUID,
        doctor_id: UUID,
        service_line_id: UUID,
    ) -> None:
        self._get_clinical_owner_in_clinic(clinic_id=clinic_id, doctor_id=doctor_id)
        mapping = (
            self.db.query(DoctorServiceLine)
            .join(ServiceLine, ServiceLine.id == DoctorServiceLine.service_line_id)
            .filter(
                DoctorServiceLine.doctor_id == doctor_id,
                DoctorServiceLine.service_line_id == service_line_id,
                ServiceLine.clinic_id == clinic_id,
            )
            .first()
        )
        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor service line mapping not found",
            )
        self.db.delete(mapping)
        self.db.commit()

    def user_allowed_department_ids(self, *, clinic_id: UUID, user_id: UUID) -> list[UUID]:
        rows = (
            self.db.query(UserDepartment.department_id)
            .join(Department, Department.id == UserDepartment.department_id)
            .filter(
                UserDepartment.user_id == user_id,
                Department.clinic_id == clinic_id,
            )
            .all()
        )
        return [row.department_id for row in rows]

    def user_primary_department_id(self, *, clinic_id: UUID, user_id: UUID) -> UUID | None:
        row = (
            self.db.query(UserDepartment.department_id)
            .join(Department, Department.id == UserDepartment.department_id)
            .filter(
                UserDepartment.user_id == user_id,
                UserDepartment.is_primary == True,
                Department.clinic_id == clinic_id,
            )
            .first()
        )
        return row.department_id if row else None

    def user_department_context(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
    ) -> list[dict]:
        rows = (
            self.db.query(
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                UserDepartment.is_primary.label("is_primary"),
            )
            .join(UserDepartment, UserDepartment.department_id == Department.id)
            .filter(
                UserDepartment.user_id == user_id,
                Department.clinic_id == clinic_id,
            )
            .order_by(UserDepartment.is_primary.desc(), Department.name.asc())
            .all()
        )
        return [
            {
                "id": row.department_id,
                "name": row.department_name,
                "is_primary": bool(row.is_primary),
            }
            for row in rows
        ]

    def _get_user_in_clinic(self, *, clinic_id: UUID, user_id: UUID) -> User:
        user = (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.clinic_id == clinic_id,
            )
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in clinic",
            )
        return user

    def _get_clinical_owner_in_clinic(self, *, clinic_id: UUID, doctor_id: UUID) -> User:
        user = self._get_user_in_clinic(clinic_id=clinic_id, user_id=doctor_id)
        if user.role not in {
            UserRole.DOCTOR.value,
            UserRole.CHEW.value,
            UserRole.MIDWIFE.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a clinical owner role",
            )
        return user

    def _get_department_in_clinic(self, *, clinic_id: UUID, department_id: UUID) -> Department:
        department = (
            self.db.query(Department)
            .filter(
                Department.id == department_id,
                Department.clinic_id == clinic_id,
            )
            .first()
        )
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found in clinic",
            )
        return department

    def _get_service_line_in_clinic(self, *, clinic_id: UUID, service_line_id: UUID) -> ServiceLine:
        service_line = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.id == service_line_id,
                ServiceLine.clinic_id == clinic_id,
            )
            .first()
        )
        if service_line is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service line not found in clinic",
            )
        return service_line

    def _clear_existing_primary(self, *, user_id: UUID) -> None:
        (
            self.db.query(UserDepartment)
            .filter(UserDepartment.user_id == user_id)
            .update({"is_primary": False}, synchronize_session=False)
        )

    def _has_primary(self, *, user_id: UUID) -> bool:
        return (
            self.db.query(UserDepartment.id)
            .filter(
                UserDepartment.user_id == user_id,
                UserDepartment.is_primary == True,
            )
            .first()
            is not None
        )
