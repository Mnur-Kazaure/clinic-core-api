from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_specimen import LabSpecimen
from app.models.service_line import ServiceLine
from app.schemas.lab_workspace import (
    LabWorkspaceAttentionItemResponse,
    LabWorkspaceBenchSnapshotResponse,
    LabWorkspaceTabBadgeResponse,
)
from app.services.lab_workspace_service import (
    SPECIMEN_ISSUE_STATUSES,
    LabWorkspaceService,
)
from app.shared.enums import (
    LabQcStatus,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabWorkspaceAttentionKey,
    LabWorkspaceTabKey,
)


QUEUE_WORKFLOW_STATUSES = frozenset(
    {
        LabRequestWorkflowStatus.ORDERED,
        LabRequestWorkflowStatus.PAID,
        LabRequestWorkflowStatus.AWAITING_SPECIMEN,
    }
)
RESULT_WORKBENCH_WORKFLOW_STATUSES = frozenset(
    {
        LabRequestWorkflowStatus.IN_ANALYSIS,
        LabRequestWorkflowStatus.RESULT_ENTERED,
        LabRequestWorkflowStatus.VERIFIED,
        LabRequestWorkflowStatus.RELEASED,
    }
)
RESULT_WORKBENCH_RESULT_STATUSES = frozenset(
    {
        LabResultLifecycleStatus.DRAFT,
        LabResultLifecycleStatus.SUBMITTED,
        LabResultLifecycleStatus.VERIFIED,
        LabResultLifecycleStatus.RELEASED,
        LabResultLifecycleStatus.AMENDED,
    }
)
QC_ATTENTION_STATUSES = frozenset({LabQcStatus.FAIL, LabQcStatus.WARNING})


