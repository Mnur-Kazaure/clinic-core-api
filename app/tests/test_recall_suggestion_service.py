import uuid
from datetime import datetime, timedelta, timezone

from app.models.chronic_recall import ChronicRecall
from app.models.condition_profile import ConditionProfile
from app.models.consultation import Consultation
from app.models.diagnosis_condition_map import DiagnosisConditionMap
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.schemas.follow_up import ChronicRecallCreateRequest
from app.services.consultation_service import ConsultationService
from app.services.follow_up_service import ChronicRecallService
from app.services.follow_up_service import RecallSuggestionService
from app.shared.enums import (
    DiagnosisMappingConfidence,
    DiagnosisSystem,
    Gender,
    RecallIntervalUnit,
    VisitStatus,
    UserRole,
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
        full_name="Recall Suggestion Patient",
        date_of_birth=datetime(1992, 1, 1).date(),
        gender=Gender.MALE,
        phone_number="08000000000",
        address="Main street",
        occupation="Civil servant",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_condition_profile(db, clinic_id, created_by, code, name, synonyms, cooldown_days=90):
    profile = ConditionProfile(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code=code,
        display_name=name,
        recall_enabled=True,
        default_interval_value=3,
        default_interval_unit=RecallIntervalUnit.MONTHS,
        cooldown_days=cooldown_days,
        keyword_synonyms=synonyms,
        created_by=created_by,
    )
    db.add(profile)
    db.commit()
    return profile


def _create_mapping(db, clinic_id, created_by, profile_id, system, code):
    mapping = DiagnosisConditionMap(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        diagnosis_system=system,
        diagnosis_code=code,
        condition_profile_id=profile_id,
        confidence=DiagnosisMappingConfidence.HIGH,
        active=True,
        created_by=created_by,
    )
    db.add(mapping)
    db.commit()
    return mapping


def test_recall_suggestion_structured_first_returns_high_confidence(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(
        db,
        clinic_id,
        admin.id,
        code="HTN",
        name="Hypertension",
        synonyms=["hypertension"],
    )
    _create_mapping(
        db,
        clinic_id,
        admin.id,
        profile_id=profile.id,
        system=DiagnosisSystem.ICD10,
        code="I10",
    )

    service = RecallSuggestionService(db)
    suggestions = service.resolve(
        clinic_id=clinic_id,
        patient_id=patient.id,
        diagnosis_text="ICD10:I10 Essential hypertension",
    )

    assert len(suggestions) == 1
    assert suggestions[0]["condition_profile_id"] == profile.id
    assert suggestions[0]["confidence"].value == "HIGH"


def test_recall_suggestion_fallback_only_when_no_structured_code(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(
        db,
        clinic_id,
        admin.id,
        code="ASTHMA",
        name="Asthma",
        synonyms=["asthma", "wheeze"],
    )
    _create_mapping(
        db,
        clinic_id,
        admin.id,
        profile_id=profile.id,
        system=DiagnosisSystem.LOCAL,
        code="AST01",
    )

    service = RecallSuggestionService(db)
    suggestions = service.resolve(
        clinic_id=clinic_id,
        patient_id=patient.id,
        diagnosis_text="Patient has recurrent asthma symptoms",
    )

    assert len(suggestions) == 1
    assert suggestions[0]["condition_profile_id"] == profile.id
    assert suggestions[0]["confidence"].value == "LOW"


def test_recall_suggestion_suppresses_active_recall(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(
        db,
        clinic_id,
        admin.id,
        code="DM",
        name="Diabetes",
        synonyms=["diabetes"],
    )
    _create_mapping(
        db,
        clinic_id,
        admin.id,
        profile_id=profile.id,
        system=DiagnosisSystem.ICD10,
        code="E11",
    )
    db.add(
        ChronicRecall(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id_canonical=patient.id,
            condition_profile_id=profile.id,
            assigned_clinician_id=admin.id,
            interval_value=1,
            interval_unit=RecallIntervalUnit.MONTHS,
            next_due_at=datetime.now(timezone.utc) + timedelta(days=1),
            active=True,
            created_by=admin.id,
        )
    )
    db.commit()

    service = RecallSuggestionService(db)
    suggestions = service.resolve(
        clinic_id=clinic_id,
        patient_id=patient.id,
        diagnosis_text="ICD10:E11 Diabetes mellitus",
    )
    assert suggestions == []


def test_recall_suggestion_respects_cooldown(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(
        db,
        clinic_id,
        admin.id,
        code="CKD",
        name="Chronic kidney disease",
        synonyms=["ckd"],
        cooldown_days=120,
    )
    _create_mapping(
        db,
        clinic_id,
        admin.id,
        profile_id=profile.id,
        system=DiagnosisSystem.LOCAL,
        code="CKD01",
    )
    db.add(
        ChronicRecall(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id_canonical=patient.id,
            condition_profile_id=profile.id,
            assigned_clinician_id=admin.id,
            interval_value=3,
            interval_unit=RecallIntervalUnit.MONTHS,
            next_due_at=datetime.now(timezone.utc) + timedelta(days=90),
            active=False,
            deactivated_at=datetime.now(timezone.utc) - timedelta(days=30),
            deactivated_reason="Transferred out",
            created_by=admin.id,
        )
    )
    db.commit()

    service = RecallSuggestionService(db)
    suggestions = service.resolve(
        clinic_id=clinic_id,
        patient_id=patient.id,
        diagnosis_text="LOCAL:CKD01 CKD follow-up",
    )
    assert suggestions == []


def test_recall_suggestion_tenant_isolation(db, clinic_id):
    other_clinic = uuid.uuid4()
    admin_a = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    admin_b = _create_user(db, other_clinic, UserRole.CLINIC_ADMIN)
    patient_a = _create_patient(db, clinic_id)

    profile_other = _create_condition_profile(
        db,
        other_clinic,
        admin_b.id,
        code="HTN",
        name="Hypertension",
        synonyms=["hypertension"],
    )
    _create_mapping(
        db,
        other_clinic,
        admin_b.id,
        profile_id=profile_other.id,
        system=DiagnosisSystem.ICD10,
        code="I10",
    )

    service = RecallSuggestionService(db)
    suggestions = service.resolve(
        clinic_id=clinic_id,
        patient_id=patient_a.id,
        diagnosis_text="ICD10:I10 Hypertension",
    )
    assert suggestions == []


def test_consultation_sign_returns_suggestion_then_suppresses_after_recall_created(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(
        db,
        clinic_id,
        admin.id,
        code="HTN",
        name="Hypertension",
        synonyms=["hypertension"],
    )
    _create_mapping(
        db,
        clinic_id,
        admin.id,
        profile_id=profile.id,
        system=DiagnosisSystem.ICD10,
        code="I10",
    )

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        diagnosis="ICD10:I10 Essential hypertension",
    )
    db.add(consultation)
    db.commit()

    consultation_service = ConsultationService(db)
    completed = consultation_service.complete_consultation(consultation, doctor)
    assert len(completed.recall_suggestions) == 1
    assert completed.recall_suggestions[0]["condition_profile_id"] == profile.id

    recall_service = ChronicRecallService(db)
    recall_service.create_recall(
        clinic_id=clinic_id,
        actor=doctor,
        payload=ChronicRecallCreateRequest(
            patient_id=patient.id,
            condition_profile_id=profile.id,
            origin_visit_id=visit.id,
            justification="Accept suggestion",
        ),
    )

    second_visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(second_visit)
    db.commit()
    second_consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=second_visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        diagnosis="ICD10:I10 Follow-up",
    )
    db.add(second_consultation)
    db.commit()

    second_completed = consultation_service.complete_consultation(second_consultation, doctor)
    assert second_completed.recall_suggestions == []
