import os
import uuid
from datetime import date
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
from app.models.access_log import AccessLog
from app.shared.enums import Gender, PurposeOfUse, UserRole


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_break_glass_requires_justification_length():
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

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"doctor.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Test Doctor",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(doctor)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Audit Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        log = AccessLog(
            id=uuid.uuid4(),
            actor_id=doctor.id,
            actor_role=doctor.role,
            clinic_id=clinic.id,
            patient_id=patient.id,
            action="BREAK_GLASS",
            purpose_of_use=PurposeOfUse.EMERGENCY,
            justification="short",
            resource="PATIENT_CHART",
            break_glass=True,
        )
        db.add(log)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()
    finally:
        db.close()
