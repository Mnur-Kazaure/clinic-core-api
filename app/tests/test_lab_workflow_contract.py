import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.lab_request import LabRequest
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.schemas.lab import LabResultCreate
from app.services.lab_service import LabService
from app.shared.enums import Gender, LabRequestStatus, UserRole, VisitStatus


def _seed_lab_context(db, clinic_id: uuid.UUID, *, test_name: str):
    clinic = Clinic(id=clinic_id, name="Lab Contract Clinic")
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Contract Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    technician = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-{clinic_id}@example.test",
        password_hash="test",
        full_name="Contract Lab",
        role=UserRole.LAB.value,
        is_active=True,
    )
    db.add_all([doctor, technician])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Lab Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Test address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.LAB_REQUESTED,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        requested_by=doctor.id,
        test_name=test_name,
        status=LabRequestStatus.PENDING,
    )
    db.add(request)
    db.commit()
    return request, technician


def test_complete_lab_request_requires_result(db, clinic_id):
    request, _ = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Fasting)",
    )

    with pytest.raises(HTTPException) as exc:
        LabService(db).complete_lab_request(request.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Cannot complete lab request without recorded results"


def test_record_qualitative_result_allows_empty_unit_and_range(db, clinic_id):
    request, technician = _seed_lab_context(
        db,
        clinic_id,
        test_name="HIV Test",
    )

    result = LabService(db).record_result(
        request.id,
        LabResultCreate(
            result_value="Negative",
            result_unit=None,
            reference_range=None,
            technician_id=technician.id,
        ),
    )

    assert result.result_value == "Negative"
    assert result.result_unit is None
    assert result.reference_range is None


def test_record_quantitative_result_requires_unit_and_reference_range(db, clinic_id):
    request, technician = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Fasting)",
    )

    with pytest.raises(HTTPException) as exc:
        LabService(db).record_result(
            request.id,
            LabResultCreate(
                result_value="5.4",
                result_unit=None,
                reference_range=None,
                technician_id=technician.id,
            ),
        )

    assert exc.value.status_code == 422
    assert (
        exc.value.detail
        == "Unit and reference range are required for quantitative tests"
    )


def test_complete_lab_request_after_result_succeeds(db, clinic_id):
    request, technician = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Fasting)",
    )
    service = LabService(db)
    service.record_result(
        request.id,
        LabResultCreate(
            result_value="5.4",
            result_unit="mmol/L",
            reference_range="3.9 - 5.5 mmol/L",
            technician_id=technician.id,
        ),
    )

    completed = service.complete_lab_request(request.id)
    assert completed.status == LabRequestStatus.COMPLETED
    assert completed.completed_at is not None
