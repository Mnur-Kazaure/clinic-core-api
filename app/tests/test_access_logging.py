import uuid
from datetime import date
import pytest
from fastapi import HTTPException

from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.visit import Visit
from app.services.access_log_service import AccessLogService
from app.models.event_log import EventLog
from app.shared.enums import VisitStatus, Gender, PurposeOfUse


def _seed_patient_visit(db, clinic_id, doctor_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Audit Patient",
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
    )
    db.add(visit)
    db.commit()
    return patient, visit


def test_access_logged_search_and_chart_read(db, doctor, clinic_id):
    service = AccessLogService(db)

    patient, visit = _seed_patient_visit(db, clinic_id, doctor.id)

    service.log_search(
        actor=doctor,
        clinic_id=clinic_id,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="patient lookup",
        resource="PATIENT_SEARCH",
    )

    service.log_chart_read(
        actor=doctor,
        clinic_id=clinic_id,
        patient_id=patient.id,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="chart review",
        resource="VISIT_DETAIL",
    )

    access_logs = db.query(AccessLog).all()
    event_logs = db.query(EventLog).filter(EventLog.event_type == "ACCESS_LOGGED").all()

    assert len(access_logs) == 2
    assert len(event_logs) == 2

    chart_log = next(log for log in access_logs if log.action == "CHART_READ")
    assert chart_log.patient_id == patient.id


def test_break_glass_requires_reason(db, doctor, clinic_id):
    service = AccessLogService(db)

    with pytest.raises(HTTPException):
        service.log_break_glass(
            actor=doctor,
            clinic_id=clinic_id,
            patient_id=uuid.uuid4(),
            purpose_of_use=PurposeOfUse.EMERGENCY,
            justification="",
            resource="VISIT_DETAIL",
        )


def test_break_glass_emits_event(db, doctor, clinic_id):
    service = AccessLogService(db)
    patient, _ = _seed_patient_visit(db, clinic_id, doctor.id)

    service.log_break_glass(
        actor=doctor,
        clinic_id=clinic_id,
        patient_id=patient.id,
        purpose_of_use=PurposeOfUse.EMERGENCY,
        justification="emergency override",
        resource="VISIT_DETAIL",
    )

    event_logs = db.query(EventLog).filter(EventLog.event_type == "BREAK_GLASS_USED").all()
    assert len(event_logs) == 1
