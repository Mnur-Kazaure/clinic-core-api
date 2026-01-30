import os
import uuid
import pytest
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.base import Base
from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.consultation import Consultation
from app.shared.enums import VisitStatus, Gender, RecordStatus


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_postgres_fk_enforces_clinic_consistency():
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
        clinic_a = Clinic(id=uuid.uuid4(), name="Clinic A")
        clinic_b = Clinic(id=uuid.uuid4(), name="Clinic B")
        db.add_all([clinic_a, clinic_b])
        db.commit()

        doctor_a = User(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            email=f"doctor.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Doctor A",
            role="doctor",
        )
        db.add(doctor_a)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            full_name="FK Patient",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor_a.id,
            status=VisitStatus.IN_CONSULTATION,
        )
        db.add(visit)
        db.commit()

        # Mismatched clinic_id should violate composite FK
        consultation = Consultation(
            id=uuid.uuid4(),
            visit_id=visit.id,
            clinic_id=clinic_b.id,
            doctor_id=doctor_a.id,
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            record_status=RecordStatus.DRAFT,
        )
        db.add(consultation)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
