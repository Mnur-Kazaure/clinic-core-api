import json
import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.clinic import Clinic
from app.models.user import User
from app.models.patient import Patient
from app.models.event_log import EventLog
from app.models.patient_identity_map import PatientIdentityMap
from app.services.identity_service import IdentityService
from app.schemas.identity import (
    ProvisionalPatientRequest,
    IdentityCaseCreateRequest,
    IdentityEvidenceCreateRequest,
    IdentityApprovalRequest,
    IdentityRollbackRequest,
)
from app.shared.enums import (
    Gender,
    IdentityCaseType,
    IdentityApprovalDecision,
    IdentityEvidenceType,
    UserRole,
    IdentityState,
)


def _seed_clinic_and_admins(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"admin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    clinic_admin = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cadmin.{uuid.uuid4()}@example.com",
        password_hash="test",
        full_name="Clinic Admin",
        role=UserRole.CLINIC_ADMIN,
        is_active=True,
    )
    db.add_all([admin, clinic_admin])
    db.commit()
    return admin, clinic_admin


def _create_patient(db, clinic_id, name):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name=name,
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()
    return patient


def _add_two_evidence(service, case_id, current_user):
    service.add_evidence(
        case_id=case_id,
        payload=IdentityEvidenceCreateRequest(
            evidence_type=IdentityEvidenceType.DOCUMENT_REF,
            ref="doc-1",
            notes=None,
        ),
        current_user=current_user,
    )
    service.add_evidence(
        case_id=case_id,
        payload=IdentityEvidenceCreateRequest(
            evidence_type=IdentityEvidenceType.STAFF_WITNESS,
            ref="witness-1",
            notes=None,
        ),
        current_user=current_user,
    )


def _approve_dual(service, case_id, admin, clinic_admin):
    service.approve_case(
        case_id=case_id,
        payload=IdentityApprovalRequest(
            decision=IdentityApprovalDecision.APPROVE,
            decision_reason="approved",
        ),
        current_user=admin,
    )
    service.approve_case(
        case_id=case_id,
        payload=IdentityApprovalRequest(
            decision=IdentityApprovalDecision.APPROVE,
            decision_reason="approved",
        ),
        current_user=clinic_admin,
    )


def test_provisional_allows_unknown_fields(db, clinic_id):
    clinic = Clinic(id=clinic_id, name="Clinic A")
    db.add(clinic)
    db.commit()

    receptionist = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"reception.{uuid.uuid4()}@example.com",
        password_hash="test",
        role=UserRole.RECEPTION,
        is_active=True,
    )
    db.add(receptionist)
    db.commit()

    service = IdentityService(db)
    payload = ProvisionalPatientRequest(created_reason="unconscious arrival")
    patient = service.create_provisional_patient(
        payload=payload,
        current_user=receptionist,
    )

    assert patient.full_name == "Unknown Patient"
    assert patient.gender == Gender.UNKNOWN
    assert patient.phone_number == "UNKNOWN"
    assert patient.identity_state == IdentityState.PROVISIONAL


def test_case_requires_approved_status_before_apply(db, clinic_id):
    admin, _ = _seed_clinic_and_admins(db, clinic_id)
    patient_a = _create_patient(db, clinic_id, "Patient A")
    patient_b = _create_patient(db, clinic_id, "Patient B")

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.MERGE,
            primary_patient_id=patient_a.id,
            target_patient_id=patient_b.id,
            reason="duplicate",
        ),
        current_user=admin,
    )

    with pytest.raises(HTTPException):
        service.apply_case(case_id=case.id, current_user=admin)


