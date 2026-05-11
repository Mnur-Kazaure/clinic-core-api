from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.enums import (
    BillingReasonCode,
    GovernanceSectionKey,
    LabConfigurationRequestStatus,
    LabConfigurationRequestType,
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabQcStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    LabStaffAssignmentStatus,
    LabVerificationPolicy,
    UserRole,
)


class LabManagerDashboardQuery(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class LabManagerLabUnitContextResponse(BaseModel):
    id: UUID
    name: str


class LabManagerOverviewMetricResponse(BaseModel):
    total_tests_today: int
    pending_verifications: int
    critical_alerts_open: int
    rejected_specimens: int
    qc_failures: int
    revenue_today_minor: int
    blocked_unpaid_requests: int
    active_staff_on_duty: int
    currency: str
    bottleneck_units: list[str] = Field(default_factory=list)


class LabManagerUnitOperationResponse(BaseModel):
    unit_id: UUID
    unit_name: str
    queue_volume: int
    staff_on_duty: int
    pending_specimens: int
    pending_results: int
    pending_verifications: int
    rejected_specimens: int
    critical_alerts: int
    qc_failures: int
    completed_today: int
    revenue_today_minor: int
    bottleneck_labels: list[str] = Field(default_factory=list)


class LabManagerStaffSummaryResponse(BaseModel):
    user_id: UUID
    full_name: str | None = None
    email: str
    role: UserRole
    is_active: bool
    assignment_status: LabStaffAssignmentStatus
    coverage_note: str | None = None
    allowed_units: list[LabManagerLabUnitContextResponse] = Field(default_factory=list)
    default_unit_id: UUID | None = None
    default_unit_name: str | None = None
    recent_activity_summary: str | None = None
    recent_activity_at: datetime | None = None
    last_updated_at: datetime | None = None
    last_updated_by_id: UUID | None = None
    last_updated_by_name: str | None = None


class LabManagerStaffAssignmentUpdateRequest(BaseModel):
    allowed_lab_unit_ids: list[UUID] = Field(default_factory=list)
    default_lab_unit_id: UUID | None = None
    assignment_status: LabStaffAssignmentStatus | None = None
    coverage_note: str | None = Field(default=None, max_length=500)


class LabManagerConfigurationRequestCreate(BaseModel):
    request_type: LabConfigurationRequestType
    justification: str = Field(min_length=5)
    linked_staff_id: UUID | None = None
    linked_unit_id: UUID | None = None
    linked_test_code: str | None = Field(default=None, max_length=64)
    request_payload_json: dict[str, Any] | list[Any] | None = None


class LabManagerConfigurationRequestResponse(BaseModel):
    id: UUID
    request_type: LabConfigurationRequestType
    status: LabConfigurationRequestStatus
    department_name: str
    justification: str
    requested_by: UUID
    requested_by_name: str | None = None
    linked_staff_id: UUID | None = None
    linked_staff_name: str | None = None
    linked_unit_id: UUID | None = None
    linked_unit_name: str | None = None
    linked_test_code: str | None = None
    request_payload_json: dict[str, Any] | list[Any] | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class LabManagerPendingVerificationResponse(BaseModel):
    request_id: UUID
    result_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    accession_number: str | None = None
    test_name: str
    unit_id: UUID | None = None
    unit_name: str | None = None
    result_status: LabResultLifecycleStatus
    abnormal: bool
    critical: bool
    waiting_minutes: int
    entered_by: UUID | None = None
    entered_by_name: str | None = None
    verification_policy: LabVerificationPolicy
    created_at: datetime


class LabManagerCriticalAlertResponse(BaseModel):
    alert_id: UUID
    result_id: UUID | None = None
    request_item_id: UUID | None = None
    visit_id: UUID | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    test_name: str | None = None
    severity: LabCriticalAlertSeverity
    status: LabCriticalAlertStatus
    message: str
    created_at: datetime
    acknowledged_at: datetime | None = None
    escalated_at: datetime | None = None
    resolved_at: datetime | None = None


class LabManagerSpecimenIssueResponse(BaseModel):
    specimen_id: UUID
    accession_number: str
    request_item_id: UUID
    visit_id: UUID
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    unit_id: UUID
    unit_name: str | None = None
    test_name: str
    status: LabSpecimenStatus
    issue_type: str
    rejection_reason_code: str | None = None
    rejection_reason_text: str | None = None
    responsible_staff_id: UUID | None = None
    responsible_staff_name: str | None = None
    updated_at: datetime


class LabManagerQualityControlRunResponse(BaseModel):
    qc_run_id: UUID
    unit_id: UUID
    unit_name: str | None = None
    machine_id: UUID | None = None
    qc_level: str
    status: LabQcStatus
    performed_by: UUID
    performed_by_name: str | None = None
    performed_at: datetime
    fail_count: int
    warning_count: int
    override_count: int
    unresolved: bool
    notes: str | None = None


class LabManagerQualityControlSummaryResponse(BaseModel):
    total_runs: int
    fail_runs: int
    warning_runs: int
    override_events: int
    unresolved_failures: int
    runs: list[LabManagerQualityControlRunResponse] = Field(default_factory=list)


class LabManagerActivityAuditItemResponse(BaseModel):
    id: str
    source_type: str
    action_type: str
    occurred_at: datetime
    actor_id: UUID | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    unit_id: UUID | None = None
    unit_name: str | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    visit_id: UUID | None = None
    request_item_id: UUID | None = None
    result_id: UUID | None = None
    specimen_id: UUID | None = None
    accession_number: str | None = None
    receipt_number: str | None = None
    summary: str
    detail: str | None = None
    severity: str = "info"
    metadata_json: dict[str, Any] | list[Any] | None = None


class LabManagerStaffPerformanceResponse(BaseModel):
    user_id: UUID
    full_name: str | None = None
    role: UserRole
    unit_names: list[str] = Field(default_factory=list)
    workload_volume: int
    specimens_handled: int
    results_entered: int
    verifications_completed: int
    releases_completed: int
    qc_entries: int
    qc_overrides: int
    pending_load: int
    patients_touched: int
    specimen_issue_rate: float
    average_release_turnaround_minutes: float | None = None


class LabManagerRevenueByUnitResponse(BaseModel):
    unit_id: UUID | None = None
    unit_name: str
    revenue_minor: int


class LabManagerSalesRevenueRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    occurred_at: datetime
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    visit_id: UUID
    test_name: str
    unit_id: UUID | None = None
    unit_name: str | None = None
    quantity: int
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    cashier_name: str | None = None
    status: str


class LabManagerSalesRevenueSummaryResponse(BaseModel):
    total_revenue_minor: int
    paid_tests_count: int
    receipt_count: int
    blocked_unpaid_count: int
    currency: str
    revenue_by_unit: list[LabManagerRevenueByUnitResponse] = Field(default_factory=list)
    rows: list[LabManagerSalesRevenueRowResponse] = Field(default_factory=list)


class LabManagerReceiptRegisterRowResponse(BaseModel):
    receipt_id: UUID
    receipt_number: str
    occurred_at: datetime
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_mrn: str | None = None
    visit_id: UUID
    cashier_name: str | None = None
    amount_minor: int
    currency: str
    payment_method: BillingReasonCode
    status: str
    unit_names: list[str] = Field(default_factory=list)
    linked_test_items: list[str] = Field(default_factory=list)


class LabManagerReceiptRegisterResponse(BaseModel):
    currency: str
    rows: list[LabManagerReceiptRegisterRowResponse] = Field(default_factory=list)


class LabManagerDateMetricResponse(BaseModel):
    label: str
    count: int
    amount_minor: int | None = None


class LabManagerNamedCountMetricResponse(BaseModel):
    label: str
    count: int


class LabManagerReportsAnalyticsResponse(BaseModel):
    test_volume_by_day: list[LabManagerDateMetricResponse] = Field(default_factory=list)
    revenue_by_unit: list[LabManagerRevenueByUnitResponse] = Field(default_factory=list)
    common_tests_ordered: list[LabManagerNamedCountMetricResponse] = Field(default_factory=list)
    critical_result_frequency: list[LabManagerNamedCountMetricResponse] = Field(default_factory=list)
    specimen_rejection_trend: list[LabManagerDateMetricResponse] = Field(default_factory=list)
    verification_turnaround_minutes: float | None = None
    completion_turnaround_minutes: float | None = None
    qc_pass_fail_trend: list[LabManagerNamedCountMetricResponse] = Field(default_factory=list)
    staff_workload_trend: list[LabManagerNamedCountMetricResponse] = Field(default_factory=list)


class LabManagerBadgeStateResponse(BaseModel):
    section_key: GovernanceSectionKey
    count: int
    tone: str
    last_viewed_at: datetime | None = None


class LabManagerBadgeSnapshotResponse(BaseModel):
    generated_at: datetime
    sections: list[LabManagerBadgeStateResponse] = Field(default_factory=list)


class LabManagerDashboardResponse(BaseModel):
    date_range_start: date
    date_range_end: date
    units: list[LabManagerLabUnitContextResponse] = Field(default_factory=list)
    overview: LabManagerOverviewMetricResponse
    unit_operations: list[LabManagerUnitOperationResponse] = Field(default_factory=list)
    staff: list[LabManagerStaffSummaryResponse] = Field(default_factory=list)
    pending_verifications: list[LabManagerPendingVerificationResponse] = Field(default_factory=list)
    critical_alerts: list[LabManagerCriticalAlertResponse] = Field(default_factory=list)
    specimen_issues: list[LabManagerSpecimenIssueResponse] = Field(default_factory=list)
    quality_control: LabManagerQualityControlSummaryResponse
    activity_audit: list[LabManagerActivityAuditItemResponse] = Field(default_factory=list)
    staff_performance: list[LabManagerStaffPerformanceResponse] = Field(default_factory=list)
    sales_revenue: LabManagerSalesRevenueSummaryResponse
    receipt_register: LabManagerReceiptRegisterResponse
    reports_analytics: LabManagerReportsAnalyticsResponse
    configuration_requests: list[LabManagerConfigurationRequestResponse] = Field(default_factory=list)
