from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.shared.enums import (
    LabWorkspaceAttentionKey,
    LabWorkspaceTabKey,
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabQcStatus,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenRejectionReasonCode,
    LabSpecimenStatus,
)


class LabWorkspaceOverviewResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    pending_requests: int
    awaiting_specimen: int
    pending_verifications: int
    critical_alerts: int
    completed_today: int
    qc_failures: int
    unrouted_requests: int


class LabWorkspaceAttentionItemResponse(BaseModel):
    key: LabWorkspaceAttentionKey
    label: str
    count: int
    tone: str
    target_tab: LabWorkspaceTabKey


class LabWorkspaceTabBadgeResponse(BaseModel):
    tab_key: LabWorkspaceTabKey
    count: int
    tone: str


class LabWorkspaceBenchSnapshotResponse(BaseModel):
    generated_at: datetime
    unit_id: UUID
    unit_name: str
    pending_requests: int
    awaiting_specimen: int
    pending_verifications: int
    critical_alerts: int
    completed_today: int
    qc_failures: int
    unrouted_requests: int
    specimen_issue_count: int
    result_workbench_count: int
    queue_count: int
    qc_attention_count: int
    attention_items: list[LabWorkspaceAttentionItemResponse]
    tab_badges: list[LabWorkspaceTabBadgeResponse]


class LabWorkspaceSpecimenSummaryResponse(BaseModel):
    id: UUID
    accession_number: str
    request_item_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str
    target_unit_id: UUID
    target_unit_name: str | None = None
    status: LabSpecimenStatus
    specimen_type: str
    specimen_source: str
    container_type: str | None = None
    collection_site: str | None = None
    collected_at: datetime | None = None
    received_at: datetime | None = None
    rejection_reason_code: LabSpecimenRejectionReasonCode | None = None
    rejection_reason_text: str | None = None
    created_at: datetime
    updated_at: datetime


class LabWorkspaceQcRunSummaryResponse(BaseModel):
    id: UUID
    unit_id: UUID
    unit_name: str | None = None
    machine_id: UUID | None = None
    qc_level: str
    status: LabQcStatus
    performed_by: UUID
    performed_at: datetime
    fail_count: int
    warning_count: int
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LabManagerUnitMetricResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    pending_requests: int
    awaiting_specimen: int
    pending_verifications: int
    critical_alerts: int
    qc_failures: int
    specimen_issues: int
    completed_today: int


class LabManagerRequestSummaryResponse(BaseModel):
    request_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str
    status: LabRequestStatus
    workflow_status: LabRequestWorkflowStatus
    unit_id: UUID | None = None
    unit_name: str | None = None
    latest_result_id: UUID | None = None
    latest_result_status: LabResultLifecycleStatus | None = None
    created_at: datetime


class LabManagerCriticalAlertSummaryResponse(BaseModel):
    alert_id: UUID
    result_id: UUID | None = None
    request_item_id: UUID | None = None
    visit_id: UUID | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    severity: LabCriticalAlertSeverity
    status: LabCriticalAlertStatus
    message: str
    created_at: datetime


class LabManagerQcFailureSummaryResponse(BaseModel):
    qc_run_id: UUID
    qc_result_id: UUID
    unit_id: UUID
    unit_name: str | None = None
    qc_level: str
    analyte_name: str
    expected_min: float | None = None
    expected_max: float | None = None
    observed_value: float
    performed_at: datetime


class LabManagerSpecimenIssueSummaryResponse(BaseModel):
    specimen_id: UUID
    accession_number: str
    request_item_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    test_name: str
    unit_id: UUID
    unit_name: str | None = None
    status: LabSpecimenStatus
    rejection_reason_code: LabSpecimenRejectionReasonCode | None = None
    rejection_reason_text: str | None = None
    updated_at: datetime


class LabManagerOverviewResponse(BaseModel):
    total_pending_requests: int
    total_pending_verifications: int
    total_critical_alerts: int
    total_qc_failures: int
    total_specimen_issues: int
    unrouted_requests: int
    unit_metrics: list[LabManagerUnitMetricResponse]
    pending_verifications: list[LabManagerRequestSummaryResponse]
    critical_alerts: list[LabManagerCriticalAlertSummaryResponse]
    qc_failures: list[LabManagerQcFailureSummaryResponse]
    specimen_issues: list[LabManagerSpecimenIssueSummaryResponse]
