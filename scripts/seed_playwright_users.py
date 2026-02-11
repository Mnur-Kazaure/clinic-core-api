"""Seed deterministic users for Playwright role-matrix smoke tests.

This script is idempotent:
- creates/updates one clinic
- creates/updates RECEPTION, CHEW, MIDWIFE users by email
"""

from __future__ import annotations

import argparse

from app.core.auth.passwords import hash_password
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
    return parser.parse_args()


def _upsert_user(
    db,
    *,
    clinic_id,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
) -> None:
    user = db.query(User).filter(User.email == email).first()
    password_hash = hash_password(password)
    if user:
        user.clinic_id = clinic_id
        user.full_name = full_name
        user.role = role.value
        user.password_hash = password_hash
        user.is_active = True
        return

    db.add(
        User(
            clinic_id=clinic_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role.value,
            is_active=True,
        )
    )


def main() -> None:
    args = _parse_args()
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
            role=UserRole.RECEPTION,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.chew_email,
            password=args.chew_password,
            full_name="E2E CHEW",
            role=UserRole.CHEW,
        )
        _upsert_user(
            db,
            clinic_id=clinic.id,
            email=args.midwife_email,
            password=args.midwife_password,
            full_name="E2E Midwife",
            role=UserRole.MIDWIFE,
        )

        db.commit()
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
