from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.orm import Session

from app.models.department_governance_section_checkpoint import (
    DepartmentGovernanceSectionCheckpoint,
)
from app.models.event_log import EventLog
from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_specimen import LabSpecimen
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.schemas.lab_manager import (
    LabManagerBadgeSnapshotResponse,
    LabManagerBadgeStateResponse,
)
from app.services.lab_workspace_service import (
    PENDING_VERIFICATION_RESULT_STATUSES,
    SPECIMEN_ISSUE_STATUSES,
    UNRESOLVED_ALERT_STATUSES,
)
from app.shared.enums import (
    GovernanceSectionKey,
    GovernanceWorkspaceKey,
    LabQcStatus,
    LabSpecimenStatus,
)


class LabManagerBadgeService:
    WORKSPACE_KEY = GovernanceWorkspaceKey.LAB_MANAGER.value
    APPROVED_SECTIONS = (
        GovernanceSectionKey.PENDING_VERIFICATIONS,
        GovernanceSectionKey.CRITICAL_ALERTS,
        GovernanceSectionKey.SPECIMEN_ISSUES,
        GovernanceSectionKey.QUALITY_CONTROL,
        GovernanceSectionKey.SALES_REVENUE,
        GovernanceSectionKey.RECEIPT_REGISTER,
    )
    CHECKPOINT_SECTIONS = frozenset(
        {
            GovernanceSectionKey.SPECIMEN_ISSUES,
            GovernanceSectionKey.QUALITY_CONTROL,
            GovernanceSectionKey.SALES_REVENUE,
            GovernanceSectionKey.RECEIPT_REGISTER,
        }
    )
    DELAYED_RECEIPT_MINUTES = 60

    def __init__(self, db: Session):
        self.db = db

    def get_snapshot(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
    ) -> LabManagerBadgeSnapshotResponse:
        generated_at = datetime.now(timezone.utc)
        checkpoints = self._checkpoint_map(
            clinic_id=clinic_id,
            user_id=user_id,
        )
        sections: list[LabManagerBadgeStateResponse] = []
        for section_key in self.APPROVED_SECTIONS:
            sections.append(
                self._build_section_state(
                    clinic_id=clinic_id,
                    generated_at=generated_at,
                    section_key=section_key,
                    last_viewed_at=checkpoints.get(section_key.value),
                )
            )
        return LabManagerBadgeSnapshotResponse(
            generated_at=generated_at,
            sections=sections,
        )

    def mark_section_viewed(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        section_key: GovernanceSectionKey,
    ) -> LabManagerBadgeSnapshotResponse:
        self._assert_supported_section(section_key=section_key)
        now = datetime.now(timezone.utc)
        checkpoint = (
            self.db.query(DepartmentGovernanceSectionCheckpoint)
            .filter(
                DepartmentGovernanceSectionCheckpoint.clinic_id == clinic_id,
                DepartmentGovernanceSectionCheckpoint.user_id == user_id,
                DepartmentGovernanceSectionCheckpoint.workspace_key == self.WORKSPACE_KEY,
                DepartmentGovernanceSectionCheckpoint.section_key == section_key.value,
            )
            .first()
        )
        if checkpoint is None:
            checkpoint = DepartmentGovernanceSectionCheckpoint(
                clinic_id=clinic_id,
                user_id=user_id,
                workspace_key=self.WORKSPACE_KEY,
                section_key=section_key.value,
                last_viewed_at=now,
            )
        else:
            checkpoint.last_viewed_at = now
        self.db.add(checkpoint)
        self.db.commit()
        return self.get_snapshot(clinic_id=clinic_id, user_id=user_id)

    def cursor_signature(self, *, clinic_id: UUID, user_id: UUID) -> str:
        snapshot = self.get_snapshot(clinic_id=clinic_id, user_id=user_id)
        return self.snapshot_signature(snapshot)

    def snapshot_signature(
        self,
        snapshot: LabManagerBadgeSnapshotResponse,
    ) -> str:
        payload = {
            "generated_at": snapshot.generated_at.isoformat(),
            "sections": [
                {
                    "section_key": item.section_key.value,
                    "count": item.count,
                    "tone": item.tone,
                    "last_viewed_at": item.last_viewed_at.isoformat()
                    if item.last_viewed_at
                    else None,
                }
                for item in snapshot.sections
            ],
        }
        return json.dumps(payload, sort_keys=True)

    def _build_section_state(
        self,
        *,
        clinic_id: UUID,
        generated_at: datetime,
        section_key: GovernanceSectionKey,
        last_viewed_at: datetime | None,
    ) -> LabManagerBadgeStateResponse:
        effective_checkpoint = last_viewed_at or generated_at

        if section_key == GovernanceSectionKey.PENDING_VERIFICATIONS:
            count = self._count_pending_verifications(clinic_id=clinic_id)
            tone = "warning" if count else "info"
        elif section_key == GovernanceSectionKey.CRITICAL_ALERTS:
            count = self._count_unresolved_critical_alerts(clinic_id=clinic_id)
            tone = "critical" if count else "info"
        elif section_key == GovernanceSectionKey.SPECIMEN_ISSUES:
            count, tone = self._count_new_specimen_issues(
                clinic_id=clinic_id,
                checkpoint=effective_checkpoint,
                generated_at=generated_at,
            )
        elif section_key == GovernanceSectionKey.QUALITY_CONTROL:
            count, tone = self._count_quality_control_attention(
                clinic_id=clinic_id,
                checkpoint=effective_checkpoint,
            )
        elif section_key == GovernanceSectionKey.SALES_REVENUE:
            count = self._count_new_sales_rows(
                clinic_id=clinic_id,
                checkpoint=effective_checkpoint,
            )
            tone = "info" if count else "info"
        elif section_key == GovernanceSectionKey.RECEIPT_REGISTER:
            count = self._count_new_receipts(
                clinic_id=clinic_id,
                checkpoint=effective_checkpoint,
            )
            tone = "info" if count else "info"
        else:
            raise AssertionError(f"Unsupported badge section: {section_key.value}")

        return LabManagerBadgeStateResponse(
            section_key=section_key,
            count=count,
            tone=tone,
            last_viewed_at=last_viewed_at,
        )

    def _checkpoint_map(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
    ) -> dict[str, datetime]:
        rows = (
            self.db.query(DepartmentGovernanceSectionCheckpoint)
            .filter(
                DepartmentGovernanceSectionCheckpoint.clinic_id == clinic_id,
                DepartmentGovernanceSectionCheckpoint.user_id == user_id,
                DepartmentGovernanceSectionCheckpoint.workspace_key == self.WORKSPACE_KEY,
                DepartmentGovernanceSectionCheckpoint.section_key.in_(
                    [item.value for item in self.APPROVED_SECTIONS]
                ),
            )
            .all()
        )
        return {row.section_key: self._ensure_utc(row.last_viewed_at) for row in rows}

    def _count_pending_verifications(self, *, clinic_id: UUID) -> int:
        return (
            self.db.query(LabResult.id)
            .join(LabRequest, LabRequest.id == LabResult.request_item_id)
            .filter(
                LabResult.clinic_id == clinic_id,
                LabResult.status.in_(PENDING_VERIFICATION_RESULT_STATUSES),
                LabRequest.target_unit_id.isnot(None),
            )
            .count()
        )

    def _count_unresolved_critical_alerts(self, *, clinic_id: UUID) -> int:
        return (
            self.db.query(LabCriticalAlert.id)
            .join(LabRequest, LabRequest.id == LabCriticalAlert.request_item_id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabCriticalAlert.unit_id.isnot(None),
                LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
            )
            .count()
        )

    def _count_new_specimen_issues(
        self,
        *,
        clinic_id: UUID,
        checkpoint: datetime,
        generated_at: datetime,
    ) -> tuple[int, str]:
        delayed_threshold = generated_at - timedelta(minutes=self.DELAYED_RECEIPT_MINUTES)
        rows = (
            self.db.query(LabSpecimen.id, LabSpecimen.status)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                or_(
                    LabSpecimen.updated_at > checkpoint,
                    LabSpecimen.created_at > checkpoint,
                ),
                (
                    LabSpecimen.status.in_(SPECIMEN_ISSUE_STATUSES)
                    | and_(
                        LabSpecimen.status == LabSpecimenStatus.COLLECTED,
                        LabSpecimen.received_at.is_(None),
                        LabSpecimen.collected_at <= delayed_threshold,
                    )
                ),
            )
            .all()
        )
        count = len(rows)
        has_lost = any(status == LabSpecimenStatus.LOST for _, status in rows)
        tone = "critical" if has_lost else "warning" if count else "info"
        return count, tone

    def _count_quality_control_attention(
        self,
        *,
        clinic_id: UUID,
        checkpoint: datetime,
    ) -> tuple[int, str]:
        problem_runs = (
            self.db.query(LabQcRun.id, LabQcRun.status, LabQcRun.performed_at)
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.status.in_([LabQcStatus.FAIL, LabQcStatus.WARNING]),
            )
            .all()
        )
        if not problem_runs:
            return 0, "info"

        override_events = (
            self.db.query(EventLog.payload)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type == "LAB_QC_OVERRIDE",
            )
            .all()
        )
        overridden_run_ids: set[UUID] = set()
        for (payload_text,) in override_events:
            payload = self._parse_json(payload_text)
            metadata = payload.get("metadata_json") if isinstance(payload, dict) else {}
            for raw_run_id in (metadata or {}).get("qc_run_ids", []):
                try:
                    overridden_run_ids.add(UUID(str(raw_run_id)))
                except (TypeError, ValueError):
                    continue

        attention_run_ids: set[UUID] = set()
        has_fail_attention = False
        for run_id, run_status, performed_at in problem_runs:
            if run_status == LabQcStatus.FAIL and run_id not in overridden_run_ids:
                attention_run_ids.add(run_id)
                has_fail_attention = True
                continue
            if (
                run_status == LabQcStatus.WARNING
                and self._ensure_utc(performed_at) > checkpoint
            ):
                attention_run_ids.add(run_id)

        count = len(attention_run_ids)
        tone = "critical" if has_fail_attention and count else "warning" if count else "info"
        return count, tone

    def _count_new_sales_rows(
        self,
        *,
        clinic_id: UUID,
        checkpoint: datetime,
    ) -> int:
        return (
            self.db.query(PaymentReceiptItem.id)
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == PaymentReceiptItem.receipt_id,
                    PaymentReceipt.clinic_id == PaymentReceiptItem.clinic_id,
                ),
            )
            .join(LabRequest, LabRequest.billing_item_id == PaymentReceiptItem.billing_item_id)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at > checkpoint,
                LabRequest.clinic_id == clinic_id,
            )
            .count()
        )

    def _count_new_receipts(
        self,
        *,
        clinic_id: UUID,
        checkpoint: datetime,
    ) -> int:
        return (
            self.db.query(func.count(distinct(PaymentReceipt.id)))
            .join(
                PaymentReceiptItem,
                and_(
                    PaymentReceipt.id == PaymentReceiptItem.receipt_id,
                    PaymentReceipt.clinic_id == PaymentReceiptItem.clinic_id,
                ),
            )
            .join(LabRequest, LabRequest.billing_item_id == PaymentReceiptItem.billing_item_id)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at > checkpoint,
                LabRequest.clinic_id == clinic_id,
            )
            .scalar()
            or 0
        )

    def _assert_supported_section(self, *, section_key: GovernanceSectionKey) -> None:
        if section_key not in self.APPROVED_SECTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Badge checkpoint section is not enabled for the laboratory HOD workspace",
            )

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _parse_json(self, raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
