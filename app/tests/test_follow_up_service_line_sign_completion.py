import uuid
from datetime import datetime, timezone

from app.models.follow_up import FollowUp
from app.models.follow_up_status_history import FollowUpStatusHistory
from app.models.patient import Patient
from app.models.pregnancy_episode import PregnancyEpisode
from app.models.user import User
from app.models.visit import Visit
from app.schemas.anc import ANCEncounterUpsert
from app.schemas.maternity import MaternityDeliveryUpsert
from app.services.anc_service import ANCService
from app.services.maternity_service import MaternityService
from app.shared.enums import (
    FollowUpGeneratedBy,
    FollowUpPriority,
    FollowUpStatus,
    FollowUpType,
    Gender,
    PregnancyEpisodeStatus,
    VisitServiceLine,
    VisitStatus,
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
        full_name="Service Line Follow-Up Patient",
        date_of_birth=datetime(1991, 1, 1).date(),
        gender=Gender.FEMALE,
        phone_number="08000000000",
        address="Test address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()
    return patient


def _create_follow_up(db, *, clinic_id, patient_id, owner_user_id, status: FollowUpStatus):
    follow_up = FollowUp(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id_canonical=patient_id,
        type=FollowUpType.MANUAL,
        priority=FollowUpPriority.IMPORTANT,
        status=status,
        due_at=datetime.now(timezone.utc),
        owner_user_id=owner_user_id,
        reason="Linked follow-up",
        generated_by=FollowUpGeneratedBy.USER,
        created_by=owner_user_id,
    )
    db.add(follow_up)
    db.commit()
    return follow_up


def test_anc_sign_completes_linked_follow_up(db, clinic_id):
    chew = _create_user(db, clinic_id, UserRole.CHEW)
    patient = _create_patient(db, clinic_id)
    follow_up = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=chew.id,
        status=FollowUpStatus.SCHEDULED,
    )
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=chew.id,
        status=VisitStatus.TRIAGED,
        service_line=VisitServiceLine.ANC,
        linked_follow_up_id=follow_up.id,
    )
    db.add(visit)
    db.commit()
    episode = PregnancyEpisode(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        status=PregnancyEpisodeStatus.ACTIVE,
        created_by=chew.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(episode)
    db.commit()

    ANCService(db).upsert_encounter(
        clinic_id=clinic_id,
        visit_id=visit.id,
        actor_id=chew.id,
        payload=ANCEncounterUpsert(
            action="SIGN",
            episode_id=episode.id,
            remarks="Signed ANC encounter",
        ),
    )

    db.refresh(follow_up)
    history = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == follow_up.id)
        .order_by(FollowUpStatusHistory.changed_at.desc())
        .first()
    )
    assert follow_up.status == FollowUpStatus.COMPLETED
    assert follow_up.completed_visit_id == visit.id
    assert follow_up.completed_at is not None
    assert history is not None
    assert history.new_status == FollowUpStatus.COMPLETED


def test_maternity_sign_completes_linked_follow_up(db, clinic_id):
    midwife = _create_user(db, clinic_id, UserRole.MIDWIFE)
    patient = _create_patient(db, clinic_id)
    follow_up = _create_follow_up(
        db,
        clinic_id=clinic_id,
        patient_id=patient.id,
        owner_user_id=midwife.id,
        status=FollowUpStatus.MISSED,
    )
    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=midwife.id,
        status=VisitStatus.TRIAGED,
        service_line=VisitServiceLine.MATERNITY,
        linked_follow_up_id=follow_up.id,
    )
    db.add(visit)
    db.commit()

    MaternityService(db).upsert_delivery(
        clinic_id=clinic_id,
        visit_id=visit.id,
        actor_id=midwife.id,
        payload=MaternityDeliveryUpsert(
            action="SIGN",
            notes="Signed maternity delivery",
        ),
    )

    db.refresh(follow_up)
    history = (
        db.query(FollowUpStatusHistory)
        .filter(FollowUpStatusHistory.follow_up_id == follow_up.id)
        .order_by(FollowUpStatusHistory.changed_at.desc())
        .first()
    )
    assert follow_up.status == FollowUpStatus.COMPLETED
    assert follow_up.completed_visit_id == visit.id
    assert follow_up.completed_at is not None
    assert history is not None
    assert history.new_status == FollowUpStatus.COMPLETED
