# app/core/guards/pmr_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


PMR_READ_ROLES = {
    UserRole.RECEPTION,
    UserRole.DOCTOR,
    # ANC and maternity owners may view SUMMARY-only PMR for patients in an active
    # visit assigned to them (enforced in PMRService).
    UserRole.CHEW,
    UserRole.MIDWIFE,
    UserRole.CLINIC_ADMIN,
    UserRole.CMD,
}

MRN_ISSUE_ROLES = {
    UserRole.RECEPTION,
    UserRole.CLINIC_ADMIN,
    UserRole.CMD,
}


def require_pmr_read_role(user=Depends(get_current_user)):
    if user.role not in PMR_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PMR access denied",
        )
    return user


def require_mrn_issue_role(user=Depends(get_current_user)):
    if user.role not in MRN_ISSUE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MRN issuance denied",
        )
    return user
