import uuid
from datetime import datetime, date, timezone

from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.consultation import Consultation
from app.models.lab_request import LabRequest
from app.models.lab_specimen import LabSpecimen
from app.models.service_line import ServiceLine
from app.models.user import User
from app.services.visit.service import VisitService
from app.services.consultation_service import ConsultationService
from app.services.lab_service import LabService
from app.services.prescription_service import PrescriptionService
from app.shared.enums import (
    VisitStatus,
    LabRequestStatus,
    RecordStatus,
    Gender,
    LabSpecimenStatus,
    UserRole,
)
from app.schemas.lab import LabResultCreate
from app.schemas.prescription import PrescriptionCreateRequest


def _seed_clinic_user(db, clinic_id, role, email):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=email,
        password_hash="test",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _seed_patient_visit(db, clinic_id, doctor_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Event Patient",
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
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor_id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()
    return patient, visit


def test_visit_transition_emits_event(db, clinic_id):
    doctor = _seed_clinic_user(db, clinic_id, UserRole.DOCTOR, "doc@event.test")
    patient, visit = _seed_patient_visit(db, clinic_id, doctor.id)

    lab_request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        requested_by=doctor.id,
        test_name="CBC",
        status=LabRequestStatus.PENDING,
    )
    db.add(lab_request)
    db.commit()

    VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.LAB_REQUESTED,
        user=doctor,
        expected_version=visit.version,
    )

    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "ENTRY_AMENDED")
        .count()
        == 1
    )


def test_consultation_sign_emits_event(db, clinic_id):
    doctor = _seed_clinic_user(db, clinic_id, UserRole.DOCTOR, "doc2@event.test")
    _, visit = _seed_patient_visit(db, clinic_id, doctor.id)

    service = ConsultationService(db)
    consultation = service.start_consultation(visit, doctor)
    service.complete_consultation(consultation, doctor)

    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "ENTRY_SIGNED")
        .count()
        >= 1
    )


def test_lab_post_emits_event(db, clinic_id):
    lab_user = _seed_clinic_user(db, clinic_id, UserRole.LAB, "lab@event.test")
    doctor = _seed_clinic_user(db, clinic_id, UserRole.DOCTOR, "doc3@event.test")
    _, visit = _seed_patient_visit(db, clinic_id, doctor.id)
    unit = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Event Lab Unit",
        parent_id=None,
        department_id=None,
        default_child_id=None,
        requires_doctor=False,
        is_active=True,
    )
    db.add(unit)
    db.commit()

    lab_request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        requested_by=doctor.id,
        test_name="CBC",
        target_unit_id=unit.id,
        status=LabRequestStatus.PENDING,
    )
    db.add(lab_request)
    db.commit()

    specimen = LabSpecimen(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        accession_number=f"LAB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{clinic_id.hex[:5].upper()}",
        request_item_id=lab_request.id,
        target_unit_id=unit.id,
        specimen_type="Blood",
        specimen_source="blood",
        status=LabSpecimenStatus.RECEIVED,
        collected_by=lab_user.id,
        collected_at=datetime.now(timezone.utc),
        received_by=lab_user.id,
        received_at=datetime.now(timezone.utc),
    )
    db.add(specimen)
    db.commit()

    payload = LabResultCreate(
        result_value="Normal",
        result_unit="mg",
        reference_range="10-20",
    )
    LabService(db).record_result(
        lab_request.id,
        payload,
        technician_id=lab_user.id,
    )

    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "LAB_RESULT_POSTED")
        .count()
        == 1
    )


def test_prescription_void_emits_event(db, clinic_id):
    doctor = _seed_clinic_user(db, clinic_id, UserRole.DOCTOR, "doc4@event.test")
    patient, visit = _seed_patient_visit(db, clinic_id, doctor.id)

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        record_status=RecordStatus.SIGNED,
        signed_at=datetime.now(timezone.utc),
    )
    db.add(consultation)
    db.commit()

    payload = PrescriptionCreateRequest(
        consultation_id=consultation.id,
        drug_name="Drug",
        dosage="10mg",
        frequency="1x",
        duration="5d",
        instructions=None,
    )
    service = PrescriptionService(db)
    prescription = service.issue_prescription(
        consultation=consultation,
        visit_id=visit.id,
        doctor_id=doctor.id,
        payload=payload,
    )

    service.cancel_prescription(
        prescription=prescription,
        reason="duplicate order",
    )

    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "ENTRY_VOIDED")
        .count()
        >= 1
    )
