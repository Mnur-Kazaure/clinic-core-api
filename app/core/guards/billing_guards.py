# app/core/guards/billing_guards.py
from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.shared.enums import LAB_OPERATION_ROLES, UserRole


CHARGE_ROLES = {
    UserRole.CASHIER,
    UserRole.ACCOUNTANT,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
    UserRole.PHARMACY,
    UserRole.PHARMACY_HOD,
} | set(LAB_OPERATION_ROLES)

PAYMENT_ROLES = {
    UserRole.CASHIER,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

REVERSAL_ROLES = {
    UserRole.ACCOUNTANT,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

READ_ROLES = {
    UserRole.CASHIER,
    UserRole.ACCOUNTANT,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

CATALOG_READ_ROLES = {
    UserRole.DOCTOR,
    UserRole.CASHIER,
    UserRole.ACCOUNTANT,
    UserRole.PHARMACY,
    UserRole.PHARMACY_HOD,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
} | set(LAB_OPERATION_ROLES)

REFUND_ROLES = {
    UserRole.ACCOUNTANT,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

SHIFT_ROLES = {
    UserRole.CASHIER,
    UserRole.CLINIC_ADMIN,
    UserRole.ADMIN,
}

RECEIPT_SEQUENCE_ROLES = {
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


def require_billing_catalog_read_role(user=Depends(get_current_user)):
    if user.role not in CATALOG_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Charge catalog access denied",
        )
    return user


def require_billing_refund_role(user=Depends(get_current_user)):
    if user.role not in REFUND_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Billing refund access denied",
        )
    return user


def require_billing_shift_role(user=Depends(get_current_user)):
    if user.role not in SHIFT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashier shift access denied",
        )
    return user


def require_receipt_sequence_admin_role(user=Depends(get_current_user)):
    if user.role not in RECEIPT_SEQUENCE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receipt sequence configuration access denied",
        )
    return user
