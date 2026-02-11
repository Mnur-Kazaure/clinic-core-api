import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.event_log import EventLog  # noqa: F401 (sqlite create_all registration)
from app.models.lab_request import LabRequest
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_status_history import VisitStatusHistory
from app.services.visit.service import VisitService
from app.core.guards.pharmacy_prescription_guards import require_pharmacy_for_dispense
from app.shared.enums import (
    Gender,
    LabRequestStatus,
    PrescriptionStatus,
    RecordStatus,
    UserRole,
    VisitOverrideReasonCode,
    VisitStatus,
)


def _seed_core(db):
    clinic = Clinic(id=uuid.uuid4(), name="Clinic A")
    db.add(clinic)
    db.commit()

    receptionist = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    pharmacist = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"pharmacy.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.PHARMACY,
        is_active=True,
    )
    db.add_all([receptionist, doctor, pharmacist])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Patient A",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    return clinic, receptionist, doctor, pharmacist, patient


def test_completion_normal_succeeds_when_no_outstanding(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    updated = VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.COMPLETED,
        user=receptionist,
        expected_version=1,
        mode="normal",
        idempotency_key="test-key-1",
    )

    assert updated.status == VisitStatus.COMPLETED
    assert updated.version == 2


def test_completion_normal_returns_409_when_outstanding(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    pending_lab = LabRequest(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        visit_id=visit.id,
        requested_by=doctor.id,
        test_name="Malaria parasite microscopy",
        special_instructions="Urgent",
        status=LabRequestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(pending_lab)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=receptionist,
            expected_version=1,
            mode="normal",
            idempotency_key="test-key-2",
        )

    assert exc.value.status_code == 409
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail.get("code") == "VISIT_HAS_OUTSTANDING_WORK"
    assert exc.value.detail.get("allowed_override") is True
    assert exc.value.detail.get("outstanding", {}).get("pending_labs_count") == 1


def test_completion_override_requires_reason_code(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    db.add(
        LabRequest(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            visit_id=visit.id,
            requested_by=doctor.id,
            test_name="PCV",
            status=LabRequestStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=receptionist,
            expected_version=1,
            mode="override",
            override_reason_code=None,
            idempotency_key="test-key-3",
        )

    assert exc.value.status_code == 422


def test_completion_override_other_requires_reason_text_min_len(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    db.add(
        LabRequest(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            visit_id=visit.id,
            requested_by=doctor.id,
            test_name="HB",
            status=LabRequestStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=receptionist,
            expected_version=1,
            mode="override",
            override_reason_code=VisitOverrideReasonCode.OTHER,
            override_reason_text="too short",
            idempotency_key="test-key-4",
        )

    assert exc.value.status_code == 422


def test_completion_override_records_snapshot_and_source(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    # pending lab -> outstanding snapshot should show pending_labs_count=1
    db.add(
        LabRequest(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            visit_id=visit.id,
            requested_by=doctor.id,
            test_name="Urinalysis",
            status=LabRequestStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    updated = VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.COMPLETED,
        user=receptionist,
        expected_version=1,
        mode="override",
        override_reason_code=VisitOverrideReasonCode.PATIENT_LEFT,
        idempotency_key="test-key-5",
    )

    assert updated.status == VisitStatus.COMPLETED
    assert updated.version == 2

    history = (
        db.query(VisitStatusHistory)
        .filter(VisitStatusHistory.visit_id == visit.id)
        .order_by(VisitStatusHistory.created_at.desc())
        .first()
    )
    assert history is not None
    assert history.source == "override"
    assert history.reason_code == VisitOverrideReasonCode.PATIENT_LEFT.value
    assert history.pending_labs_count_snapshot == 1
    assert history.unfulfilled_prescriptions_count_snapshot == 0
    assert history.idempotency_key == "test-key-5"


def test_version_conflict_returns_current_version(db):
    clinic, receptionist, doctor, _pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.PHARMACY_PENDING,
        started_at=datetime.now(timezone.utc),
        version=3,
    )
    db.add(visit)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=receptionist,
            expected_version=2,
            mode="normal",
            idempotency_key="test-key-6",
        )

    assert exc.value.status_code == 409
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail.get("code") == "VERSION_CONFLICT"
    assert exc.value.detail.get("current_version") == 3


def test_pharmacy_dispense_guard_allows_completed_visit(db):
    clinic, _receptionist, doctor, pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        version=2,
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=consultation.id,
        visit_id=visit.id,
        clinic_id=clinic.id,
        prescribed_by=doctor.id,
        drug_name="Ibuprofen",
        dosage="500mg",
        frequency="Before meals",
        duration="10 days",
        instructions="With food",
        status=PrescriptionStatus.ISSUED,
        record_status=RecordStatus.SIGNED,
        signed_at=datetime.now(timezone.utc),
        issued_at=datetime.now(timezone.utc),
    )
    db.add(prescription)
    db.commit()

    allowed = require_pharmacy_for_dispense(
        prescription_id=prescription.id,
        db=db,
        current_user=pharmacist,
    )
    assert allowed.id == prescription.id


def test_pharmacy_dispense_guard_blocks_cancelled_visit(db):
    clinic, _receptionist, doctor, pharmacist, patient = _seed_core(db)

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.CANCELLED,
        started_at=datetime.now(timezone.utc),
        version=2,
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=consultation.id,
        visit_id=visit.id,
        clinic_id=clinic.id,
        prescribed_by=doctor.id,
        drug_name="Ibuprofen",
        dosage="500mg",
        frequency="Before meals",
        duration="10 days",
        instructions="With food",
        status=PrescriptionStatus.ISSUED,
        record_status=RecordStatus.SIGNED,
        signed_at=datetime.now(timezone.utc),
        issued_at=datetime.now(timezone.utc),
    )
    db.add(prescription)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        require_pharmacy_for_dispense(
            prescription_id=prescription.id,
            db=db,
            current_user=pharmacist,
        )
    assert exc.value.status_code == 409
