import os
import uuid
import pytest
from datetime import datetime, timezone
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
from app.models.admission import Admission
from app.models.ward import Ward
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.shared.enums import AdmissionType, AdmissionStatus, WardType, BedStatus, BedAssignmentType, Gender


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_bed_occupancy_unique_constraints():
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
            role="ADMIN",
            is_active=True,
        )
        db.add(admin)
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Bed Patient",
            date_of_birth=datetime(2000, 1, 1).date(),
            gender=Gender.MALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        db.add(patient)
        db.commit()

        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission)
        db.commit()

        ward = Ward(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            name="Ward A",
            ward_type=WardType.GENERAL,
            active=True,
        )
        db.add(ward)
        db.commit()

        bed_a = Bed(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="A1",
            status=BedStatus.AVAILABLE,
            active=True,
        )
        bed_b = Bed(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            ward_id=ward.id,
            bed_label="A2",
            status=BedStatus.AVAILABLE,
            active=True,
        )
        db.add_all([bed_a, bed_b])
        db.commit()

        assignment = BedAssignment(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            admission_id=admission.id,
            bed_id=bed_a.id,
            assigned_by=admin.id,
            assignment_type=BedAssignmentType.ASSIGN,
            assigned_at=datetime.now(timezone.utc),
        )
        db.add(assignment)
        db.commit()

        # Same admission cannot have two active beds
        conflict = BedAssignment(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            admission_id=admission.id,
            bed_id=bed_b.id,
            assigned_by=admin.id,
            assignment_type=BedAssignmentType.ASSIGN,
            assigned_at=datetime.now(timezone.utc),
        )
        db.add(conflict)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Same bed cannot be active for another admission
        patient_b = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Bed Patient B",
            date_of_birth=datetime(2001, 1, 1).date(),
            gender=Gender.MALE,
            phone_number="001",
            address="Test B",
            occupation="Test",
        )
        db.add(patient_b)
        db.commit()

        admission_b = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient_b.id,
            admission_type=AdmissionType.ELECTIVE,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add(admission_b)
        db.commit()

        conflict_bed = BedAssignment(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            admission_id=admission_b.id,
            bed_id=bed_a.id,
            assigned_by=admin.id,
            assignment_type=BedAssignmentType.ASSIGN,
            assigned_at=datetime.now(timezone.utc),
        )
        db.add(conflict_bed)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
