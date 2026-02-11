# app/services/user_service.py
from sqlalchemy.orm import Session

from app.models.user import User
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

    def list_assignable_staff(self, clinic_id):
        return (
            self.db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role.in_(
                    [
                        UserRole.DOCTOR.value,
                        UserRole.CHEW.value,
                        UserRole.MIDWIFE.value,
                    ]
                ),
                User.is_active == True,
            )
            .order_by(User.role.asc(), User.full_name.asc(), User.email.asc())
            .all()
        )
