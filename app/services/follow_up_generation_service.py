from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.chronic_recall import ChronicRecall
from app.models.condition_profile import ConditionProfile
from app.models.follow_up import FollowUp
from app.models.follow_up_status_history import FollowUpStatusHistory
from app.shared.enums import AdmissionStatus, FollowUpGeneratedBy, FollowUpStatus, FollowUpType


MISSED_GRACE_WINDOW = timedelta(hours=24)
MISSED_REASON = "Automatic MISSED transition after due_at + 24h grace window"


class ChronicRecallGenerator:
    def __init__(self, db: Session):
        self.db = db

    def run_due_generation(
        self,
        *,
        now: datetime | None = None,
        batch_size: int = 200,
    ) -> dict[str, int]:
        effective_now = now or datetime.now(timezone.utc)
        stats = {
            "scanned_recalls": 0,
            "generated_follow_ups": 0,
            "generation_conflicts": 0,
            "suppressed_active_admission": 0,
            "missed_transitions": 0,
        }

        due_recall_ids = self._get_due_recall_ids(now=effective_now, batch_size=batch_size)
        stats["scanned_recalls"] = len(due_recall_ids)

        for recall_id in due_recall_ids:
            outcome = self._generate_follow_up_for_recall(recall_id=recall_id, now=effective_now)
            if outcome == "generated":
                stats["generated_follow_ups"] += 1
            elif outcome == "conflict":
                stats["generation_conflicts"] += 1
            elif outcome == "suppressed":
                stats["suppressed_active_admission"] += 1

        stats["missed_transitions"] = self._transition_missed_follow_ups(
            now=effective_now,
            batch_size=batch_size,
        )
        return stats

    def _get_due_recall_ids(self, *, now: datetime, batch_size: int) -> list:
        rows = (
            self.db.query(ChronicRecall.id)
            .filter(
                ChronicRecall.active.is_(True),
                ChronicRecall.generation_paused.is_(False),
                ChronicRecall.next_due_at <= now,
            )
            .order_by(ChronicRecall.next_due_at.asc(), ChronicRecall.id.asc())
            .limit(batch_size)
            .all()
        )
        return [row.id for row in rows]

    def _generate_follow_up_for_recall(
        self,
        *,
        recall_id,
        now: datetime,
    ) -> str:
        recall_profile = (
            self.db.query(ChronicRecall, ConditionProfile)
            .join(
                ConditionProfile,
                (ConditionProfile.id == ChronicRecall.condition_profile_id)
                & (ConditionProfile.clinic_id == ChronicRecall.clinic_id),
            )
            .filter(
                ChronicRecall.id == recall_id,
                ChronicRecall.active.is_(True),
                ChronicRecall.generation_paused.is_(False),
                ChronicRecall.next_due_at <= now,
            )
            .first()
        )
        if recall_profile is None:
            return "skipped"

        recall, profile = recall_profile
        if self._has_active_inpatient_admission(
            clinic_id=recall.clinic_id,
            patient_id_canonical=recall.patient_id_canonical,
        ):
            return "suppressed"

        due_at = recall.next_due_at
        follow_up = FollowUp(
            clinic_id=recall.clinic_id,
            patient_id_canonical=recall.patient_id_canonical,
            type=FollowUpType.CHRONIC_RECALL,
            priority=profile.default_priority,
            status=FollowUpStatus.SCHEDULED,
            due_at=due_at,
            owner_user_id=recall.assigned_clinician_id,
            reason=f"{profile.display_name} review",
            chronic_recall_id=recall.id,
            generated_by=FollowUpGeneratedBy.SYSTEM,
            created_by=None,
        )
        self.db.add(follow_up)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return "conflict"

        recall.last_generated_due_at = due_at
        recall.next_due_at = _advance_due(
            due_at,
            interval_value=recall.interval_value,
            interval_unit=recall.interval_unit.value,
        )
        self.db.commit()
        return "generated"

    def _has_active_inpatient_admission(self, *, clinic_id, patient_id_canonical) -> bool:
        row = (
            self.db.query(Admission.id)
            .filter(
                Admission.clinic_id == clinic_id,
                Admission.patient_id == patient_id_canonical,
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .first()
        )
        return row is not None

    def _transition_missed_follow_ups(self, *, now: datetime, batch_size: int) -> int:
        threshold = now - MISSED_GRACE_WINDOW
        due_follow_ups = (
            self.db.query(FollowUp)
            .filter(
                FollowUp.status == FollowUpStatus.SCHEDULED,
                FollowUp.completed_visit_id.is_(None),
                FollowUp.due_at < threshold,
            )
            .order_by(FollowUp.due_at.asc(), FollowUp.id.asc())
            .limit(batch_size)
            .all()
        )
        if not due_follow_ups:
            return 0

        transitioned = 0
        for follow_up in due_follow_ups:
            old_status = follow_up.status
            follow_up.status = FollowUpStatus.MISSED
            self.db.add(
                FollowUpStatusHistory(
                    follow_up_id=follow_up.id,
                    old_status=old_status,
                    new_status=FollowUpStatus.MISSED,
                    actor_user_id=None,
                    reason=MISSED_REASON,
                    changed_at=now,
                )
            )
            transitioned += 1
        self.db.commit()
        return transitioned


def _advance_due(base_due_at: datetime, *, interval_value: int, interval_unit: str) -> datetime:
    if interval_unit == "DAYS":
        return base_due_at + timedelta(days=interval_value)
    if interval_unit == "WEEKS":
        return base_due_at + timedelta(weeks=interval_value)
    return base_due_at + timedelta(days=interval_value * 30)
