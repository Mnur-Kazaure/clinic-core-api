# app/core/guards/audit_review_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


AUDIT_REVIEW_ROLES = {UserRole.CLINIC_ADMIN}


def require_audit_review_role(user=Depends(get_current_user)):
    if user.role not in AUDIT_REVIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit review access denied",
        )
    return user
