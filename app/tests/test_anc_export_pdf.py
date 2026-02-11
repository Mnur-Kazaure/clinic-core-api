import json
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.access_log import AccessLog
from app.models.clinic import Clinic
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.pregnancy_episode import PregnancyEpisode
from app.models.user import User
from app.models.visit import Visit
from app.services.anc_service import ANCService
from app.shared.enums import (
    Gender,
    PregnancyEpisodeStatus,
    PurposeOfUse,
    UserRole,
    VisitServiceLine,
    VisitStatus,
)


def _seed_export_context(db, clinic_id):
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
    chew = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"chew.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="CHEW",
        role=UserRole.CHEW,
        is_active=True,
    )
    midwife = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"midwife.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Midwife",
        role=UserRole.MIDWIFE,
        is_active=True,
    )
    db.add_all([reception, chew, midwife])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="ANC Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.FEMALE,
        phone_number="000",
        address="Test",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    episode = PregnancyEpisode(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        status=PregnancyEpisodeStatus.ACTIVE,
        created_by=reception.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(episode)
    db.commit()

    return {
        "clinic_id": clinic_id,
        "reception": reception,
        "chew": chew,
        "midwife": midwife,
        "patient": patient,
        "episode": episode,
    }


def test_anc_export_reception_succeeds_and_writes_single_audit(db, clinic_id):
    ctx = _seed_export_context(db, clinic_id)
    service = ANCService(db)

    pdf_bytes, filename = service.export_episode_pdf(
        clinic_id=ctx["clinic_id"],
        episode_id=ctx["episode"].id,
        actor=ctx["reception"],
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="ANC export for continuity",
    )

    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert filename.endswith(".pdf")

    logs = db.query(AccessLog).all()
    events = db.query(EventLog).filter(EventLog.event_type == "ACCESS_LOGGED").all()
    assert len(logs) == 1
    assert len(events) == 1

    payload = json.loads(events[0].payload)
    assert payload["resource"] == "ANC"
    assert payload["episode_id"] == str(ctx["episode"].id)
    assert payload["patient_id_requested"] == str(ctx["patient"].id)
    assert payload["patient_id_canonical"] == str(ctx["patient"].id)


def test_anc_export_chew_requires_assigned_active_anc_visit(db, clinic_id):
    ctx = _seed_export_context(db, clinic_id)
    service = ANCService(db)

    with pytest.raises(HTTPException) as excinfo:
        service.export_episode_pdf(
            clinic_id=ctx["clinic_id"],
            episode_id=ctx["episode"].id,
            actor=ctx["chew"],
            purpose_of_use=PurposeOfUse.TREATMENT,
            justification="Need print",
        )
    assert excinfo.value.status_code == 403
    assert "active ANC visit assigned" in str(excinfo.value.detail)


def test_anc_export_chew_succeeds_with_assigned_active_anc_visit(db, clinic_id):
    ctx = _seed_export_context(db, clinic_id)
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic_id"],
        patient_id=ctx["patient"].id,
        assigned_doctor_id=ctx["chew"].id,
        status=VisitStatus.TRIAGED,
        service_line=VisitServiceLine.ANC,
        started_at=datetime.now(timezone.utc),
    )
    db.add(visit)
    db.commit()

    service = ANCService(db)
    pdf_bytes, _ = service.export_episode_pdf(
        clinic_id=ctx["clinic_id"],
        episode_id=ctx["episode"].id,
        actor=ctx["chew"],
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="Clinical review",
    )
    assert pdf_bytes.startswith(b"%PDF-1.4")


def test_anc_export_denies_midwife_by_default(db, clinic_id):
    ctx = _seed_export_context(db, clinic_id)
    service = ANCService(db)

    with pytest.raises(HTTPException) as excinfo:
        service.export_episode_pdf(
            clinic_id=ctx["clinic_id"],
            episode_id=ctx["episode"].id,
            actor=ctx["midwife"],
            purpose_of_use=PurposeOfUse.TREATMENT,
            justification="Try ANC export",
        )
    assert excinfo.value.status_code == 403
