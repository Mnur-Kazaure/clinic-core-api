import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.clinical_priority_event import ClinicalPriorityEvent
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.triage_assessment import TriageAssessment
from app.models.user import User
from app.models.visit import Visit
from app.shared.enums import (
    ClinicalPriorityLevel,
    ClinicalPrioritySource,
    Gender,
    TriageComplaintSeverity,
    TriageFallbackReasonCode,
    TriageFinalizeAction,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)
from app.schemas.triage import TriageFinalizeRequest, TriageSupersedeRequest
from app.services.triage_service import TriageService
from app.services.visit.service import VisitService


def _seed_clinic(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()
    return clinic


def _seed_user(db, clinic_id, role, email):
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


def _seed_patient(db, clinic_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Triage Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()
    return patient


def _seed_visit(db, clinic_id, patient_id, owner_id, service_line, status):
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        assigned_doctor_id=owner_id,
        service_line=service_line,
        status=status,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()
    return visit


def _payload(**overrides):
    payload = {
        "expected_version": 1,
        "action": TriageFinalizeAction.QUEUE_FOR_CONSULTATION,
        "acuity_level": ClinicalPriorityLevel.URGENT,
        "chief_complaint": "Severe headache",
        "complaint_severity": TriageComplaintSeverity.SEVERE,
        "triage_note": "Patient in visible distress",
        "danger_sign_codes": [],
        "temp_c": 37.3,
        "pulse_bpm": 96,
        "rr_bpm": 20,
        "sbp_mmhg": 130,
        "dbp_mmhg": 80,
        "spo2_pct": 98,
        "missing_vitals_reason_code": None,
        "is_doctor_fallback": False,
        "fallback_reason_code": None,
        "fallback_reason_text": None,
        "referred_facility": None,
        "referral_reason": None,
    }
    payload.update(overrides)
    return TriageFinalizeRequest(**payload)


def test_triage_finalize_creates_assessment_and_transitions_to_triaged(db, clinic_id):
    _seed_clinic(db, clinic_id)
    chew = _seed_user(db, clinic_id, UserRole.CHEW, "chew@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=chew.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    triage, updated_visit = TriageService(db).finalize_assessment(
        visit_id=visit.id,
        payload=_payload(expected_version=visit.version),
        current_user=chew,
        idempotency_key="triage-finalize-1",
    )

    assert updated_visit.status == VisitStatus.TRIAGED
    assert updated_visit.version == 2
    assert triage.visit_id == visit.id

    priority_event = (
        db.query(ClinicalPriorityEvent)
        .filter(ClinicalPriorityEvent.visit_id == visit.id)
        .order_by(ClinicalPriorityEvent.set_at.desc())
        .first()
    )
    assert priority_event is not None
    assert priority_event.level == ClinicalPriorityLevel.URGENT
    assert priority_event.source == ClinicalPrioritySource.TRIAGE


def test_transition_to_triaged_directly_is_blocked(db, clinic_id):
    _seed_clinic(db, clinic_id)
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.TRIAGED,
            user=doctor,
            expected_version=visit.version,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "TRIAGE_USE_FINALIZE_ENDPOINT"


def test_start_consultation_requires_active_triage_assessment(db, clinic_id):
    _seed_clinic(db, clinic_id)
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor2@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.TRIAGED,
    )

    with pytest.raises(HTTPException) as exc:
        VisitService(db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.IN_CONSULTATION,
            user=doctor,
            expected_version=visit.version,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "RETRIAGE_REQUIRED"


def test_start_consultation_from_registered_is_allowed_for_assigned_doctor(
    db,
    clinic_id,
):
    _seed_clinic(db, clinic_id)
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor-registered@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    updated_visit = VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.IN_CONSULTATION,
        user=doctor,
        expected_version=visit.version,
    )

    assert updated_visit.status == VisitStatus.IN_CONSULTATION
    assert updated_visit.version == 2


def test_doctor_fallback_requires_reason_code(db, clinic_id):
    _seed_clinic(db, clinic_id)
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor3@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    with pytest.raises(HTTPException) as exc:
        TriageService(db).finalize_assessment(
            visit_id=visit.id,
            payload=_payload(
                expected_version=visit.version,
                is_doctor_fallback=True,
            ),
            current_user=doctor,
        )

    assert exc.value.status_code == 422
    assert "fallback_reason_code" in str(exc.value.detail)


def test_reception_cannot_finalize_triage(db, clinic_id):
    _seed_clinic(db, clinic_id)
    receptionist = _seed_user(db, clinic_id, UserRole.RECEPTION, "reception@triage.test")
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor4@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    with pytest.raises(HTTPException) as exc:
        TriageService(db).finalize_assessment(
            visit_id=visit.id,
            payload=_payload(expected_version=visit.version),
            current_user=receptionist,
        )

    assert exc.value.status_code == 403


def test_triage_supersede_creates_new_active_assessment(db, clinic_id):
    _seed_clinic(db, clinic_id)
    chew = _seed_user(db, clinic_id, UserRole.CHEW, "chew2@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=chew.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    first, visit = TriageService(db).finalize_assessment(
        visit_id=visit.id,
        payload=_payload(expected_version=visit.version),
        current_user=chew,
        idempotency_key="triage-supersede-1",
    )

    replacement_payload = TriageSupersedeRequest(
        **_payload(
            expected_version=visit.version,
            acuity_level=ClinicalPriorityLevel.CRITICAL,
            triage_note="Patient deteriorated quickly",
        ).model_dump(),
        correction_reason_code="REASSESSMENT",
        correction_reason_text="Patient condition changed after first assessment",
    )

    replacement, updated_visit = TriageService(db).supersede_assessment(
        visit_id=visit.id,
        payload=replacement_payload,
        current_user=chew,
        idempotency_key="triage-supersede-2",
    )

    db.refresh(first)
    assert first.superseded_at is not None
    assert replacement.supersedes_assessment_id == first.id
    assert updated_visit.status == VisitStatus.TRIAGED
    assert updated_visit.version == 3

    active_rows = (
        db.query(TriageAssessment)
        .filter(
            TriageAssessment.visit_id == visit.id,
            TriageAssessment.superseded_at.is_(None),
        )
        .all()
    )
    assert len(active_rows) == 1
    assert active_rows[0].id == replacement.id

    assert (
        db.query(EventLog)
        .filter(EventLog.event_type == "TRIAGE_ASSESSMENT_SUPERSEDED")
        .count()
        == 1
    )


def test_doctor_fallback_with_other_requires_reason_text(db, clinic_id):
    _seed_clinic(db, clinic_id)
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor5@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    with pytest.raises(HTTPException) as exc:
        TriageService(db).finalize_assessment(
            visit_id=visit.id,
            payload=_payload(
                expected_version=visit.version,
                is_doctor_fallback=True,
                fallback_reason_code=TriageFallbackReasonCode.OTHER,
                fallback_reason_text="short",
            ),
            current_user=doctor,
        )

    assert exc.value.status_code == 422
    assert "fallback_reason_text" in str(exc.value.detail)
