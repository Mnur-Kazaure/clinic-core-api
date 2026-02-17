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
from app.models.consultation import Consultation
from app.models.follow_up import FollowUp
from app.models.lab_request import LabRequest
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import (
    FollowUpGeneratedBy,
    LabRequestStatus,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    Gender,
    PrescriptionStatus,
    RecordStatus,
    UserRole,
    VisitServiceLine,
    VisitStatus,
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


def _upsert_patient_fixture(
    db,
    *,
    clinic_id,
    full_name: str,
    phone_number: str,
) -> Patient:
    patient = (
        db.query(Patient)
        .filter(
            Patient.clinic_id == clinic_id,
            Patient.full_name == full_name,
        )
        .first()
    )
    if patient:
        patient.phone_number = phone_number
        return patient

    patient = Patient(
        clinic_id=clinic_id,
        full_name=full_name,
        date_of_birth=date(1990, 1, 1),
        gender=Gender.FEMALE,
        phone_number=phone_number,
        address="E2E Role Action Fixture",
        occupation="E2E Fixture",
    )
    db.add(patient)
    db.flush()
    return patient


def _upsert_visit_fixture(
    db,
    *,
    clinic_id,
    patient_id,
    owner_user_id,
    target_status: VisitStatus,
) -> Visit:
    visit = (
        db.query(Visit)
        .filter(
            Visit.clinic_id == clinic_id,
            Visit.patient_id == patient_id,
            Visit.service_line == VisitServiceLine.OPD,
            Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
        )
        .order_by(Visit.created_at.desc())
        .first()
    )
    if visit is None:
        visit = Visit(
            clinic_id=clinic_id,
            patient_id=patient_id,
            assigned_doctor_id=owner_user_id,
            service_line=VisitServiceLine.OPD,
            status=target_status,
        )
        db.add(visit)
        db.flush()
        return visit

    visit.assigned_doctor_id = owner_user_id
    visit.status = target_status
    visit.service_line = VisitServiceLine.OPD
    visit.completed_at = None
    return visit


def _upsert_role_dashboard_action_fixtures(
    db,
    *,
    clinic_id,
    doctor_user_id,
) -> None:
    now = datetime.now(timezone.utc)

    doctor_patient = _upsert_patient_fixture(
        db,
        clinic_id=clinic_id,
        full_name="E2E Doctor Queue Action",
        phone_number="08000000002",
    )
    _upsert_visit_fixture(
        db,
        clinic_id=clinic_id,
        patient_id=doctor_patient.id,
        owner_user_id=doctor_user_id,
        target_status=VisitStatus.IN_CONSULTATION,
    )

    lab_patient = _upsert_patient_fixture(
        db,
        clinic_id=clinic_id,
        full_name="E2E Lab Queue Action",
        phone_number="08000000003",
    )
    lab_visit = _upsert_visit_fixture(
        db,
        clinic_id=clinic_id,
        patient_id=lab_patient.id,
        owner_user_id=doctor_user_id,
        target_status=VisitStatus.LAB_REQUESTED,
    )
    lab_request = (
        db.query(LabRequest)
        .filter(
            LabRequest.clinic_id == clinic_id,
            LabRequest.visit_id == lab_visit.id,
            LabRequest.test_name == "E2E Full Blood Count",
        )
        .order_by(LabRequest.created_at.desc())
        .first()
    )
    if lab_request is None:
        lab_request = LabRequest(
            clinic_id=clinic_id,
            visit_id=lab_visit.id,
            requested_by=doctor_user_id,
            test_name="E2E Full Blood Count",
            special_instructions="Role action smoke fixture",
            status=LabRequestStatus.PENDING,
            created_at=now,
        )
        db.add(lab_request)
    else:
        lab_request.requested_by = doctor_user_id
        lab_request.status = LabRequestStatus.PENDING
        lab_request.completed_at = None
        lab_request.special_instructions = "Role action smoke fixture"

    pharmacy_patient = _upsert_patient_fixture(
        db,
        clinic_id=clinic_id,
        full_name="E2E Pharmacy Queue Action",
        phone_number="08000000004",
    )
    pharmacy_visit = _upsert_visit_fixture(
        db,
        clinic_id=clinic_id,
        patient_id=pharmacy_patient.id,
        owner_user_id=doctor_user_id,
        target_status=VisitStatus.PHARMACY_PENDING,
    )
    consultation = (
        db.query(Consultation)
        .filter(Consultation.visit_id == pharmacy_visit.id)
        .first()
    )
    if consultation is None:
        consultation = Consultation(
            visit_id=pharmacy_visit.id,
            clinic_id=clinic_id,
            doctor_id=doctor_user_id,
            started_at=now,
            completed_at=now,
            record_status=RecordStatus.SIGNED,
            signed_at=now,
            diagnosis="E2E diagnosis for pharmacy queue",
            notes="E2E consultation fixture",
        )
        db.add(consultation)
        db.flush()
    else:
        consultation.clinic_id = clinic_id
        consultation.doctor_id = doctor_user_id
        consultation.record_status = RecordStatus.SIGNED
        consultation.started_at = consultation.started_at or now
        consultation.completed_at = now
        consultation.signed_at = now

    prescription = (
        db.query(Prescription)
        .filter(
            Prescription.clinic_id == clinic_id,
            Prescription.visit_id == pharmacy_visit.id,
            Prescription.drug_name == "Paracetamol 500mg (E2E)",
        )
        .order_by(Prescription.issued_at.desc())
        .first()
    )
    if prescription is None:
        prescription = Prescription(
            consultation_id=consultation.id,
            visit_id=pharmacy_visit.id,
            clinic_id=clinic_id,
            prescribed_by=doctor_user_id,
            drug_name="Paracetamol 500mg (E2E)",
            dosage="1 tablet",
            frequency="TDS",
            duration="3 days",
            instructions="After meals",
            status=PrescriptionStatus.ISSUED,
            record_status=RecordStatus.SIGNED,
            issued_at=now,
            signed_at=now,
        )
        db.add(prescription)
    else:
        prescription.consultation_id = consultation.id
        prescription.prescribed_by = doctor_user_id
        prescription.status = PrescriptionStatus.ISSUED
        prescription.record_status = RecordStatus.SIGNED
        prescription.signed_at = now
        prescription.issued_at = now
        prescription.dispensed_by = None
        prescription.dispensed_at = None
        prescription.cancelled_at = None


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
        doctor_user = db.query(User).filter(User.email == doctor_email).first()
        if chew_user and reception_user:
            _upsert_reception_follow_up_fixture(
                db,
                clinic_id=clinic.id,
                created_by=reception_user.id,
                owner_user_id=chew_user.id,
            )
        if doctor_user:
            _upsert_role_dashboard_action_fixtures(
                db,
                clinic_id=clinic.id,
                doctor_user_id=doctor_user.id,
            )

        db.commit()
        print("Seeded Playwright users successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
