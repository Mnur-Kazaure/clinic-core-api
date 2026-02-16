import uuid
from datetime import datetime, timedelta, timezone

from app.models.access_log import AccessLog
from app.models.chronic_recall import ChronicRecall
from app.models.condition_profile import ConditionProfile
from app.models.consultation import Consultation
from app.models.event_log import EventLog
from app.models.follow_up import FollowUp
from app.models.follow_up_status_history import FollowUpStatusHistory
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.services.consultation_service import ConsultationService
from app.services.follow_up_workflow_service import FollowUpWorkflowService
from app.services.pmr_service import PMRService
from app.shared.enums import (
    FollowUpGeneratedBy,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    Gender,
    PurposeOfUse,
    RecallIntervalUnit,
    RecordStatus,
    UserRole,
    VisitStatus,
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


def _create_patient(db, clinic_id, full_name: str = "Follow-Up Patient") -> Patient:
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name=full_name,
        date_of_birth=datetime(1990, 1, 1).date(),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Test address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_follow_up(
    db,
    *,
    clinic_id,
    patient_id,
    owner_user_id,
    status: FollowUpStatus = FollowUpStatus.SCHEDULED,
    follow_up_type: FollowUpType = FollowUpType.MANUAL,
    due_at: datetime | None = None,
    generated_by: FollowUpGeneratedBy = FollowUpGeneratedBy.USER,
    chronic_recall_id=None,
    completed_visit_id=None,
    completed_at=None,
) -> FollowUp:
    follow_up = FollowUp(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id_canonical=patient_id,
        type=follow_up_type,
        priority=FollowUpPriority.IMPORTANT,
        status=status,
        due_at=due_at or datetime.now(timezone.utc),
        owner_user_id=owner_user_id,
        reason="Follow-up care",
        chronic_recall_id=chronic_recall_id,
        generated_by=generated_by,
        created_by=owner_user_id,
        completed_visit_id=completed_visit_id,
        completed_at=completed_at,
    )
    db.add(follow_up)
    db.commit()
    return follow_up


def test_reception_reschedule_creates_replacement_and_history(db, clinic_id):
    reception = _create_user(db, clinic_id, UserRole.RECEPTION)
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    original = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.SCHEDULED,
        due_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    service = FollowUpWorkflowService(db)
    replacement = service.reschedule_follow_up(
        clinic_id=clinic_id,
        follow_up_id=original.id,
        actor=reception,
        due_at=datetime.now(timezone.utc) + timedelta(days=5),
        reason="Patient requested another date",
        justification="Reception follow-up reschedule",
    )

    db.refresh(original)
    history = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == original.id)
        .one()
    )
    access_logs = (
        db.query(AccessLog)
        .filter(
            AccessLog.clinic_id == clinic_id,
            AccessLog.resource == "FOLLOW_UP",
            AccessLog.action == "WRITE",
        )
        .all()
    )
    access_events = (
        db.query(EventLog)
        .filter(
            EventLog.clinic_id == clinic_id,
            EventLog.event_type == "ACCESS_LOGGED",
        )
        .all()
    )

    assert original.status == FollowUpStatus.CANCELLED
    assert original.cancel_reason_code == "RESCHEDULED"
    assert replacement.status == FollowUpStatus.SCHEDULED
    assert replacement.rescheduled_from_id == original.id
    assert history.old_status == FollowUpStatus.SCHEDULED
    assert history.new_status == FollowUpStatus.CANCELLED
    assert history.reason == "RESCHEDULED"
    assert len(access_logs) == 1
    assert len(access_events) == 1


def test_consultation_sign_completes_linked_follow_up(db, clinic_id):
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        linked_follow_up_id=None,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()

    follow_up = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.SCHEDULED,
        due_at=datetime.now(timezone.utc),
    )
    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        diagnosis="ICD10:I10 Hypertension",
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()

    service = ConsultationService(db)
    service.complete_consultation(
        consultation,
        doctor,
        linked_follow_up_id=follow_up.id,
    )

    db.refresh(follow_up)
    history = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == follow_up.id)
        .one()
    )
    assert follow_up.status == FollowUpStatus.COMPLETED
    assert follow_up.completed_visit_id == visit.id
    assert follow_up.completed_at is not None
    assert history.old_status == FollowUpStatus.SCHEDULED
    assert history.new_status == FollowUpStatus.COMPLETED


def test_consultation_sign_without_link_does_not_mutate_follow_up(db, clinic_id):
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()

    follow_up = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.SCHEDULED,
    )
    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime.now(timezone.utc),
        diagnosis="General review",
        record_status=RecordStatus.DRAFT,
    )
    db.add(consultation)
    db.commit()

    service = ConsultationService(db)
    service.complete_consultation(consultation, doctor)

    db.refresh(follow_up)
    history_rows = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == follow_up.id)
        .all()
    )

    assert follow_up.status == FollowUpStatus.SCHEDULED
    assert follow_up.completed_visit_id is None
    assert history_rows == []


