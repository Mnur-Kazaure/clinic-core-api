# app/core/rbac.py
from fastapi import Depends, HTTPException, status
from app.shared.enums import UserRole
from app.core.auth import get_current_user



VISIT_ACCESS_ROLES = {
    UserRole.RECEPTION,
    UserRole.DOCTOR,
    UserRole.LAB,
    UserRole.PHARMACY,
    UserRole.CHEW,
    UserRole.MIDWIFE,
    UserRole.ADMIN,
}


def require_visit_access(user=Depends(get_current_user)):
    # 🔒 Internal system bypass (not HTTP-facing)
    if user.role == UserRole.SYSTEM:
        return user

    if user.role not in VISIT_ACCESS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not allowed to access visit operations",
        )
    return user



# Reception role required
def require_reception(user=Depends(get_current_user)):
    if user.role != UserRole.RECEPTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reception access required",
        )
    return user



# Doctor role required
def require_doctor(user=Depends(get_current_user)):
    if user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )
    return user


def require_chew(user=Depends(get_current_user)):
    if user.role != UserRole.CHEW:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CHEW access required",
        )
    return user


def require_midwife(user=Depends(get_current_user)):
    if user.role != UserRole.MIDWIFE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Midwife access required",
        )
    return user


# Clinic Admin role required
def require_clinic_admin(user=Depends(get_current_user)):
    if user.role != UserRole.CLINIC_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic Admin access required",
        )
    return user
