import os
import uuid
import pytest
from datetime import datetime, timezone, date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.shared.enums import (
    VisitStatus,
    Gender,
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_priority_event_fk_enforces_clinic_consistency():
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

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            email=f"doc.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Doctor A",
            role="DOCTOR",
            is_active=True,
        )
        db.add(doctor)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_a.id,
            full_name="Priority Patient",
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
            assigned_doctor_id=doctor.id,
            status=VisitStatus.IN_CONSULTATION,
            started_at=datetime.now(timezone.utc),
        )
        db.add(visit)
        db.commit()

        # Mismatched clinic_id should violate composite FK
        priority_event = ClinicalPriorityEvent(
            id=uuid.uuid4(),
            clinic_id=clinic_b.id,
            visit_id=visit.id,
            patient_id=patient.id,
            level=ClinicalPriorityLevel.CRITICAL,
            source=ClinicalPrioritySource.CLINICIAN,
            reason="needs immediate care",
            set_by=doctor.id,
            set_at=datetime.now(timezone.utc),
        )
        db.add(priority_event)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
