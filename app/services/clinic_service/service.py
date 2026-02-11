# app/services/auth/service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.clinic import Clinic
from app.models.user import User
from app.shared.enums import UserRole
from app.core.auth.passwords import hash_password


class ClinicService:
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

    def create_staff_user(self, *, payload, current_user):
        """
        Create a staff user within the same clinic.
        Only Clinic Admin is allowed to perform this action.
        """

        # 🔒 Only Clinic Admin
        if current_user.role != UserRole.CLINIC_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Clinic Admin may create staff",
            )

        # 🔒 Allowed staff roles only
        if payload.role not in {
            UserRole.RECEPTION,
            UserRole.DOCTOR,
            UserRole.LAB,
            UserRole.PHARMACY,
            UserRole.CHEW,
            UserRole.MIDWIFE,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid staff role",
            )

        # 🔒 Email uniqueness
        exists = (
            self.db.query(User)
            .filter(User.email == payload.email)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists",
            )

        user = User(
            clinic_id=current_user.clinic_id,
            full_name=payload.full_name,
            email=payload.email,
            role=payload.role.value,
            password_hash=hash_password(payload.password),
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def list_staff(self, clinic_id):
        return (
            self.db.query(User)
            .filter(User.clinic_id == clinic_id)
            .order_by(User.created_at.desc())
            .all()
        )

    def update_staff_user(self, *, staff_id, payload, current_user):
        if current_user.role != UserRole.CLINIC_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Clinic Admin may update staff",
            )

        user = (
            self.db.query(User)
            .filter(
                User.id == staff_id,
                User.clinic_id == current_user.clinic_id,
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff user not found",
            )

        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.specialty is not None:
            user.specialty = payload.specialty
        if payload.department is not None:
            user.department = payload.department
        if payload.room_label is not None:
            user.room_label = payload.room_label
        if payload.availability_status is not None:
            user.availability_status = payload.availability_status

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_staff_user(self, *, staff_id, current_user):
        if current_user.role != UserRole.CLINIC_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Clinic Admin may delete staff",
            )

        if current_user.id == staff_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clinic Admin cannot delete own account",
            )

        user = (
            self.db.query(User)
            .filter(
                User.id == staff_id,
                User.clinic_id == current_user.clinic_id,
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff user not found",
            )

        if user.role == UserRole.CLINIC_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete Clinic Admin account",
            )

        self.db.delete(user)
        self.db.commit()

    def get_clinic_profile(self, clinic_id):
        clinic = (
            self.db.query(Clinic)
            .filter(Clinic.id == clinic_id)
            .first()
        )
        if not clinic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            )
        return clinic

    def update_clinic_profile(self, *, clinic_id, payload, current_user):
        if current_user.role != UserRole.CLINIC_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Clinic Admin may update clinic profile",
            )

        clinic = self.get_clinic_profile(clinic_id)

        if payload.name is not None:
            clinic.name = payload.name
        if payload.logo_url is not None:
            clinic.logo_url = payload.logo_url
        if payload.address is not None:
            clinic.address = payload.address
        if payload.phone is not None:
            clinic.phone = payload.phone
        if payload.email is not None:
            clinic.email = payload.email
        if payload.timezone is not None:
            clinic.timezone = payload.timezone
        if payload.description is not None:
            clinic.description = payload.description
        if payload.registration_fee_required is not None:
            clinic.registration_fee_required = payload.registration_fee_required
        if payload.registration_fee_minor is not None:
            clinic.registration_fee_minor = payload.registration_fee_minor
        if payload.monthly_revenue_target_minor is not None:
            clinic.monthly_revenue_target_minor = payload.monthly_revenue_target_minor

        if clinic.registration_fee_required and clinic.registration_fee_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration fee is required and must be greater than 0",
            )

        self.db.commit()
        self.db.refresh(clinic)
        return clinic
