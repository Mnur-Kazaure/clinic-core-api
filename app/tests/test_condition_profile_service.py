import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.user import User
from app.models.visit import Visit
from app.schemas.follow_up import (
    ChronicRecallCreateRequest,
    ConditionProfileCreateRequest,
    DiagnosisConditionMapCreateRequest,
)
from app.services.follow_up_service import ChronicRecallService, FollowUpConfigurationService
from app.shared.enums import (
    DiagnosisMappingConfidence,
    DiagnosisSystem,
    Gender,
    RecallIntervalUnit,
    UserRole,
    VisitStatus,
)


def _create_user(db, clinic_id, role: UserRole):
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"{role.value.lower()}_{uuid.uuid4()}@example.test",
        password_hash="test",
        full_name=role.value.title(),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _create_patient(db, clinic_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Follow Up Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Clinic street",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_active_visit(db, clinic_id, patient_id, owner_id):
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient_id,
        assigned_doctor_id=owner_id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()
    return visit


def test_condition_profile_mutations_require_clinic_admin(db, clinic_id):
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    service = FollowUpConfigurationService(db)

    payload = ConditionProfileCreateRequest(
        code="HTN",
        display_name="Hypertension",
        default_interval_value=3,
        default_interval_unit=RecallIntervalUnit.MONTHS,
        keyword_synonyms=["hypertension"],
        justification="setup",
    )

    with pytest.raises(HTTPException) as exc:
        service.create_condition_profile(clinic_id=clinic_id, actor=doctor, payload=payload)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Clinic Admin access required"


def test_clinic_admin_can_create_profile_and_mapping(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    service = FollowUpConfigurationService(db)

    profile = service.create_condition_profile(
        clinic_id=clinic_id,
        actor=admin,
        payload=ConditionProfileCreateRequest(
            code="HTN",
            display_name="Hypertension",
            default_interval_value=3,
            default_interval_unit=RecallIntervalUnit.MONTHS,
            keyword_synonyms=["hypertension", "high bp"],
            justification="setup",
        ),
    )
    assert profile.code == "HTN"

    mapping = service.create_diagnosis_mapping(
        clinic_id=clinic_id,
        actor=admin,
        payload=DiagnosisConditionMapCreateRequest(
            diagnosis_system=DiagnosisSystem.ICD10,
            diagnosis_code="I10",
            condition_profile_id=profile.id,
            confidence=DiagnosisMappingConfidence.HIGH,
            justification="map",
        ),
    )
    assert mapping.diagnosis_code == "I10"
    assert mapping.active is True


def test_clinician_can_create_recall_with_assigned_context(db, clinic_id):
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    patient = _create_patient(db, clinic_id)
    visit = _create_active_visit(db, clinic_id, patient.id, doctor.id)

    config_service = FollowUpConfigurationService(db)
    profile = config_service.create_condition_profile(
        clinic_id=clinic_id,
        actor=admin,
        payload=ConditionProfileCreateRequest(
            code="DM",
            display_name="Diabetes",
            default_interval_value=1,
            default_interval_unit=RecallIntervalUnit.MONTHS,
            keyword_synonyms=["diabetes"],
            justification="setup",
        ),
    )

    recall_service = ChronicRecallService(db)
    recall = recall_service.create_recall(
        clinic_id=clinic_id,
        actor=doctor,
        payload=ChronicRecallCreateRequest(
            patient_id=patient.id,
            condition_profile_id=profile.id,
            origin_visit_id=visit.id,
            justification="start recall",
        ),
    )
    assert recall.patient_id_canonical == patient.id
    assert recall.condition_profile_id == profile.id


def test_reception_cannot_create_recall(db, clinic_id):
    reception = _create_user(db, clinic_id, UserRole.RECEPTION)
    patient = _create_patient(db, clinic_id)
    recall_service = ChronicRecallService(db)

    with pytest.raises(HTTPException) as exc:
        recall_service.create_recall(
            clinic_id=clinic_id,
            actor=reception,
            payload=ChronicRecallCreateRequest(
                patient_id=patient.id,
                condition_profile_id=uuid.uuid4(),
                justification="attempt",
            ),
        )

    assert exc.value.status_code == 403


def test_recall_creation_writes_canonical_patient_id(db, clinic_id):
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    canonical_patient = _create_patient(db, clinic_id)
    alias_patient = _create_patient(db, clinic_id)
    _create_active_visit(db, clinic_id, canonical_patient.id, doctor.id)

    db.add(
        PatientIdentityMap(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            from_patient_id=alias_patient.id,
            to_patient_id=canonical_patient.id,
            mapped_at=datetime.now(timezone.utc),
            mapped_by=admin.id,
        )
    )
    db.commit()

    config_service = FollowUpConfigurationService(db)
    profile = config_service.create_condition_profile(
        clinic_id=clinic_id,
        actor=admin,
        payload=ConditionProfileCreateRequest(
            code="HTN",
            display_name="Hypertension",
            default_interval_value=3,
            default_interval_unit=RecallIntervalUnit.MONTHS,
            keyword_synonyms=["hypertension"],
            justification="setup",
        ),
    )

    recall_service = ChronicRecallService(db)
    recall = recall_service.create_recall(
        clinic_id=clinic_id,
        actor=doctor,
        payload=ChronicRecallCreateRequest(
            patient_id=alias_patient.id,
            condition_profile_id=profile.id,
            justification="start recall from alias id",
        ),
    )

    assert recall.patient_id_canonical == canonical_patient.id
