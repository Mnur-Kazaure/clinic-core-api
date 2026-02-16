import uuid
from datetime import datetime, timedelta, timezone

from app.models.admission import Admission
from app.models.chronic_recall import ChronicRecall
from app.models.condition_profile import ConditionProfile
from app.models.follow_up import FollowUp
from app.models.follow_up_status_history import FollowUpStatusHistory
from app.models.patient import Patient
from app.models.user import User
from app.services.follow_up_generation_service import ChronicRecallGenerator
from app.shared.enums import (
    AdmissionStatus,
    AdmissionType,
    FollowUpGeneratedBy,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    Gender,
    RecallIntervalUnit,
    UserRole,
)


def _create_user(db, clinic_id, role: UserRole) -> User:
    user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"{role.value.lower()}_{uuid.uuid4()}@example.test",
        password_hash="test",
        full_name=f"{role.value.title()} User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def _create_patient(db, clinic_id) -> Patient:
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Follow-up Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Sample address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_condition_profile(db, clinic_id, created_by: uuid.UUID, code: str, display_name: str) -> ConditionProfile:
    profile = ConditionProfile(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code=code,
        display_name=display_name,
        recall_enabled=True,
        default_interval_value=1,
        default_interval_unit=RecallIntervalUnit.MONTHS,
        default_priority=FollowUpPriority.IMPORTANT,
        cooldown_days=90,
        keyword_synonyms=[display_name.lower()],
        created_by=created_by,
    )
    db.add(profile)
    db.commit()
    return profile


def _create_due_recall(
    db,
    *,
    clinic_id,
    patient_id,
    condition_profile_id,
    clinician_id,
    created_by,
    next_due_at: datetime,
) -> ChronicRecall:
    recall = ChronicRecall(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id_canonical=patient_id,
        condition_profile_id=condition_profile_id,
        assigned_clinician_id=clinician_id,
        interval_value=1,
        interval_unit=RecallIntervalUnit.MONTHS,
        next_due_at=next_due_at,
        active=True,
        generation_paused=False,
        created_by=created_by,
    )
    db.add(recall)
    db.commit()
    return recall


def _create_scheduled_follow_up(
    db,
    *,
    clinic_id,
    patient_id,
    owner_user_id,
    due_at: datetime,
    chronic_recall_id=None,
    reason="Recall review",
) -> FollowUp:
    row = FollowUp(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id_canonical=patient_id,
        type=FollowUpType.CHRONIC_RECALL if chronic_recall_id else FollowUpType.MANUAL,
        priority=FollowUpPriority.IMPORTANT,
        status=FollowUpStatus.SCHEDULED,
        due_at=due_at,
        owner_user_id=owner_user_id,
        reason=reason,
        chronic_recall_id=chronic_recall_id,
        generated_by=FollowUpGeneratedBy.SYSTEM if chronic_recall_id else FollowUpGeneratedBy.USER,
        created_by=owner_user_id,
    )
    db.add(row)
    db.commit()
    return row


