# app/core/guards/admission_guards.py
from uuid import UUID
from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.models.admission import Admission
from app.shared.enums import UserRole


ADMISSION_ROLES = {
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}

ADMISSION_REQUEST_ROLES = {
    UserRole.DOCTOR,
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}

ADMISSION_DECISION_ROLES = {
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}


def require_admission_role(user=Depends(get_current_user)):
    if user.role not in ADMISSION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admission access denied",
        )
    return user


def require_admission_request_role(user=Depends(get_current_user)):
    if user.role not in ADMISSION_REQUEST_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admission request access denied",
        )
    return user


def require_admission_decision_role(user=Depends(get_current_user)):
    if user.role not in ADMISSION_DECISION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admission approval access denied",
        )
    return user


def require_admission_access(
    admission_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> Admission:
    admission = (
        db.query(Admission)
        .filter(Admission.id == admission_id)
        .first()
    )
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admission not found",
        )
    if admission.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )
    if current_user.role not in ADMISSION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admission access denied",
        )
    return admission
