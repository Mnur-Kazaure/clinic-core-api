# app/services/user_service.py
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.doctor_service_line import DoctorServiceLine
from app.models.user import User
from app.models.user_department import UserDepartment
from app.shared.enums import UserRole


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def list_doctors(self, clinic_id):
        return (
            self.db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role == UserRole.DOCTOR.value,
#                User.role == UserRole.DOCTOR,
                User.is_active == True,
            )
            .all()
        )

    def list_by_role(self, clinic_id, role: UserRole):
        return (
            self.db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role == role.value,
                User.is_active == True,
            )
            .all()
        )

    def list_by_roles(self, clinic_id, roles: list[UserRole]):
        role_values = [role.value for role in roles]
        return (
            self.db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role.in_(role_values),
                User.is_active == True,
            )
            .order_by(User.role.asc(), User.full_name.asc(), User.email.asc())
            .all()
        )

    def list_assignable_staff(
        self,
        clinic_id,
        *,
        service_line_id=None,
        role_filter: UserRole | None = None,
        department_id=None,
        include_all_departments: bool = False,
    ):
        q = self.db.query(User).filter(
            User.clinic_id == clinic_id,
            User.is_active == True,
        )

        if role_filter is not None:
            q = q.filter(User.role == role_filter.value)
        else:
            q = q.filter(
                User.role.in_(
                    [
                        UserRole.DOCTOR.value,
                        UserRole.CHEW.value,
                        UserRole.MIDWIFE.value,
                    ]
                )
            )

        if service_line_id is not None:
            q = q.join(
                DoctorServiceLine,
                DoctorServiceLine.doctor_id == User.id,
            ).filter(DoctorServiceLine.service_line_id == service_line_id)

        if not include_all_departments and department_id is not None:
            q = q.join(
                UserDepartment,
                UserDepartment.user_id == User.id,
            ).join(
                Department,
                Department.id == UserDepartment.department_id,
            ).filter(
                Department.clinic_id == clinic_id,
                UserDepartment.department_id == department_id,
            )

        return (
            q.order_by(User.role.asc(), User.full_name.asc(), User.email.asc())
            .distinct()
            .all()
        )
