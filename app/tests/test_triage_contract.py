import uuid
from datetime import date, datetime, timedelta, timezone

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
    TriageAssessmentRecordStatus,
    Gender,
    TriageComplaintSeverity,
    TriageFallbackReasonCode,
    TriageFinalizeAction,
    UserRole,
    VisitServiceLine,
    VisitStatus,
    VisitTriageState,
)
from app.schemas.triage import (
    TriageDraftRequest,
    TriageFinalizeRequest,
    TriageSignRequest,
    TriageSupersedeRequest,
)
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


def test_triage_finalize_creates_assessment_and_keeps_visit_registered(db, clinic_id):
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

    assert updated_visit.status == VisitStatus.REGISTERED
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
    assert exc.value.detail["code"] == "TRIAGE_STATUS_RETIRED"


def test_start_consultation_allowed_from_triaged_without_assessment(db, clinic_id):
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

    transitioned = VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.IN_CONSULTATION,
        user=doctor,
        expected_version=visit.version,
    )

    assert transitioned.status == VisitStatus.IN_CONSULTATION


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
    assert updated_visit.status == VisitStatus.REGISTERED
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


def test_triage_draft_then_sign_updates_visit_mirror_fields(db, clinic_id):
    _seed_clinic(db, clinic_id)
    chew = _seed_user(db, clinic_id, UserRole.CHEW, "chew-draft@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=chew.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    draft, draft_visit = TriageService(db).upsert_draft_assessment(
        visit_id=visit.id,
        payload=TriageDraftRequest(**_payload(expected_version=visit.version).model_dump()),
        current_user=chew,
        idempotency_key="triage-draft-1",
    )

    assert draft.record_status == TriageAssessmentRecordStatus.DRAFT
    assert draft_visit.status == VisitStatus.REGISTERED
    assert draft_visit.triage_state == VisitTriageState.PENDING

    signed, signed_visit = TriageService(db).sign_assessment(
        visit_id=visit.id,
        payload=TriageSignRequest(expected_version=draft_visit.version),
        current_user=chew,
        idempotency_key="triage-sign-1",
    )

    assert signed.record_status == TriageAssessmentRecordStatus.SIGNED
    assert signed_visit.status == VisitStatus.REGISTERED
    assert signed_visit.triage_state == VisitTriageState.TRIAGED
    assert signed_visit.triage_acuity == ClinicalPriorityLevel.URGENT
    assert signed_visit.triaged_at is not None
    assert signed_visit.triaged_by == chew.id


def test_start_consultation_allowed_without_signed_triage_record(db, clinic_id):
    _seed_clinic(db, clinic_id)
    chew = _seed_user(db, clinic_id, UserRole.CHEW, "chew-triage@triage.test")
    visit_owner = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor-start@triage.test")
    patient = _seed_patient(db, clinic_id)
    visit = _seed_visit(
        db,
        clinic_id,
        patient.id,
        owner_id=visit_owner.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )

    _, draft_visit = TriageService(db).upsert_draft_assessment(
        visit_id=visit.id,
        payload=TriageDraftRequest(**_payload(expected_version=visit.version).model_dump()),
        current_user=chew,
    )

    transitioned = VisitService(db).transition_visit(
        visit_id=visit.id,
        to_status=VisitStatus.IN_CONSULTATION,
        user=visit_owner,
        expected_version=draft_visit.version,
    )

    assert transitioned.status == VisitStatus.IN_CONSULTATION


def test_triage_queue_orders_pending_then_signed_acuity(db, clinic_id):
    _seed_clinic(db, clinic_id)
    chew = _seed_user(db, clinic_id, UserRole.CHEW, "chew-queue@triage.test")
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor-queue@triage.test")
    now = datetime.now(timezone.utc)

    pending_patient = _seed_patient(db, clinic_id)
    pending_visit = _seed_visit(
        db,
        clinic_id,
        pending_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )
    pending_visit.started_at = now - timedelta(minutes=20)
    pending_visit.triage_state = VisitTriageState.PENDING
    db.add(pending_visit)

    anc_pending_patient = _seed_patient(db, clinic_id)
    anc_pending_visit = _seed_visit(
        db,
        clinic_id,
        anc_pending_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.ANC,
        status=VisitStatus.REGISTERED,
    )
    anc_pending_visit.started_at = now - timedelta(minutes=10)
    anc_pending_visit.triage_state = VisitTriageState.PENDING
    db.add(anc_pending_visit)

    urgent_patient = _seed_patient(db, clinic_id)
    urgent_visit = _seed_visit(
        db,
        clinic_id,
        urgent_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )
    urgent_visit.triage_state = VisitTriageState.TRIAGED
    urgent_visit.triage_acuity = ClinicalPriorityLevel.URGENT
    urgent_visit.triaged_at = now
    db.add(urgent_visit)

    critical_patient = _seed_patient(db, clinic_id)
    critical_visit = _seed_visit(
        db,
        clinic_id,
        critical_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.ANC,
        status=VisitStatus.REGISTERED,
    )
    critical_visit.triage_state = VisitTriageState.TRIAGED
    critical_visit.triage_acuity = ClinicalPriorityLevel.CRITICAL
    critical_visit.triaged_at = now
    db.add(critical_visit)

    maternity_patient = _seed_patient(db, clinic_id)
    maternity_visit = _seed_visit(
        db,
        clinic_id,
        maternity_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.MATERNITY,
        status=VisitStatus.REGISTERED,
    )
    maternity_visit.triage_state = VisitTriageState.PENDING
    db.add(maternity_visit)
    db.commit()

    queue = TriageService(db).list_triage_queue(
        current_user=chew,
        triage_state=None,
    )

    queue_ids = [visit.id for visit in queue]
    assert maternity_visit.id not in queue_ids
    assert queue_ids[:4] == [
        pending_visit.id,
        anc_pending_visit.id,
        critical_visit.id,
        urgent_visit.id,
    ]


def test_triage_queue_scope_for_midwife_excludes_opd(db, clinic_id):
    _seed_clinic(db, clinic_id)
    midwife = _seed_user(db, clinic_id, UserRole.MIDWIFE, "midwife-queue@triage.test")
    doctor = _seed_user(db, clinic_id, UserRole.DOCTOR, "doctor-midwife-queue@triage.test")

    anc_patient = _seed_patient(db, clinic_id)
    anc_visit = _seed_visit(
        db,
        clinic_id,
        anc_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.ANC,
        status=VisitStatus.REGISTERED,
    )
    anc_visit.triage_state = VisitTriageState.PENDING
    db.add(anc_visit)

    maternity_patient = _seed_patient(db, clinic_id)
    maternity_visit = _seed_visit(
        db,
        clinic_id,
        maternity_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.MATERNITY,
        status=VisitStatus.REGISTERED,
    )
    maternity_visit.triage_state = VisitTriageState.PENDING
    db.add(maternity_visit)

    opd_patient = _seed_patient(db, clinic_id)
    opd_visit = _seed_visit(
        db,
        clinic_id,
        opd_patient.id,
        owner_id=doctor.id,
        service_line=VisitServiceLine.OPD,
        status=VisitStatus.REGISTERED,
    )
    opd_visit.triage_state = VisitTriageState.PENDING
    db.add(opd_visit)
    db.commit()

    queue = TriageService(db).list_triage_queue(current_user=midwife)
    queue_ids = {visit.id for visit in queue}

    assert anc_visit.id in queue_ids
    assert maternity_visit.id in queue_ids
    assert opd_visit.id not in queue_ids