def test_followup_generation_idempotent_no_duplicates(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    clinician = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(db, clinic_id, admin.id, "HTN", "Hypertension")
    due_at = datetime.now(timezone.utc) - timedelta(hours=1)
    recall = _create_due_recall(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        condition_profile_id=profile.id,
        clinician_id=clinician.id,
        created_by=admin.id,
        next_due_at=due_at,
    )

    generator = ChronicRecallGenerator(db)
    first_stats = generator.run_due_generation(now=datetime.now(timezone.utc))
    second_stats = generator.run_due_generation(now=datetime.now(timezone.utc))

    scheduled = (
        db.query(FollowUp)
        .filter(
            FollowUp.clinic_id == clinic_id,
            FollowUp.chronic_recall_id == recall.id,
            FollowUp.status == FollowUpStatus.SCHEDULED,
        )
        .all()
    )
    db.refresh(recall)

    assert first_stats["generated_follow_ups"] == 1
    assert second_stats["generated_follow_ups"] == 0
    assert len(scheduled) == 1
    assert recall.last_generated_due_at is not None
    assert recall.next_due_at.replace(tzinfo=timezone.utc) > due_at


def test_followup_generation_atomicity_conflict_does_not_advance_next_due(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    clinician = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(db, clinic_id, admin.id, "DM", "Diabetes")
    due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    recall = _create_due_recall(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        condition_profile_id=profile.id,
        clinician_id=clinician.id,
        created_by=admin.id,
        next_due_at=due_at,
    )
    _create_scheduled_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=clinician.id,
        due_at=due_at,
        chronic_recall_id=recall.id,
        reason="Existing generated follow-up",
    )

    generator = ChronicRecallGenerator(db)
    stats = generator.run_due_generation(now=datetime.now(timezone.utc))
    db.refresh(recall)

    assert stats["generation_conflicts"] == 1
    assert recall.next_due_at.replace(tzinfo=timezone.utc) == due_at


def test_inpatient_suppression_blocks_generation_for_active_admission(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    clinician = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    profile = _create_condition_profile(db, clinic_id, admin.id, "ASTHMA", "Asthma")
    due_at = datetime.now(timezone.utc) - timedelta(hours=12)
    recall = _create_due_recall(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        condition_profile_id=profile.id,
        clinician_id=clinician.id,
        created_by=admin.id,
        next_due_at=due_at,
    )
    db.add(
        Admission(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patient.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    db.commit()

    generator = ChronicRecallGenerator(db)
    stats = generator.run_due_generation(now=datetime.now(timezone.utc))
    db.refresh(recall)
    scheduled_count = db.query(FollowUp).filter(FollowUp.chronic_recall_id == recall.id).count()

    assert stats["generated_follow_ups"] == 0
    assert stats["suppressed_active_admission"] == 1
    assert scheduled_count == 0
    assert recall.next_due_at.replace(tzinfo=timezone.utc) == due_at


def test_missed_rule_transitions_after_24h_grace_window(db, clinic_id):
    clinician = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    due_at = datetime.now(timezone.utc) - timedelta(hours=25)
    follow_up = _create_scheduled_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=clinician.id,
        due_at=due_at,
    )

    generator = ChronicRecallGenerator(db)
    stats = generator.run_due_generation(now=datetime.now(timezone.utc))
    db.refresh(follow_up)
    history = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == follow_up.id)
        .one()
    )

    assert stats["missed_transitions"] == 1
    assert follow_up.status == FollowUpStatus.MISSED
    assert history.old_status == FollowUpStatus.SCHEDULED
    assert history.new_status == FollowUpStatus.MISSED


def test_followup_generation_inpatient_suppression_is_clinic_scoped(db, clinic_id):
    clinic_b = uuid.uuid4()
    admin_a = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    doctor_a = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient_a = _create_patient(db, clinic_id)
    profile_a = _create_condition_profile(db, clinic_id, admin_a.id, "CKD", "Chronic Kidney Disease")
    recall_a = _create_due_recall(
        db,
        clinic_id=clinic_id,
        patient_id=patient_a.id,
        condition_profile_id=profile_a.id,
        clinician_id=doctor_a.id,
        created_by=admin_a.id,
        next_due_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    admin_b = _create_user(db, clinic_b, UserRole.CLINIC_ADMIN)
    doctor_b = _create_user(db, clinic_b, UserRole.DOCTOR)
    patient_b = _create_patient(db, clinic_b)
    profile_b = _create_condition_profile(db, clinic_b, admin_b.id, "HF", "Heart Failure")
    _create_due_recall(
        db,
        clinic_id=clinic_b,
        patient_id=patient_b.id,
        condition_profile_id=profile_b.id,
        clinician_id=doctor_b.id,
        created_by=admin_b.id,
        next_due_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(
        Admission(
            id=uuid.uuid4(),
            clinic_id=clinic_b,
            patient_id=patient_b.id,
            admission_type=AdmissionType.EMERGENCY,
            status=AdmissionStatus.ACTIVE,
            admitted_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
    )
    db.commit()

    generator = ChronicRecallGenerator(db)
    stats = generator.run_due_generation(now=datetime.now(timezone.utc))
    follow_ups_a = db.query(FollowUp).filter(FollowUp.clinic_id == clinic_id).all()
    follow_ups_b = db.query(FollowUp).filter(FollowUp.clinic_id == clinic_b).all()

    assert stats["generated_follow_ups"] == 1
    assert stats["suppressed_active_admission"] == 1
    assert len(follow_ups_a) == 1
    assert follow_ups_a[0].chronic_recall_id == recall_a.id
    assert follow_ups_a[0].clinic_id == clinic_id
    assert follow_ups_b == []
