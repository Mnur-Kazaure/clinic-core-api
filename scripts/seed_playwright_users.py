"""Seed deterministic users for Playwright role-matrix smoke tests.

This script is idempotent:
- creates/updates one clinic
- creates/updates RECEPTION, CHEW, MIDWIFE, DOCTOR, LAB, PHARMACY, ADMIN users by email
"""

from __future__ import annotations

import argparse

import bcrypt

from app.core.database import SessionLocal
from app.models.clinic import Clinic
from app.models.user import User
from app.shared.enums import UserRole


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Playwright e2e users")
    parser.add_argument("--clinic-name", default="Playwright E2E Clinic")
    parser.add_argument("--reception-email", required=True)
    parser.add_argument("--reception-password", required=True)
    parser.add_argument("--chew-email", required=True)
    parser.add_argument("--chew-password", required=True)
    parser.add_argument("--midwife-email", required=True)
    parser.add_argument("--midwife-password", required=True)
    parser.add_argument("--doctor-email", default=None)
    parser.add_argument("--doctor-password", default=None)
    parser.add_argument("--lab-email", default=None)
    parser.add_argument("--lab-password", default=None)
    parser.add_argument("--pharmacy-email", default=None)
    parser.add_argument("--pharmacy-password", default=None)
    parser.add_argument("--admin-email", default=None)
    parser.add_argument("--admin-password", default=None)
    return parser.parse_args()


def _upsert_user(
    db,
    *,
    clinic_id,
    email: str,
    password: str,
    full_name: str,
    role_value: str,
) -> None:
    user = db.query(User).filter(User.email == email).first()
    password_hash = _hash_password(password)
    if user:
        user.clinic_id = clinic_id
        user.full_name = full_name
        user.role = role_value
        user.password_hash = password_hash
        user.is_active = True
        return

    db.add(
        User(
            clinic_id=clinic_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role_value,
            is_active=True,
        )
        )


def _hash_password(password: str) -> str:
    # Keep seeding independent from passlib backend quirks in CI.
    truncated = password.encode("utf-8")[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def _derive_colleague_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+colleague@{domain}"


def _derive_admin_email(email: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+admin@{domain}"


def _derive_role_email(email: str, suffix: str) -> str:
    local, domain = email.split("@", 1)
    return f"{local}+{suffix}@{domain}"


def _resolve_role_value(primary: str, fallback: str) -> str:
    """Use newer role when available, otherwise fall back for older branches."""
    role = getattr(UserRole, primary, None)
    if role is not None:
        return role.value
    return getattr(UserRole, fallback).value


def main() -> None:
    args = _parse_args()
    doctor_email = args.doctor_email or _derive_role_email(args.reception_email, "doctor")
    doctor_password = args.doctor_password or args.reception_password
    lab_email = args.lab_email or _derive_role_email(args.reception_email, "lab")
    lab_password = args.lab_password or args.reception_password
    pharmacy_email = args.pharmacy_email or _derive_role_email(
        args.reception_email, "pharmacy"
    )
    pharmacy_password = args.pharmacy_password or args.reception_password
    admin_email = args.admin_email or _derive_admin_email(args.reception_email)
    admin_password = args.admin_password or args.reception_password
    db = SessionLocal()
    try:
        clinic = db.query(Clinic).filter(Clinic.name == args.clinic_name).first()
        if not clinic:
            clinic = Clinic(name=args.clinic_name)
            db.add(clinic)
            db.flush()

        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.reception_email,
            password=args.reception_password,
            full_name="E2E Reception",
            role_value=UserRole.RECEPTION.value,
        )
        chew_role_value = _resolve_role_value("CHEW", "DOCTOR")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.chew_email,
            password=args.chew_password,
            full_name="E2E CHEW",
            role_value=chew_role_value,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.chew_email),
            password=args.chew_password,
            full_name="E2E CHEW Colleague",
            role_value=chew_role_value,
        )
        midwife_role_value = _resolve_role_value("MIDWIFE", "LAB")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.midwife_email,
            password=args.midwife_password,
            full_name="E2E Midwife",
            role_value=midwife_role_value,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.midwife_email),
            password=args.midwife_password,
            full_name="E2E Midwife Colleague",
            role_value=midwife_role_value,
        )
        doctor_role_value = _resolve_role_value("DOCTOR", "CHEW")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=doctor_email,
            password=doctor_password,
            full_name="E2E Doctor",
            role_value=doctor_role_value,
        )
        lab_role_value = _resolve_role_value("LAB", "MIDWIFE")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=lab_email,
            password=lab_password,
            full_name="E2E Lab Technician",
            role_value=lab_role_value,
        )
        pharmacy_role_value = _resolve_role_value("PHARMACY", "RECEPTION")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=pharmacy_email,
            password=pharmacy_password,
            full_name="E2E Pharmacy",
            role_value=pharmacy_role_value,
        )
        clinic_admin_role_value = _resolve_role_value("CLINIC_ADMIN", "ADMIN")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=admin_email,
            password=admin_password,
            full_name="E2E Clinic Admin",
            role_value=clinic_admin_role_value,
        )

        db.commit()
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
