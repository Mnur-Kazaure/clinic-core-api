import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.lab_request import LabRequest
from app.models.lab_specimen import LabSpecimen
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.schemas.lab import LabResultCreate
from app.services.lab_service import LabService
from app.schemas.lab_safety import LabResultReleaseRequest
from app.services.lab_safety_service import LabSafetyService
from app.shared.enums import (
    Gender,
    LabRequestStatus,
    LabSpecimenStatus,
    UserRole,
    VisitStatus,
)


def _seed_lab_context(db, clinic_id: uuid.UUID, *, test_name: str):
    clinic = Clinic(id=clinic_id, name="Lab Contract Clinic")
    db.add(clinic)
    db.commit()

    unit = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Contract Lab Unit",
        parent_id=None,
        department_id=None,
        default_child_id=None,
        requires_doctor=False,
        is_active=True,
    )
    db.add(unit)
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
    supervisor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-supervisor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Contract Lab Supervisor",
        role=UserRole.LAB_SUPERVISOR.value,
        is_active=True,
    )
    db.add_all([doctor, technician, supervisor])
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
        target_unit_id=unit.id,
        status=LabRequestStatus.PENDING,
    )
    db.add(request)
    db.commit()

    specimen = LabSpecimen(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        accession_number=f"LAB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{clinic_id.hex[:5].upper()}",
        request_item_id=request.id,
        target_unit_id=unit.id,
        specimen_type="Blood",
        specimen_source="blood",
        status=LabSpecimenStatus.RECEIVED,
        collected_by=technician.id,
        collected_at=datetime.now(timezone.utc),
        received_by=technician.id,
        received_at=datetime.now(timezone.utc),
    )
    db.add(specimen)
    db.commit()
    return request, technician, supervisor


def test_complete_lab_request_requires_result(db, clinic_id):
    request, _, _ = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Fasting)",
    )

    with pytest.raises(HTTPException) as exc:
        LabService(db).complete_lab_request(request.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Cannot complete lab request without a released result"


def test_record_qualitative_result_allows_empty_unit_and_range(db, clinic_id):
    request, technician, _ = _seed_lab_context(
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
        ),
        technician_id=technician.id,
    )

    assert result.result_value == "Negative"
    assert result.result_unit is None
    assert result.reference_range is None


def test_record_quantitative_result_requires_unit_and_reference_range(db, clinic_id):
    request, technician, _ = _seed_lab_context(
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
            ),
            technician_id=technician.id,
        )

    assert exc.value.status_code == 422
    assert (
        exc.value.detail
        == "Unit and reference range are required for quantitative tests"
    )


def test_complete_lab_request_after_result_succeeds(db, clinic_id):
    request, technician, supervisor = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Fasting)",
    )
    service = LabService(db)
    result = service.record_result(
        request.id,
        LabResultCreate(
            result_value="5.4",
            result_unit="mmol/L",
            reference_range="3.9 - 5.5 mmol/L",
        ),
        technician_id=technician.id,
    )
    LabSafetyService(db).release_result(
        result_id=result.id,
        clinic_id=request.clinic_id,
        actor_id=supervisor.id,
        payload=LabResultReleaseRequest(),
    )

    completed = service.complete_lab_request(request.id)
    assert completed.status == LabRequestStatus.COMPLETED
    assert completed.completed_at is not None


def test_complete_lab_request_response_exposes_visit_transition_context(db, clinic_id):
    request, technician, supervisor = _seed_lab_context(
        db,
        clinic_id,
        test_name="Blood Glucose (Random)",
    )
    service = LabService(db)
    result = service.record_result(
        request.id,
        LabResultCreate(
            result_value="6.1",
            result_unit="mmol/L",
            reference_range="3.9 - 7.8 mmol/L",
        ),
        technician_id=technician.id,
    )
    LabSafetyService(db).release_result(
        result_id=result.id,
        clinic_id=request.clinic_id,
        actor_id=supervisor.id,
        payload=LabResultReleaseRequest(),
    )

    completed = service.complete_lab_request(request.id)
    response = service.build_completion_response(lab_request=completed)

    visit = db.query(Visit).filter(Visit.id == request.visit_id).one()
    assert response.lab_request_id == request.id
    assert response.visit_id == request.visit_id
    assert response.status == LabRequestStatus.COMPLETED
    assert response.visit_status == VisitStatus.LAB_REQUESTED
    assert response.visit_ready_for_transition is True
    assert response.suggested_next_visit_status == VisitStatus.LAB_COMPLETED
    assert response.visit_transition_expected_version == visit.version
