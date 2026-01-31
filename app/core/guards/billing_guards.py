# app/core/guards/billing_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import UserRole


CHARGE_ROLES = {
    UserRole.RECEPTION,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
    UserRole.LAB,
    UserRole.PHARMACY,
}

PAYMENT_ROLES = {
    UserRole.RECEPTION,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

REVERSAL_ROLES = {
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

READ_ROLES = {
    UserRole.RECEPTION,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}


def require_billing_charge_role(user=Depends(get_current_user)):
    if user.role not in CHARGE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing charge access denied",
        )
    return user


def require_billing_payment_role(user=Depends(get_current_user)):
    if user.role not in PAYMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing payment access denied",
        )
    return user


def require_billing_reversal_role(user=Depends(get_current_user)):
    if user.role not in REVERSAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing reversal access denied",
        )
    return user


def require_billing_read_role(user=Depends(get_current_user)):
    if user.role not in READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing read access denied",
        )
    return user
