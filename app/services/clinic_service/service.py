# app/services/auth/service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.clinic import Clinic
from app.models.service_line import ServiceLine
from app.models.user import User
from app.schemas.clinic import StaffLabUnitResponse, StaffResponse
from app.services.lab_catalog_seed_service import LabCatalogSeedService
from app.services.lab_unit_access_service import LabUnitAccessService
from app.services.pharmacy_seed_service import PharmacySeedService
from app.shared.enums import UserRole
from app.core.auth.passwords import hash_password
from app.services.service_line_seed_service import ServiceLineSeedService


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

            ServiceLineSeedService(self.db).seed_default_structure(
                clinic_id=clinic.id
            )
            PharmacySeedService(self.db).seed_kazaure_structure(
                clinic_id=clinic.id,
                commit=False,
            )
            LabCatalogSeedService(self.db).seed_kazaure_catalog(
                clinic_id=clinic.id,
                commit=False,
            )

            # Some deployed schemas enforce users.full_name as NOT NULL.
            # Seed the initial admin with a deterministic name from email.
            admin_name = (
                str(payload.admin_email).split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
                or "Clinic Admin"
            )

            admin = User(
                email=payload.admin_email,
                password_hash=hash_password(payload.admin_password),
                full_name=admin_name.title(),
                role=UserRole.CLINIC_ADMIN.value,
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
        normalized_role = self._normalize_staff_role(payload.role)

        if normalized_role not in {
            UserRole.RECEPTION,
            UserRole.CASHIER,
            UserRole.ACCOUNTANT,
            UserRole.CMD,
            UserRole.DOCTOR,
            UserRole.LAB,
            UserRole.LAB_TECH,
            UserRole.LAB_SCIENTIST,
            UserRole.LAB_SUPERVISOR,
            UserRole.LAB_MANAGER,
            UserRole.PHARMACY,
            UserRole.PHARMACY_HOD,
            UserRole.PHARMACY_STORE_OFFICER,
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
            role=normalized_role.value,
            password_hash=hash_password(payload.password),
            is_active=True,
        )

        self.db.add(user)
        self.db.flush()

        LabUnitAccessService(self.db).sync_user_units(
            clinic_id=current_user.clinic_id,
            user=user,
            role=normalized_role,
            allowed_unit_ids=list(payload.allowed_lab_unit_ids),
            default_unit_id=payload.default_lab_unit_id,
        )

        if normalized_role in {UserRole.DOCTOR, UserRole.CHEW, UserRole.MIDWIFE}:
            ServiceLineSeedService(self.db).link_owner_to_all_leaf_service_lines(
                clinic_id=current_user.clinic_id,
                owner_user_id=user.id,
            )

        self.db.commit()
        self.db.refresh(user)

        return user

    def list_staff(self, clinic_id):
        users = (
            self.db.query(User)
            .filter(User.clinic_id == clinic_id)
            .order_by(User.created_at.desc())
            .all()
        )
        return [self._build_staff_response(user=user) for user in users]

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

        next_role = self._normalize_staff_role(UserRole(user.role))
        if payload.role is not None:
            normalized_role = self._normalize_staff_role(payload.role)
            if normalized_role == UserRole.CLINIC_ADMIN or user.role == UserRole.CLINIC_ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Clinic Admin role cannot be reassigned from Staff Management",
                )
            next_role = normalized_role
            user.role = normalized_role.value

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

        if (
            "role" in payload.model_fields_set
            or
            "allowed_lab_unit_ids" in payload.model_fields_set
            or "default_lab_unit_id" in payload.model_fields_set
        ):
            LabUnitAccessService(self.db).sync_user_units(
                clinic_id=current_user.clinic_id,
                user=user,
                role=next_role,
                allowed_unit_ids=payload.allowed_lab_unit_ids if "allowed_lab_unit_ids" in payload.model_fields_set else [],
                default_unit_id=payload.default_lab_unit_id,
            )

        self.db.commit()
        self.db.refresh(user)
        return self._build_staff_response(user=user)

    @staticmethod
    def _normalize_staff_role(role: UserRole) -> UserRole:
        return role

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

    def _build_staff_response(self, *, user: User) -> StaffResponse:
        lab_units = LabUnitAccessService(self.db).list_user_units(
            clinic_id=user.clinic_id,
            user_id=user.id,
        )
        default_lab_unit_name = None
        if user.default_lab_unit_id is not None:
            default_lab_unit_name = (
                self.db.query(ServiceLine.name)
                .filter(
                    ServiceLine.id == user.default_lab_unit_id,
                    ServiceLine.clinic_id == user.clinic_id,
                )
                .scalar()
            )

        return StaffResponse(
            id=user.id,
            clinic_id=user.clinic_id,
            full_name=user.full_name,
            email=user.email,
            role=UserRole(user.role),
            is_active=user.is_active,
            specialty=user.specialty,
            department=user.department,
            room_label=user.room_label,
            availability_status=user.availability_status,
            default_lab_unit_id=user.default_lab_unit_id,
            default_lab_unit_name=default_lab_unit_name,
            allowed_lab_units=[
                StaffLabUnitResponse(id=unit.id, name=unit.name)
                for unit in lab_units
            ],
        )

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
