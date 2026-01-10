# app/api/v1/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth.passwords import verify_password
from app.core.auth.jwt import encode_access_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ClinicRegistrationRequest,
)

from app.services.auth.service import AuthService
from app.shared.enums import UserRole

from app.schemas.auth import StaffCreateRequest
from app.core.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


# -----------------------
# Login Endpoint
# -----------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user using email + password
    """
    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .first()
    )

    if not user or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = encode_access_token(
        user_id=user.id,
        # role=user.role,
        role=UserRole(user.role),
        clinic_id=user.clinic_id,
    )

    return TokenResponse(access_token=access_token)


# -----------------------
# Clinic Registration Endpoint
# -----------------------
@router.post(
    "/register-clinic",
    status_code=status.HTTP_201_CREATED,
)
def register_clinic(
    payload: ClinicRegistrationRequest,
    db: Session = Depends(get_db),
):
    clinic, admin = AuthService(db).register_clinic(payload)

    return {
        "clinic_id": str(clinic.id),
        "admin_user_id": str(admin.id),
        "message": "Clinic registered successfully",
    }

# -----------------------
# Staff Provisioning Endpoint
# -----------------------
@router.post(
    "/staff",
    status_code=status.HTTP_201_CREATED,
)
def create_staff(
    payload: StaffCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Provision a staff user under the same clinic.
    Accessible only by Clinic Admin.
    """
    service = AuthService(db)
    user = service.create_staff_user(
        payload=payload,
        current_user=current_user,
    )

    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
        "message": "Staff user created successfully",
    }
