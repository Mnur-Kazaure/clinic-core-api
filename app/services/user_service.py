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