def test_evidence_minimum_enforced_before_approval(db, clinic_id):
    admin, _ = _seed_clinic_and_admins(db, clinic_id)
    patient_a = _create_patient(db, clinic_id, "Patient A")
    patient_b = _create_patient(db, clinic_id, "Patient B")

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.MERGE,
            primary_patient_id=patient_a.id,
            target_patient_id=patient_b.id,
            reason="duplicate",
        ),
        current_user=admin,
    )

    service.add_evidence(
        case_id=case.id,
        payload=IdentityEvidenceCreateRequest(
            evidence_type=IdentityEvidenceType.DOCUMENT_REF,
            ref="doc-1",
            notes=None,
        ),
        current_user=admin,
    )

    with pytest.raises(HTTPException):
        service.approve_case(
            case_id=case.id,
            payload=IdentityApprovalRequest(
                decision=IdentityApprovalDecision.APPROVE,
                decision_reason="approved",
            ),
            current_user=admin,
        )


def test_split_emits_event_and_updates_states(db, clinic_id):
    admin, clinic_admin = _seed_clinic_and_admins(db, clinic_id)
    primary = _create_patient(db, clinic_id, "Patient A")
    target = _create_patient(db, clinic_id, "Patient B")

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.SPLIT,
            primary_patient_id=primary.id,
            target_patient_id=target.id,
            reason="split record",
        ),
        current_user=admin,
    )

    _add_two_evidence(service, case.id, admin)
    _approve_dual(service, case.id, admin, clinic_admin)

    applied = service.apply_case(case_id=case.id, current_user=admin)
    assert applied.status.name == "APPLIED"

    db.refresh(primary)
    assert primary.identity_state == IdentityState.SPLIT

    event = (
        db.query(EventLog)
        .filter(EventLog.event_type == "IDENTITY_SPLIT")
        .first()
    )
    assert event is not None
    payload = json.loads(event.payload)
    assert payload["primary_patient_id"] == str(primary.id)
    assert payload["target_patient_id"] == str(target.id)
    assert len(payload["evidence_ids"]) >= 2
    assert len(payload["approval_ids"]) >= 2


def test_rollback_updates_identity_state(db, clinic_id):
    admin, clinic_admin = _seed_clinic_and_admins(db, clinic_id)
    patient_a = _create_patient(db, clinic_id, "Patient A")
    patient_a.identity_state = IdentityState.PROVISIONAL
    patient_a.created_reason = "unconscious"
    patient_b = _create_patient(db, clinic_id, "Patient B")
    db.commit()

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.MERGE,
            primary_patient_id=patient_a.id,
            target_patient_id=patient_b.id,
            reason="duplicate",
        ),
        current_user=admin,
    )

    _add_two_evidence(service, case.id, admin)
    _approve_dual(service, case.id, admin, clinic_admin)
    service.apply_case(case_id=case.id, current_user=admin)

    service.rollback_case(
        case_id=case.id,
        payload=IdentityRollbackRequest(reason="wrong merge"),
        current_user=admin,
    )

    db.refresh(patient_a)
    assert patient_a.identity_state == IdentityState.PROVISIONAL


def test_mapping_cycle_prevented_on_merge(db, clinic_id):
    admin, clinic_admin = _seed_clinic_and_admins(db, clinic_id)
    patient_a = _create_patient(db, clinic_id, "Patient A")
    patient_b = _create_patient(db, clinic_id, "Patient B")

    existing_map = PatientIdentityMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        from_patient_id=patient_b.id,
        to_patient_id=patient_a.id,
        mapped_at=datetime.now(timezone.utc),
        mapped_by=admin.id,
    )
    db.add(existing_map)
    db.commit()

    service = IdentityService(db)
    case = service.create_case(
        payload=IdentityCaseCreateRequest(
            case_type=IdentityCaseType.MERGE,
            primary_patient_id=patient_a.id,
            target_patient_id=patient_b.id,
            reason="cycle check",
        ),
        current_user=admin,
    )

    _add_two_evidence(service, case.id, admin)
    _approve_dual(service, case.id, admin, clinic_admin)

    with pytest.raises(HTTPException):
        service.apply_case(case_id=case.id, current_user=admin)
