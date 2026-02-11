import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.clinic import Clinic
from app.models.user import User
from app.schemas.patient import PatientCreateSchema
from app.services.patient_service import PatientService
from app.shared.enums import (
    Gender,
    UserRole,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


def _patient_payload():
    return PatientCreateSchema(
        full_name="John Doe",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="08012345678",
        address="123 Main St",
        occupation="Teacher",
        identity_state=None,
        created_reason=None,
    )


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_registration_fee_requires_payment_method_postgres():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url

    db = SessionLocal()
    try:
        clinic = Clinic(
            id=uuid.uuid4(),
            name="Clinic A",
            billing_currency="NGN",
            registration_fee_minor=5000,
            registration_fee_required=True,
        )
        db.add(clinic)
        db.commit()

        receptionist = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"reception_{clinic.id}@example.test",
            password_hash="test",
            full_name="Reception User",
            role=UserRole.RECEPTION,
            is_active=True,
        )
        db.add(receptionist)
        db.commit()

        payload = _patient_payload()

        service = PatientService(db)
        patient = service.create_patient(payload, receptionist)
        assert patient.id is not None
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_registration_fee_creates_ledger_entries_postgres():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url

    db = SessionLocal()
    try:
        clinic = Clinic(
            id=uuid.uuid4(),
            name="Clinic A",
            billing_currency="NGN",
            registration_fee_minor=2500,
            registration_fee_required=True,
        )
        db.add(clinic)
        db.commit()

        receptionist = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"reception_{clinic.id}@example.test",
            password_hash="test",
            full_name="Reception User",
            role=UserRole.RECEPTION,
            is_active=True,
        )
        db.add(receptionist)
        db.commit()

        payload = _patient_payload()
        service = PatientService(db)
        patient = service.create_patient(payload, receptionist)

        entries = (
            db.query(BillingLedgerEntry)
            .filter(BillingLedgerEntry.patient_id == patient.id)
            .all()
        )
        assert entries == []
    finally:
        db.close()
