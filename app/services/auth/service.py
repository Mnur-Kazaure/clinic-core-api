# app/services/auth/service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.clinic import Clinic
from app.models.user import User
from app.shared.enums import UserRole
from app.core.auth.passwords import hash_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_clinic(self, payload):
        # 🔒 Enforce single-clinic invariant
        existing_clinic = self.db.query(Clinic).first()
        if existing_clinic:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Clinic already registered",
            )

        # 🔒 Enforce unique admin identity
        if self.db.query(User).filter(User.email == payload.admin_email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        try:
            clinic = Clinic(name=payload.clinic_name)
            self.db.add(clinic)
            self.db.flush()  # obtain clinic.id

            admin = User(
                email=payload.admin_email,
                password_hash=hash_password(payload.admin_password),
                role=UserRole.CLINIC_ADMIN,
                clinic_id=clinic.id,
                is_active=True,
            )
            self.db.add(admin)

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return clinic, admin