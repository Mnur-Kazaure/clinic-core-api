import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.bed_assignment import BedAssignment
from app.models.patient import Patient
from app.models.user import User
from app.models.ward import Ward
from app.services.admission_service import AdmissionService
from app.services.bed_service import BedService
from app.shared.enums import (
    AdmissionDischargeDisposition,
    AdmissionStatus,
    AdmissionType,
    BedAssignmentType,
    BedStatus,
    Gender,
    UserRole,
    WardType,
)


def _admin(clinic_id):
    return User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.test",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )


def _patient(clinic_id):
    return Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )


def test_cancel_admission_releases_active_bed_assignment(db, clinic_id):
    admin = _admin(clinic_id)
    patient = _patient(clinic_id)
    db.add_all([admin, patient])
    db.commit()

    admission_service = AdmissionService(db)
    admission = admission_service.create_admission(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        actor=admin,
    )

    ward = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Ward A",
        ward_type=WardType.GENERAL,
        active=True,
    )
    bed = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        ward_id=ward.id,
        bed_label="A1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    db.add_all([ward, bed])
    db.commit()

    BedService(db).assign_bed(
        admission_id=admission.id,
        bed_id=bed.id,
        actor=admin,
    )

    cancelled = admission_service.cancel_admission(
        admission_id=admission.id,
        actor=admin,
        reason="Created in error",
    )
    assert cancelled.status == AdmissionStatus.CANCELLED

    assignment = (
        db.query(BedAssignment)
        .filter(BedAssignment.admission_id == admission.id)
        .first()
    )
    assert assignment is not None
    assert assignment.released_at is not None


def test_discharge_transfer_out_requires_destination(db, clinic_id):
    admin = _admin(clinic_id)
    patient = _patient(clinic_id)
    db.add_all([admin, patient])
    db.commit()

    admission = Admission(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        admission_type=AdmissionType.ELECTIVE,
        status=AdmissionStatus.ACTIVE,
        admitted_at=datetime.now(timezone.utc),
    )
    db.add(admission)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        AdmissionService(db).discharge_admission(
            admission_id=admission.id,
            actor=admin,
            disposition=AdmissionDischargeDisposition.TRANSFERRED_OUT,
        )
    assert exc.value.status_code == 422


def test_discharge_deceased_requires_pronounced_at(db, clinic_id):
    admin = _admin(clinic_id)
    patient = _patient(clinic_id)
    db.add_all([admin, patient])
    db.commit()

    admission = Admission(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        admission_type=AdmissionType.ELECTIVE,
        status=AdmissionStatus.ACTIVE,
        admitted_at=datetime.now(timezone.utc),
    )
    db.add(admission)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        AdmissionService(db).discharge_admission(
            admission_id=admission.id,
            actor=admin,
            disposition=AdmissionDischargeDisposition.DECEASED,
        )
    assert exc.value.status_code == 422

