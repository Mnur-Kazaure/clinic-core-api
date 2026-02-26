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
from app.models.patient_mrn import PatientMRN
from app.models.user import User
from app.models.ward import Ward
from app.services.bed_service import BedService
from app.shared.enums import (
    AdmissionStatus,
    AdmissionType,
    BedAssignmentType,
    BedStatus,
    Gender,
    MRNStatus,
    WardType,
)


POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


def _migrate(db_url: str) -> None:
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


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL not set")
def test_bed_board_summary_and_tenant_isolation():
    engine = create_engine(POSTGRES_TEST_URL)
    SessionLocal = sessionmaker(bind=engine)
    _migrate(POSTGRES_TEST_URL)

    db = SessionLocal()
    try:
        clinic = Clinic(id=uuid.uuid4(), name="Board Clinic")
        other_clinic = Clinic(id=uuid.uuid4(), name="Other Clinic")
        db.add_all([clinic, other_clinic])
        db.commit()

        admin = User(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            email=f"board-admin-{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Board Admin",
            role="ADMIN",
            is_active=True,
        )
        other_admin = User(
            id=uuid.uuid4(),
            clinic_id=other_clinic.id,
            email=f"board-other-{uuid.uuid4()}@example.com",
            password_hash="test",
            full_name="Other Admin",
            role="ADMIN",
            is_active=True,
        )
        db.add_all([admin, other_admin])
        db.commit()

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name="Board Patient",
            date_of_birth=datetime(2000, 1, 1).date(),
            gender=Gender.FEMALE,
            phone_number="000",
            address="Test",
            occupation="Test",
        )
        other_patient = Patient(
            id=uuid.uuid4(),
            clinic_id=other_clinic.id,
            full_name="Other Patient",
            date_of_birth=datetime(2001, 1, 1).date(),
            gender=Gender.MALE,
            phone_number="111",
            address="Test",
            occupation="Test",
        )
        db.add_all([patient, other_patient])
        db.commit()

        db.add(
            PatientMRN(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                patient_id=patient.id,
                mrn="0000123-4",
                status=MRNStatus.ACTIVE,
                issued_at=datetime.now(timezone.utc),
                issued_by=admin.id,
                check_digit="4",
            )
        )
        db.commit()

        admission = Admission(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        other_admission = Admission(
            id=uuid.uuid4(),
            clinic_id=other_clinic.id,
            patient_id=other_patient.id,
            admission_type=AdmissionType.ELECTIVE,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc),
        )
        db.add_all([admission, other_admission])
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
        other_ward = Ward(
            id=uuid.uuid4(),
            clinic_id=other_clinic.id,
            name="Other Ward",
            ward_type=WardType.GENERAL,
            active=True,
        )
        db.add_all([ward_a, ward_b, other_ward])
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
            status=BedStatus.OUT_OF_SERVICE,
            active=True,
        )
        bed_a3 = Bed(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            ward_id=ward_a.id,
            bed_label="A3",
            status=BedStatus.AVAILABLE,
            active=False,
        )
        bed_b1 = Bed(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            ward_id=ward_b.id,
            bed_label="B1",
            status=BedStatus.AVAILABLE,
            active=True,
        )
        other_bed = Bed(
            id=uuid.uuid4(),
            clinic_id=other_clinic.id,
            ward_id=other_ward.id,
            bed_label="O1",
            status=BedStatus.AVAILABLE,
            active=True,
        )
        db.add_all([bed_a1, bed_a2, bed_a3, bed_b1, other_bed])
        db.commit()

        db.add(
            BedAssignment(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                admission_id=admission.id,
                bed_id=bed_a1.id,
                assigned_by=admin.id,
                assignment_type=BedAssignmentType.ASSIGN,
                assigned_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            BedAssignment(
                id=uuid.uuid4(),
                clinic_id=other_clinic.id,
                admission_id=other_admission.id,
                bed_id=other_bed.id,
                assigned_by=other_admin.id,
                assignment_type=BedAssignmentType.ASSIGN,
                assigned_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

        service = BedService(db)
        board = service.get_bed_board(clinic_id=clinic.id)

        assert board["totals"] == {
            "total_beds": 4,
            "available_beds": 1,
            "occupied_beds": 1,
            "out_of_service_beds": 1,
            "inactive_beds": 1,
        }
        assert len(board["wards"]) == 2

        ward_a_payload = next(
            ward for ward in board["wards"] if ward["summary"]["ward_name"] == "Ward A"
        )
        occupied_bed = next(
            bed for bed in ward_a_payload["beds"] if bed["bed_label"] == "A1"
        )
        assert occupied_bed["occupancy_status"] == "OCCUPIED"
        assert occupied_bed["occupant"]["patient_name"] == "Board Patient"
        assert occupied_bed["occupant"]["patient_mrn"] == "0000123-4"
    finally:
        db.close()
