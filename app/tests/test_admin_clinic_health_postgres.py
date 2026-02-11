import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.admin import get_clinic_health
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import Gender, UserRole, VisitStatus


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_admin_clinic_health_snapshot_counts():
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
        clinic = Clinic(id=uuid.uuid4(), name="Clinic A", billing_currency="NGN")
        db.add(clinic)
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"admin_{clinic.id}@example.test",
            password_hash="test",
            full_name="Admin User",
            role=UserRole.CLINIC_ADMIN,
            is_active=True,
        )
        db.add(admin)

        staff = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"staff_{clinic.id}@example.test",
            password_hash="test",
            full_name="Staff Member",
            role=UserRole.RECEPTION,
            is_active=True,
        )
        db.add(staff)

        inactive = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"inactive_{clinic.id}@example.test",
            password_hash="test",
            full_name="Inactive Staff",
            role=UserRole.RECEPTION,
            is_active=False,
        )
        db.add(inactive)

        doctor = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"doctor_{clinic.id}@example.test",
            password_hash="test",
            full_name="Assigned Doctor",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(doctor)

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Patient A",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.MALE,
            phone_number="000",
            address="Test address",
            occupation="Test",
        )
        db.add(patient)

        visit = Visit(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            assigned_doctor_id=doctor.id,
            status=VisitStatus.REGISTERED,
        )
        db.add(visit)
        db.commit()

        snapshot = get_clinic_health(db=db, current_user=admin)
        assert snapshot.active_visits == 1
        assert snapshot.active_staff == 3
    finally:
        db.close()
