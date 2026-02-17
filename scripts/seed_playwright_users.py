"""Seed deterministic users for Playwright role-matrix smoke tests.

This script is idempotent:
- creates/updates one clinic
- creates/updates RECEPTION, CHEW, MIDWIFE, DOCTOR, LAB, PHARMACY, ADMIN users by email
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone

import bcrypt

from app.core.database import SessionLocal
from app.models.clinic import Clinic
from app.models.follow_up import FollowUp
from app.models.patient import Patient
from app.models.user import User
from app.shared.enums import (
    FollowUpGeneratedBy,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    Gender,
    UserRole,
)


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


def _upsert_reception_follow_up_fixture(
    db,
    *,
    clinic_id,
    created_by,
    owner_user_id,
) -> None:
    fixture_patient_name = "E2E Follow-Up Linked Visit"
    fixture_reason = "E2E linked follow-up visit"
    patient = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == clinic_id,
            Patient.full_name == fixture_patient_name,
        )
        .first()
    )
    if not patient:
        patient = Patient(
            clinic_id=clinic_id,
            full_name=fixture_patient_name,
            date_of_birth=date(1995, 1, 1),
            gender=Gender.FEMALE,
            phone_number="08000000001",
            address="E2E Follow-Up Fixture",
            occupation="E2E Fixture",
        )
        db.add(patient)
        db.flush()

    due_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    existing = (
        db.query(FollowUp)
        .filter(
            FollowUp.clinic_id == clinic_id,
            FollowUp.patient_id_canonical == patient.id,
            FollowUp.reason == fixture_reason,
            FollowUp.status.in_([FollowUpStatus.SCHEDULED, FollowUpStatus.MISSED]),
        )
        .order_by(FollowUp.created_at.desc())
        .first()
    )
    if existing:
        existing.status = FollowUpStatus.SCHEDULED
        existing.owner_user_id = owner_user_id
        existing.priority = FollowUpPriority.IMPORTANT
        existing.type = FollowUpType.MANUAL
        existing.due_at = due_at
        existing.generated_by = FollowUpGeneratedBy.USER
        existing.created_by = created_by
        existing.cancel_reason_code = None
        existing.cancel_reason_text = None
        return

    db.add(
        FollowUp(
            clinic_id=clinic_id,
            patient_id_canonical=patient.id,
            type=FollowUpType.MANUAL,
            priority=FollowUpPriority.IMPORTANT,
            status=FollowUpStatus.SCHEDULED,
            due_at=due_at,
            owner_user_id=owner_user_id,
            reason=fixture_reason,
            generated_by=FollowUpGeneratedBy.USER,
            created_by=created_by,
        )
    )


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
        # Session autoflush is disabled; flush before fixture lookups so brand-new
        # users are visible to the follow-up fixture query on fresh databases.
        db.flush()
        # Keep one deterministic follow-up item visible for reception action smoke.
        chew_user = db.query(User).filter(User.email == args.chew_email).first()
        reception_user = db.query(User).filter(User.email == args.reception_email).first()
        if chew_user and reception_user:
            _upsert_reception_follow_up_fixture(
                db,
                clinic_id=clinic.id,
                created_by=reception_user.id,
                owner_user_id=chew_user.id,
            )

        db.commit()
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
