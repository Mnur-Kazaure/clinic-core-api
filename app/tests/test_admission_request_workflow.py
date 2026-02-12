import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from app.models.patient import Patient
from app.models.bed import Bed
from app.models.ward import Ward
from app.services.admission_request_service import AdmissionRequestService
from app.services.admission_service import AdmissionService
from app.services.bed_service import BedService
from app.shared.enums import (
    AdmissionType,
    AdmissionStatus,
    AdmissionRequestStatus,
    BedStatus,
    Gender,
    UserRole,
    WardType,
)
from app.models.user import User


def _create_patient(db, clinic_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Admission Request Patient",
        date_of_birth=datetime(2000, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_admin(db, clinic_id):
    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return admin


def test_doctor_request_and_admin_approve(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    service = AdmissionRequestService(db)
    request = service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        reason="Needs observation",
        actor=doctor,
    )
    assert request.status == AdmissionRequestStatus.PENDING

    request, admission = service.approve_request(
        request_id=request.id,
        actor=admin,
        decision_reason="Approved for admission",
    )
    assert request.status == AdmissionRequestStatus.APPROVED
    assert request.admission_id == admission.id
    assert admission.status == AdmissionStatus.ACTIVE
    assert admission.patient_id == patient.id


def test_list_requests_includes_active_bed_state(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    request_service = AdmissionRequestService(db)
    request = request_service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        reason="Needs bed",
        actor=doctor,
    )
    approved_request, admission = request_service.approve_request(
        request_id=request.id,
        actor=admin,
        decision_reason="Approved",
    )

    ward = Ward(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Ward A",
        ward_type=WardType.GENERAL,
        active=True,
    )
    db.add(ward)
    db.commit()

    bed = Bed(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        ward_id=ward.id,
        bed_label="A1",
        status=BedStatus.AVAILABLE,
        active=True,
    )
    db.add(bed)
    db.commit()

    BedService(db).assign_bed(
        admission_id=admission.id,
        bed_id=bed.id,
        actor=admin,
    )

    approved = request_service.list_requests(
        actor=admin,
        status=AdmissionRequestStatus.APPROVED,
    )
    target = next(item for item in approved if item.id == approved_request.id)

    assert target.admission_id == admission.id
    assert target.admission_status == AdmissionStatus.ACTIVE
    assert target.has_active_bed_assignment is True
    assert str(target.current_bed_id) == str(bed.id)
    assert target.current_bed_label == "A1"


def test_reject_request(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    service = AdmissionRequestService(db)
    request = service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.ELECTIVE,
        reason="Schedule admission",
        actor=doctor,
    )

    request = service.reject_request(
        request_id=request.id,
        actor=admin,
        decision_reason="Not necessary",
    )
    assert request.status == AdmissionRequestStatus.REJECTED


def test_only_requester_can_cancel(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    service = AdmissionRequestService(db)
    request = service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.ELECTIVE,
        reason="Schedule admission",
        actor=doctor,
    )

    with pytest.raises(HTTPException) as exc:
        service.cancel_request(
            request_id=request.id,
            actor=admin,
            reason="Cancel by admin",
        )
    assert exc.value.status_code == 403


def test_no_duplicate_pending_requests(db, clinic_id, doctor):
    patient = _create_patient(db, clinic_id)

    service = AdmissionRequestService(db)
    service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        reason="Needs observation",
        actor=doctor,
    )

    with pytest.raises(HTTPException) as exc:
        service.create_request(
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            reason="Duplicate",
            actor=doctor,
        )
    assert exc.value.status_code == 409


def test_request_blocked_when_active_admission(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    admission_service = AdmissionService(db)
    admission = admission_service.create_admission(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        actor=admin,
    )
    assert admission.status == AdmissionStatus.ACTIVE

    request_service = AdmissionRequestService(db)
    with pytest.raises(HTTPException) as exc:
        request_service.create_request(
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            reason="Needs admission",
            actor=doctor,
        )
    assert exc.value.status_code == 409


def test_list_requests_shows_closed_admission_status_and_no_active_bed(db, clinic_id, doctor):
    admin = _create_admin(db, clinic_id)
    patient = _create_patient(db, clinic_id)

    request_service = AdmissionRequestService(db)
    request = request_service.create_request(
        patient_id=patient.id,
        admission_type=AdmissionType.EMERGENCY,
        reason="Needs admission",
        actor=doctor,
    )
    approved_request, admission = request_service.approve_request(
        request_id=request.id,
        actor=admin,
        decision_reason="Approved",
    )

    AdmissionService(db).discharge_admission(
        admission_id=admission.id,
        actor=admin,
    )

    approved = request_service.list_requests(
        actor=admin,
        status=AdmissionRequestStatus.APPROVED,
    )
    target = next(item for item in approved if item.id == approved_request.id)

    assert target.admission_status == AdmissionStatus.DISCHARGED
    assert target.has_active_bed_assignment is False
    assert target.current_bed_id is None
    assert target.current_bed_label is None