def test_pmr_timeline_surfaces_follow_up_events(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    reception = _create_user(db, clinic_id, UserRole.RECEPTION)
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id)

    profile = ConditionProfile(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="HTN",
        display_name="Hypertension",
        recall_enabled=True,
        default_interval_value=3,
        default_interval_unit=RecallIntervalUnit.MONTHS,
        default_priority=FollowUpPriority.IMPORTANT,
        cooldown_days=90,
        keyword_synonyms=["hypertension"],
        created_by=admin.id,
    )
    db.add(profile)
    db.commit()

    recall = ChronicRecall(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id_canonical=patient.id,
        condition_profile_id=profile.id,
        assigned_clinician_id=doctor.id,
        interval_value=3,
        interval_unit=RecallIntervalUnit.MONTHS,
        next_due_at=datetime.now(timezone.utc) + timedelta(days=90),
        active=True,
        created_by=admin.id,
    )
    db.add(recall)
    db.commit()

    follow_up_generated = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        follow_up_type=FollowUpType.CHRONIC_RECALL,
        status=FollowUpStatus.SCHEDULED,
        generated_by=FollowUpGeneratedBy.SYSTEM,
        chronic_recall_id=recall.id,
    )

    completed_visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.COMPLETED,
    )
    db.add(completed_visit)
    db.commit()
    _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.COMPLETED,
        completed_visit_id=completed_visit.id,
        completed_at=datetime.now(timezone.utc),
    )

    follow_up_missed = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.MISSED,
    )
    follow_up_cancelled = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        status=FollowUpStatus.CANCELLED,
    )
    db.add_all(
        [
            FollowUpStatusHistory(
                id=uuid.uuid4(),
                follow_up_id=follow_up_missed.id,
                old_status=FollowUpStatus.SCHEDULED,
                new_status=FollowUpStatus.MISSED,
                actor_user_id=doctor.id,
                reason="Missed visit",
                changed_at=datetime.now(timezone.utc),
            ),
            FollowUpStatusHistory(
                id=uuid.uuid4(),
                follow_up_id=follow_up_cancelled.id,
                old_status=FollowUpStatus.SCHEDULED,
                new_status=FollowUpStatus.CANCELLED,
                actor_user_id=admin.id,
                reason="Rescheduled",
                changed_at=datetime.now(timezone.utc),
            ),
        ]
    )
    db.commit()

    response = PMRService(db).get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="Reception PMR follow-up timeline review",
        limit=20,
        cursor=None,
        detail_level="SUMMARY",
        break_glass=False,
    )
    event_types = {item["event_type"] for item in response["follow_up_timeline"]}

    assert follow_up_generated.id is not None
    assert {
        "RECALL_CREATED",
        "FOLLOW_UP_GENERATED",
        "FOLLOW_UP_COMPLETED",
        "FOLLOW_UP_MISSED",
        "FOLLOW_UP_CANCELLED",
    }.issubset(event_types)


def test_triple_visibility_dashboards_and_audit_once_per_call(db, clinic_id):
    admin = _create_user(db, clinic_id, UserRole.CLINIC_ADMIN)
    reception = _create_user(db, clinic_id, UserRole.RECEPTION)
    doctor = _create_user(db, clinic_id, UserRole.DOCTOR)
    patient = _create_patient(db, clinic_id, full_name="Triple Visibility Patient")

    follow_up = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=doctor.id,
        follow_up_type=FollowUpType.CHRONIC_RECALL,
        status=FollowUpStatus.SCHEDULED,
        generated_by=FollowUpGeneratedBy.SYSTEM,
        due_at=datetime.now(timezone.utc),
    )

    follow_up_service = FollowUpWorkflowService(db)
    pmr_service = PMRService(db)

    before_access_count = db.query(AccessLog).count()
    before_access_event_count = (
        db.query(EventLog).filter(EventLog.event_type == "ACCESS_LOGGED").count()
    )

    clinician_data = follow_up_service.list_clinician_follow_ups(
        clinic_id=clinic_id,
        actor=doctor,
        purpose_of_use=PurposeOfUse.TREATMENT,
        justification="Clinician follow-up dashboard review",
    )
    reception_data = follow_up_service.list_reception_follow_ups(
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="Reception follow-up dashboard review",
    )
    pmr_data = pmr_service.get_pmr(
        patient_id=patient.id,
        clinic_id=clinic_id,
        actor=reception,
        purpose_of_use=PurposeOfUse.OPERATIONS,
        justification="Reception PMR follow-up timeline review",
        limit=20,
        cursor=None,
        detail_level="SUMMARY",
        break_glass=False,
    )

    clinician_ids = {
        item["id"]
        for group in ("overdue", "today", "upcoming")
        for item in clinician_data[group]
    }
    reception_ids = {
        item["id"]
        for group in ("today", "tomorrow")
        for item in reception_data[group]
    }
    pmr_event_types = {item["event_type"] for item in pmr_data["follow_up_timeline"]}

    after_access_count = db.query(AccessLog).count()
    after_access_event_count = (
        db.query(EventLog).filter(EventLog.event_type == "ACCESS_LOGGED").count()
    )

    assert follow_up.id in clinician_ids
    assert follow_up.id in reception_ids
    assert "FOLLOW_UP_GENERATED" in pmr_event_types
    assert after_access_count - before_access_count == 3
    assert after_access_event_count - before_access_event_count == 3
