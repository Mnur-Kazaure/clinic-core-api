# app/core/guards/identity_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


PROVISIONAL_ROLES = {
    UserRole.RECEPTION,
    UserRole.CLINIC_ADMIN,
}

APPROVAL_ROLES = {
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}

CASE_ROLES = {
    UserRole.ADMIN,
    UserRole.CLINIC_ADMIN,
}


def require_provisional_role(user=Depends(get_current_user)):
    if user.role not in PROVISIONAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identity provisional access denied",
        )
    return user


def require_identity_approval_role(user=Depends(get_current_user)):
    if user.role not in APPROVAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identity approval access denied",
        )
    return user


def require_identity_case_role(user=Depends(get_current_user)):
    if user.role not in CASE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Identity case access denied",
        )
    return user
