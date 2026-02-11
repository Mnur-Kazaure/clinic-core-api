import os
import uuid
from datetime import datetime, timezone, date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_intake_flag import VisitIntakeFlag
from app.shared.enums import Gender, VisitStatus


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_intake_flag_append_only_enforced():
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

        reception = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"reception.{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Reception",
            role="RECEPTION",
            is_active=True,
        )
        db.add(reception)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Flag Patient",
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
            clinic_id=clinic.id,
            patient_id=patient.id,
            assigned_doctor_id=reception.id,
            status=VisitStatus.REGISTERED,
            started_at=datetime.now(timezone.utc),
        )
        db.add(visit)
        db.commit()

        flag = VisitIntakeFlag(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            visit_id=visit.id,
            flagged=True,
            reason="emergency intake",
            set_by=reception.id,
            set_at=datetime.now(timezone.utc),
        )
        db.add(flag)
        db.commit()

        flag.reason = "updated"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        db.delete(flag)
        with pytest.raises(DBAPIError):
            db.commit()
    finally:
        db.close()
