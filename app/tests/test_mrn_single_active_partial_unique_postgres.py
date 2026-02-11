import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.shared.enums import Gender, UserRole, MRNStatus


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_mrn_single_active_partial_unique_postgres():
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
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Admin",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="MRN Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        mrn_a = PatientMRN(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            mrn="AAA-0000001-1",
            status=MRNStatus.ACTIVE,
            issued_at=datetime.now(timezone.utc),
            issued_by=admin.id,
            check_digit="1",
        )
        mrn_b = PatientMRN(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            mrn="AAA-0000002-2",
            status=MRNStatus.ACTIVE,
            issued_at=datetime.now(timezone.utc),
            issued_by=admin.id,
            check_digit="2",
        )
        db.add(mrn_a)
        db.commit()
        db.add(mrn_b)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
    finally:
        db.close()