class LabWorkspaceAttentionService:
    def __init__(self, db: Session):
        self.db = db
        self.workspace_service = LabWorkspaceService(db)

    def get_snapshot(
        self,
        *,
        clinic_id: UUID,
        unit: ServiceLine,
    ) -> LabWorkspaceBenchSnapshotResponse:
        generated_at = datetime.now(timezone.utc)
        overview = self.workspace_service.get_unit_overview(
            clinic_id=clinic_id,
            unit=unit,
        )
        pending_requests = self.workspace_service.list_unit_requests(
            clinic_id=clinic_id,
            unit_id=unit.id,
            status=LabRequestStatus.PENDING,
        )

        queue_count = sum(
            1
            for request in pending_requests
            if request.workflow_status in QUEUE_WORKFLOW_STATUSES
        )
        result_workbench_count = sum(
            1
            for request in pending_requests
            if (
                request.ready_specimen_count > 0
                or request.latest_result_status in RESULT_WORKBENCH_RESULT_STATUSES
                or request.workflow_status in RESULT_WORKBENCH_WORKFLOW_STATUSES
            )
        )

        specimen_issue_request_ids = {
            request_item_id
            for request_item_id, in (
                self.db.query(LabSpecimen.request_item_id)
                .filter(
                    LabSpecimen.clinic_id == clinic_id,
                    LabSpecimen.target_unit_id == unit.id,
                    LabSpecimen.status.in_(SPECIMEN_ISSUE_STATUSES),
                )
                .distinct()
                .all()
            )
        }
        specimen_attention_request_ids = {
            request.id for request in pending_requests if request.ready_specimen_count == 0
        } | specimen_issue_request_ids
        specimen_issue_count = len(specimen_issue_request_ids)

        qc_status_counts = {
            status: count
            for status, count in (
                self.db.query(LabQcRun.status, func.count(LabQcRun.id))
                .filter(
                    LabQcRun.clinic_id == clinic_id,
                    LabQcRun.unit_id == unit.id,
                    LabQcRun.status.in_(QC_ATTENTION_STATUSES),
                )
                .group_by(LabQcRun.status)
                .all()
            )
        }
        qc_failures = int(qc_status_counts.get(LabQcStatus.FAIL, 0))
        qc_warnings = int(qc_status_counts.get(LabQcStatus.WARNING, 0))
        qc_attention_count = qc_failures + qc_warnings

        attention_items = [
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.PENDING_QUEUE,
                label="Pending Queue",
                count=queue_count,
                tone="info",
                target_tab=LabWorkspaceTabKey.QUEUE,
            ),
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.AWAITING_SPECIMEN,
                label="Awaiting Specimen",
                count=overview.awaiting_specimen,
                tone="warning" if overview.awaiting_specimen else "info",
                target_tab=LabWorkspaceTabKey.SPECIMENS,
            ),
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.PENDING_VERIFICATIONS,
                label="Pending Verification",
                count=overview.pending_verifications,
                tone="warning" if overview.pending_verifications else "info",
                target_tab=LabWorkspaceTabKey.RESULTS,
            ),
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.CRITICAL_ALERTS,
                label="Critical Alerts",
                count=overview.critical_alerts,
                tone="critical" if overview.critical_alerts else "info",
                target_tab=LabWorkspaceTabKey.RESULTS,
            ),
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.QC_FAILURES,
                label="QC Failures",
                count=overview.qc_failures,
                tone="critical" if overview.qc_failures else "info",
                target_tab=LabWorkspaceTabKey.QC,
            ),
            LabWorkspaceAttentionItemResponse(
                key=LabWorkspaceAttentionKey.COMPLETED_TODAY,
                label="Completed Today",
                count=overview.completed_today,
                tone="success" if overview.completed_today else "info",
                target_tab=LabWorkspaceTabKey.COMPLETED,
            ),
        ]

        tab_badges = [
            LabWorkspaceTabBadgeResponse(
                tab_key=LabWorkspaceTabKey.QUEUE,
                count=queue_count,
                tone="info",
            ),
            LabWorkspaceTabBadgeResponse(
                tab_key=LabWorkspaceTabKey.SPECIMENS,
                count=len(specimen_attention_request_ids),
                tone=(
                    "critical"
                    if specimen_issue_count
                    else "warning"
                    if specimen_attention_request_ids
                    else "info"
                ),
            ),
            LabWorkspaceTabBadgeResponse(
                tab_key=LabWorkspaceTabKey.RESULTS,
                count=result_workbench_count,
                tone=(
                    "critical"
                    if overview.critical_alerts
                    else "warning"
                    if result_workbench_count or overview.pending_verifications
                    else "info"
                ),
            ),
            LabWorkspaceTabBadgeResponse(
                tab_key=LabWorkspaceTabKey.QC,
                count=qc_attention_count,
                tone=(
                    "critical"
                    if qc_failures
                    else "warning"
                    if qc_warnings
                    else "info"
                ),
            ),
        ]

        return LabWorkspaceBenchSnapshotResponse(
            generated_at=generated_at,
            unit_id=overview.unit_id,
            unit_name=overview.unit_name,
            pending_requests=overview.pending_requests,
            awaiting_specimen=overview.awaiting_specimen,
            pending_verifications=overview.pending_verifications,
            critical_alerts=overview.critical_alerts,
            completed_today=overview.completed_today,
            qc_failures=overview.qc_failures,
            unrouted_requests=overview.unrouted_requests,
            specimen_issue_count=specimen_issue_count,
            result_workbench_count=result_workbench_count,
            queue_count=queue_count,
            qc_attention_count=qc_attention_count,
            attention_items=attention_items,
            tab_badges=tab_badges,
        )

    def snapshot_signature(self, snapshot: LabWorkspaceBenchSnapshotResponse) -> str:
        payload = {
            "generated_at": snapshot.generated_at.isoformat(),
            "unit_id": str(snapshot.unit_id),
            "attention_items": [
                {
                    "key": item.key.value,
                    "count": item.count,
                    "tone": item.tone,
                }
                for item in snapshot.attention_items
            ],
            "tab_badges": [
                {
                    "tab_key": item.tab_key.value,
                    "count": item.count,
                    "tone": item.tone,
                }
                for item in snapshot.tab_badges
            ],
            "unrouted_requests": snapshot.unrouted_requests,
        }
        return json.dumps(payload, sort_keys=True)
