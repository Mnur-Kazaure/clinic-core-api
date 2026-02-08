import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.user import User
from app.models.ward import Ward
from app.services.bed_service import BedService
from app.shared.enums import (
    AdmissionStatus,
    AdmissionType,
    BedAssignmentType,
    BedStatus,
    Gender,
    WardType,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


def _migrate(db_url: str):
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        if original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_database_url


def _seed_context(db):
    clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin User",
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

    ward_a = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Ward A",
        ward_type=WardType.GENERAL,
        active=True,
    )
    ward_b = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Ward B",
        ward_type=WardType.GENERAL,
        active=True,
    )
    ward_inactive = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Closed Ward",
        ward_type=WardType.GENERAL,
        active=False,
    )
    db.add_all([ward_a, ward_b, ward_inactive])
    db.commit()

    bed_a1 = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        ward_id=ward_a.id,
        bed_label="A1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    bed_a2 = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        ward_id=ward_a.id,
        bed_label="A2",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    bed_a3 = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        ward_id=ward_a.id,
        bed_label="A3",
        status=BedStatus.OUT_OF_SERVICE,
        active=True,
    )
    bed_b1 = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        ward_id=ward_b.id,
        bed_label="B1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    db.add_all([bed_a1, bed_a2, bed_a3, bed_b1])
    db.commit()

    assignment = BedAssignment(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        admission_id=admission.id,
        bed_id=bed_a2.id,
        assigned_by=admin.id,
        assignment_type=BedAssignmentType.ASSIGN,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(assignment)
    db.commit()

    return clinic, ward_a, ward_b


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_list_beds_available_only_filters_by_status_and_active_assignment():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic, ward_a, _ = _seed_context(db)
        service = BedService(db)

        beds = service.list_beds(
            clinic_id=clinic.id,
            available_only=True,
        )
        labels = [bed.bed_label for bed in beds]

        assert labels == ["A1", "B1"]

        ward_a_beds = service.list_beds(
            clinic_id=clinic.id,
            available_only=True,
            ward_id=ward_a.id,
        )
        ward_a_labels = [bed.bed_label for bed in ward_a_beds]
        assert ward_a_labels == ["A1"]
    finally:
        db.close()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_list_wards_returns_only_active_wards():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic, _, _ = _seed_context(db)
        service = BedService(db)

        wards = service.list_wards(clinic_id=clinic.id)
        names = [ward.name for ward in wards]

        assert names == ["Ward A", "Ward B"]
    finally:
        db.close()
