"""Seed deterministic users for Playwright role-matrix smoke tests.

This script is idempotent:
- creates/updates one clinic
- creates/updates RECEPTION, CHEW, MIDWIFE, ADMIN users by email

Safety:
- by default, refuses to overwrite non-E2E user accounts
- pass --allow-overwrite-existing only when intentionally reusing real accounts
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
    parser.add_argument("--admin-email", default=None)
    parser.add_argument("--admin-password", default=None)
    parser.add_argument(
        "--allow-overwrite-existing",
        action="store_true",
        help="Allow overwriting existing non-E2E users by email.",
    )
    return parser.parse_args()


def _upsert_user(
    db,
    *,
    clinic_id,
    email: str,
    password: str,
    full_name: str,
    role_value: str,
    allow_overwrite_existing: bool,
) -> None:
    user = db.query(User).filter(User.email == email).first()
    password_hash = _hash_password(password)
    if user:
        is_e2e_account = user.full_name.startswith("E2E ")
        if not allow_overwrite_existing and not is_e2e_account:
            raise RuntimeError(
                "Refusing to overwrite non-E2E user account "
                f"({email}). Re-run with --allow-overwrite-existing only if intentional."
            )
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


def _resolve_role_value(primary: str, fallback: str) -> str:
    """Use newer role when available, otherwise fall back for older branches."""
    role = getattr(UserRole, primary, None)
    if role is not None:
        return role.value
    return getattr(UserRole, fallback).value


def main() -> None:
    args = _parse_args()
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
            allow_overwrite_existing=args.allow_overwrite_existing,
        )
        chew_role_value = _resolve_role_value("CHEW", "DOCTOR")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.chew_email,
            password=args.chew_password,
            full_name="E2E CHEW",
            role_value=chew_role_value,
            allow_overwrite_existing=args.allow_overwrite_existing,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.chew_email),
            password=args.chew_password,
            full_name="E2E CHEW Colleague",
            role_value=chew_role_value,
            allow_overwrite_existing=args.allow_overwrite_existing,
        )
        midwife_role_value = _resolve_role_value("MIDWIFE", "LAB")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.midwife_email,
            password=args.midwife_password,
            full_name="E2E Midwife",
            role_value=midwife_role_value,
            allow_overwrite_existing=args.allow_overwrite_existing,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=_derive_colleague_email(args.midwife_email),
            password=args.midwife_password,
            full_name="E2E Midwife Colleague",
            role_value=midwife_role_value,
            allow_overwrite_existing=args.allow_overwrite_existing,
        )
        clinic_admin_role_value = _resolve_role_value("CLINIC_ADMIN", "ADMIN")
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=admin_email,
            password=admin_password,
            full_name="E2E Clinic Admin",
            role_value=clinic_admin_role_value,
            allow_overwrite_existing=args.allow_overwrite_existing,
        )

        db.commit()
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
