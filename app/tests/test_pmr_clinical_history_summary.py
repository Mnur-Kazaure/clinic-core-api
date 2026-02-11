import json
import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.consultation import Consultation
from app.models.event_log import EventLog
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.prescription import Prescription
from app.models.user import User
from app.models.visit import Visit
from app.services.pmr_service import PMRService
from app.shared.enums import (
    Gender,
    LabRequestStatus,
    PrescriptionStatus,
    PurposeOfUse,
    UserRole,
    VisitStatus,
)


def test_pmr_clinical_history_includes_visit_anchored_sections(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    reception = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Reception",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Doctor",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    tech = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Tech",
        role=UserRole.LAB,
        is_active=True,
    )
    db.add_all([reception, doctor, tech])
    db.commit()

    canonical_patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient Canonical",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    merged_from_patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Patient Duplicate",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add_all([canonical_patient, merged_from_patient])
    db.commit()

    mapping = PatientIdentityMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        from_patient_id=merged_from_patient.id,
        to_patient_id=canonical_patient.id,
        mapped_at=datetime.now(timezone.utc),
        mapped_by=reception.id,
    )
    db.add(mapping)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=merged_from_patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc),
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        presenting_complaints="Headache and fever",
        diagnosis="Malaria suspected",
        notes="Hydrate and monitor.",
    )
    db.add(consultation)
    db.commit()

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=consultation.id,
        visit_id=visit.id,
        clinic_id=clinic_id,
        prescribed_by=doctor.id,
        drug_name="Paracetamol",
        dosage="500mg",
        frequency="Twice daily",
        duration="3 days",
        instructions="After meals",
        status=PrescriptionStatus.ISSUED,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(prescription)
    db.commit()

    lab_request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        requested_by=doctor.id,
        test_name="Malaria Rapid Test",
        special_instructions="Urgent",
        status=LabRequestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(lab_request)
    db.commit()

    lab_result = LabResult(
        id=uuid.uuid4(),
        lab_request_id=lab_request.id,
        clinic_id=clinic_id,
        technician_id=tech.id,
        result_value="Positive",
        result_unit=None,
        reference_range=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(lab_result)
    db.commit()

    pmr = PMRService(db).get_pmr(
        patient_id=canonical_patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="PMR lookup",
        break_glass=False,
        limit=10,
    )

    assert canonical_patient.id in pmr["identity_closure_ids"]
    assert merged_from_patient.id in pmr["identity_closure_ids"]

    assert pmr["clinical_history"]
    entry = next(h for h in pmr["clinical_history"] if h["visit_id"] == visit.id)

    assert entry["sections"]["consultation"]["exists"] is True
    assert entry["sections"]["consultation"]["item"]["diagnosis_summary"] == "Malaria suspected"

    assert entry["sections"]["prescriptions"]["exists"] is True
    assert entry["sections"]["prescriptions"]["count"] == 1
    assert entry["sections"]["prescriptions"]["items"][0]["drugs"][0]["name"] == "Paracetamol"

    assert entry["sections"]["labs"]["exists"] is True
    assert entry["sections"]["labs"]["count"] == 1
    assert entry["sections"]["labs"]["requests"][0]["results_available"] is True


def test_pmr_returns_access_log_id_and_single_access_logged_event(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    reception = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Reception",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    db.add(reception)
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="PMR Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    pmr = PMRService(db).get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="Record lookup",
        break_glass=False,
        limit=5,
    )
    assert pmr["access_log_id"]

    event = (
        db.query(EventLog)
        .filter(EventLog.event_type == "ACCESS_LOGGED")
        .order_by(EventLog.created_at.desc())
        .first()
    )
    payload = json.loads(event.payload)
    assert payload["access_log_id"] == str(pmr["access_log_id"])
    assert payload["resource"] == "PMR"

