from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.clinic import Clinic
from app.models.event_log import EventLog
from app.models.lab_configuration_request import LabConfigurationRequest
from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_qc_result import LabQcResult
from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.lab_specimen_event import LabSpecimenEvent
from app.models.lab_staff_assignment_profile import LabStaffAssignmentProfile
from app.models.lab_user_unit_access import LabUserUnitAccess
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.patient_mrn import PatientMRN
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.models.identity_map_revocation import IdentityMapRevocation
from app.schemas.lab_manager import (
    LabManagerActivityAuditItemResponse,
    LabManagerConfigurationRequestCreate,
    LabManagerConfigurationRequestResponse,
    LabManagerCriticalAlertResponse,
    LabManagerDashboardResponse,
    LabManagerLabUnitContextResponse,
    LabManagerOverviewMetricResponse,
    LabManagerPendingVerificationResponse,
    LabManagerQualityControlRunResponse,
    LabManagerQualityControlSummaryResponse,
    LabManagerReceiptRegisterResponse,
    LabManagerReceiptRegisterRowResponse,
    LabManagerReportsAnalyticsResponse,
    LabManagerRevenueByUnitResponse,
    LabManagerSalesRevenueRowResponse,
    LabManagerSalesRevenueSummaryResponse,
    LabManagerStaffAssignmentUpdateRequest,
    LabManagerStaffPerformanceResponse,
    LabManagerSpecimenIssueResponse,
    LabManagerStaffSummaryResponse,
    LabManagerUnitOperationResponse,
)
from app.services.event_service import EventService
from app.services.lab_unit_access_service import LabUnitAccessService
from app.services.lab_workspace_service import (
    PENDING_VERIFICATION_RESULT_STATUSES,
    SPECIMEN_ISSUE_STATUSES,
    UNRESOLVED_ALERT_STATUSES,
    LabWorkspaceService,
)
from app.shared.enums import (
    BillingItemStatus,
    BillingReasonCode,
    LAB_OPERATION_ROLES,
    LAB_WORKFORCE_ROLES,
    LabConfigurationRequestStatus,
    LabConfigurationRequestType,
    LabCriticalAlertStatus,
    LabQcStatus,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenEventType,
    LabSpecimenStatus,
    LabStaffAssignmentStatus,
    LabVerificationPolicy,
    MRNStatus,
    ServiceLineKind,
    UserRole,
)


LAB_WORKFORCE_ROLE_VALUES = tuple(role.value for role in LAB_WORKFORCE_ROLES)
LAB_OPERATION_ROLE_VALUES = tuple(role.value for role in LAB_OPERATION_ROLES)
ACTIVE_ASSIGNMENT_STATUSES = {
    LabStaffAssignmentStatus.ACTIVE,
    LabStaffAssignmentStatus.TEMP_COVERAGE,
    LabStaffAssignmentStatus.RESTRICTED,
}


class LabManagerGovernanceService(LabWorkspaceService):
    DELAYED_RECEIPT_MINUTES = 60

    def __init__(self, db: Session):
        super().__init__(db)
        self.event_service = EventService(db)
        self.unit_access_service = LabUnitAccessService(db)

    def get_dashboard(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LabManagerDashboardResponse:
        resolved_start, resolved_end, start_dt, end_dt = self._resolve_date_range(
            start_date=start_date,
            end_date=end_date,
        )
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
        today_end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)

        units = self._active_leaf_lab_units(clinic_id=clinic_id)
        lab_staff = self._list_lab_staff(clinic_id=clinic_id)
        staff_ids = [user.id for user in lab_staff]
        profile_map = self._profile_map(clinic_id=clinic_id, user_ids=staff_ids)
        user_name_map = {user.id: user.full_name for user in lab_staff}

        today_sales_rows = self._fetch_sales_rows(
            clinic_id=clinic_id,
            start_dt=today_start,
            end_dt=today_end,
        )
        ranged_sales_rows = self._fetch_sales_rows(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        unit_operations = self._build_unit_operations(
            clinic_id=clinic_id,
            units=units,
            lab_staff=lab_staff,
            profile_map=profile_map,
            today_sales_rows=today_sales_rows,
        )
        pending_verifications = self._list_pending_verifications(
            clinic_id=clinic_id,
        )
        critical_alerts = self._list_critical_alerts(
            clinic_id=clinic_id,
        )
        specimen_issues = self._list_specimen_issues(
            clinic_id=clinic_id,
            end_dt=end_dt,
        )
        quality_control = self._build_quality_control_summary(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
            user_name_map=user_name_map,
        )
        configuration_requests = self._list_configuration_requests(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        activity_audit = self._build_activity_audit(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
            configuration_requests=configuration_requests,
            receipt_rows=ranged_sales_rows,
        )
        staff = self._build_staff_summaries(
            clinic_id=clinic_id,
            lab_staff=lab_staff,
            profile_map=profile_map,
            activity_audit=activity_audit,
        )
        staff_performance = self._build_staff_performance(
            clinic_id=clinic_id,
            lab_staff=lab_staff,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        sales_revenue = self._build_sales_revenue_summary(
            clinic_id=clinic_id,
            rows=ranged_sales_rows,
        )
        receipt_register = self._build_receipt_register(rows=ranged_sales_rows)
        reports_analytics = self._build_reports_analytics(
            clinic_id=clinic_id,
            start_dt=start_dt,
            end_dt=end_dt,
            sales_rows=ranged_sales_rows,
            staff_performance=staff_performance,
        )
        overview = self._build_overview(
            clinic_id=clinic_id,
            unit_operations=unit_operations,
            critical_alerts=critical_alerts,
            specimen_issues=specimen_issues,
            quality_control=quality_control,
            today_sales_rows=today_sales_rows,
            lab_staff=lab_staff,
            profile_map=profile_map,
        )

        return LabManagerDashboardResponse(
            date_range_start=resolved_start,
            date_range_end=resolved_end,
            units=[
                LabManagerLabUnitContextResponse(id=unit.id, name=unit.name)
                for unit in units
            ],
            overview=overview,
            unit_operations=unit_operations,
            staff=staff,
            pending_verifications=pending_verifications,
            critical_alerts=critical_alerts,
            specimen_issues=specimen_issues,
            quality_control=quality_control,
            activity_audit=activity_audit,
            staff_performance=staff_performance,
            sales_revenue=sales_revenue,
            receipt_register=receipt_register,
            reports_analytics=reports_analytics,
            configuration_requests=configuration_requests,
        )

    def update_staff_assignment(
        self,
        *,
        clinic_id: UUID,
        actor_id: UUID,
        staff_id: UUID,
        payload: LabManagerStaffAssignmentUpdateRequest,
    ) -> LabManagerStaffSummaryResponse:
        actor = self._get_manager_user(clinic_id=clinic_id, user_id=actor_id)
        staff_user = self._get_lab_staff_user(clinic_id=clinic_id, user_id=staff_id)
        now = datetime.now(timezone.utc)

        target_role = UserRole(staff_user.role)
        if target_role == UserRole.LAB_MANAGER and (
            payload.allowed_lab_unit_ids or payload.default_lab_unit_id is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Lab manager accounts do not use operational lab-unit assignments",
            )

        if target_role != UserRole.LAB_MANAGER:
            self.unit_access_service.sync_user_units(
                clinic_id=clinic_id,
                user=staff_user,
                role=target_role,
                allowed_unit_ids=list(payload.allowed_lab_unit_ids),
                default_unit_id=payload.default_lab_unit_id,
            )

        profile = self._get_or_create_assignment_profile(
            clinic_id=clinic_id,
            user_id=staff_user.id,
        )
        if payload.assignment_status is not None:
            profile.assignment_status = payload.assignment_status
        if "coverage_note" in payload.model_fields_set:
            profile.coverage_note = payload.coverage_note.strip() if payload.coverage_note else None
        profile.updated_by = actor.id
        profile.updated_at = now

        self.db.add(profile)
        self.event_service.build_event(
            event_type="LAB_STAFF_ASSIGNMENT_UPDATED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="lab",
            payload={
                "target_user_id": str(staff_user.id),
                "target_user_name": staff_user.full_name,
                "role": staff_user.role,
                "allowed_lab_unit_ids": [str(unit_id) for unit_id in payload.allowed_lab_unit_ids],
                "default_lab_unit_id": str(payload.default_lab_unit_id)
                if payload.default_lab_unit_id
                else None,
                "assignment_status": (
                    payload.assignment_status.value if payload.assignment_status else profile.assignment_status.value
                ),
                "coverage_note": profile.coverage_note,
                "timestamp": now.isoformat(),
            },
        )
        self.db.commit()
        activity_audit = self._build_activity_audit(
            clinic_id=clinic_id,
            start_dt=datetime.combine(now.date(), time.min, tzinfo=timezone.utc),
            end_dt=datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=timezone.utc),
            configuration_requests=[],
            receipt_rows=[],
        )
        return self._build_staff_summaries(
            clinic_id=clinic_id,
            lab_staff=[staff_user],
            profile_map={staff_user.id: profile},
            activity_audit=activity_audit,
        )[0]

    def create_configuration_request(
        self,
        *,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabManagerConfigurationRequestCreate,
    ) -> LabManagerConfigurationRequestResponse:
        actor = self._get_manager_user(clinic_id=clinic_id, user_id=actor_id)
        linked_staff_name = None
        linked_unit_name = None

        if payload.linked_staff_id is not None:
            staff_user = self._get_lab_staff_user(clinic_id=clinic_id, user_id=payload.linked_staff_id)
            linked_staff_name = staff_user.full_name

        if payload.linked_unit_id is not None:
            unit = (
                self.db.query(ServiceLine)
                .filter(
                    ServiceLine.id == payload.linked_unit_id,
                    ServiceLine.clinic_id == clinic_id,
                    ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
                    ServiceLine.is_active == True,
                )
                .first()
            )
            if unit is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Linked lab unit is invalid or inactive",
                )
            linked_unit_name = unit.name

        request = LabConfigurationRequest(
            clinic_id=clinic_id,
            requested_by=actor.id,
            request_type=payload.request_type,
            status=LabConfigurationRequestStatus.PENDING,
            department_name="Medical Laboratory",
            justification=payload.justification.strip(),
            linked_staff_id=payload.linked_staff_id,
            linked_unit_id=payload.linked_unit_id,
            linked_test_code=payload.linked_test_code.strip() if payload.linked_test_code else None,
            request_payload_json=payload.request_payload_json,
        )
        self.db.add(request)
        self.db.flush()

        self.event_service.build_event(
            event_type="LAB_CONFIGURATION_REQUEST_SUBMITTED",
            actor_id=actor.id,
            actor_role=actor.role,
            clinic_id=clinic_id,
            patient_id=None,
            emitter="lab",
            payload={
                "request_id": str(request.id),
                "request_type": request.request_type.value,
                "linked_staff_id": str(request.linked_staff_id) if request.linked_staff_id else None,
                "linked_unit_id": str(request.linked_unit_id) if request.linked_unit_id else None,
                "linked_test_code": request.linked_test_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.db.commit()
        self.db.refresh(request)

        return LabManagerConfigurationRequestResponse(
            id=request.id,
            request_type=request.request_type,
            status=request.status,
            department_name=request.department_name,
            justification=request.justification,
            requested_by=request.requested_by,
            requested_by_name=actor.full_name,
            linked_staff_id=request.linked_staff_id,
            linked_staff_name=linked_staff_name,
            linked_unit_id=request.linked_unit_id,
            linked_unit_name=linked_unit_name,
            linked_test_code=request.linked_test_code,
            request_payload_json=request.request_payload_json,
            created_at=request.created_at,
            updated_at=request.updated_at,
            resolved_at=request.resolved_at,
        )

    def _build_overview(
        self,
        *,
        clinic_id: UUID,
        unit_operations: list[LabManagerUnitOperationResponse],
        critical_alerts: list[LabManagerCriticalAlertResponse],
        specimen_issues: list[LabManagerSpecimenIssueResponse],
        quality_control: LabManagerQualityControlSummaryResponse,
        today_sales_rows: list[LabManagerSalesRevenueRowResponse],
        lab_staff: list[User],
        profile_map: dict[UUID, LabStaffAssignmentProfile],
    ) -> LabManagerOverviewMetricResponse:
        today = datetime.now(timezone.utc).date()
        total_tests_today = (
            self.db.query(LabRequest.id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                func.date(LabRequest.created_at) == today,
            )
            .count()
        )
        revenue_today_minor = sum(row.amount_minor for row in today_sales_rows)
        bottleneck_units = [
            item.unit_name
            for item in unit_operations
            if item.bottleneck_labels
        ]
        active_staff_on_duty = sum(
            1
            for user in lab_staff
            if user.role != UserRole.LAB_MANAGER.value
            and user.is_active
            and self._effective_assignment_status(profile_map.get(user.id))
            in ACTIVE_ASSIGNMENT_STATUSES
        )
        return LabManagerOverviewMetricResponse(
            total_tests_today=total_tests_today,
            pending_verifications=sum(item.pending_verifications for item in unit_operations),
            critical_alerts_open=len(critical_alerts),
            rejected_specimens=sum(1 for item in specimen_issues if item.status == LabSpecimenStatus.REJECTED),
            qc_failures=quality_control.unresolved_failures,
            revenue_today_minor=revenue_today_minor,
            blocked_unpaid_requests=self._count_blocked_unpaid_requests(clinic_id=clinic_id),
            active_staff_on_duty=active_staff_on_duty,
            currency=self._resolve_currency(clinic_id=clinic_id),
            bottleneck_units=bottleneck_units[:4],
        )

    def _build_unit_operations(
        self,
        *,
        clinic_id: UUID,
        units: list[ServiceLine],
        lab_staff: list[User],
        profile_map: dict[UUID, LabStaffAssignmentProfile],
        today_sales_rows: list[LabManagerSalesRevenueRowResponse],
    ) -> list[LabManagerUnitOperationResponse]:
        if not units:
            return []

        unit_ids = [unit.id for unit in units]
        unit_name_map = {unit.id: unit.name for unit in units}

        staffed_user_ids = {
            user.id
            for user in lab_staff
            if user.role != UserRole.LAB_MANAGER.value
            and user.is_active
            and self._effective_assignment_status(profile_map.get(user.id))
            in ACTIVE_ASSIGNMENT_STATUSES
        }
        unit_staff_counts: dict[UUID, int] = defaultdict(int)
        if staffed_user_ids:
            access_rows = (
                self.db.query(LabUserUnitAccess.user_id, LabUserUnitAccess.service_line_id)
                .filter(
                    LabUserUnitAccess.user_id.in_(staffed_user_ids),
                    LabUserUnitAccess.service_line_id.in_(unit_ids),
                )
                .all()
            )
            for _, service_line_id in access_rows:
                unit_staff_counts[service_line_id] += 1

        request_rows = (
            self.db.query(
                LabRequest.target_unit_id,
                LabRequest.workflow_status,
                LabRequest.status,
                func.count(LabRequest.id),
            )
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.target_unit_id.in_(unit_ids),
            )
            .group_by(
                LabRequest.target_unit_id,
                LabRequest.workflow_status,
                LabRequest.status,
            )
            .all()
        )
        pending_by_unit: dict[UUID, int] = defaultdict(int)
        pending_results_by_unit: dict[UUID, int] = defaultdict(int)
        completed_today_by_unit = {
            row.target_unit_id: row.count
            for row in (
                self.db.query(
                    LabRequest.target_unit_id,
                    func.count(LabRequest.id).label("count"),
                )
                .filter(
                    LabRequest.clinic_id == clinic_id,
                    LabRequest.target_unit_id.in_(unit_ids),
                    LabRequest.status == LabRequestStatus.COMPLETED,
                    func.date(LabRequest.completed_at) == datetime.now(timezone.utc).date(),
                )
                .group_by(LabRequest.target_unit_id)
                .all()
            )
        }
        for unit_id, workflow_status, request_status, count in request_rows:
            if request_status == LabRequestStatus.PENDING:
                pending_by_unit[unit_id] += int(count or 0)
                if workflow_status in {
                    LabRequestWorkflowStatus.IN_ANALYSIS,
                    LabRequestWorkflowStatus.RESULT_ENTERED,
                }:
                    pending_results_by_unit[unit_id] += int(count or 0)

        specimen_rows = (
            self.db.query(
                LabSpecimen.target_unit_id,
                LabSpecimen.status,
                func.count(LabSpecimen.id),
            )
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimen.target_unit_id.in_(unit_ids),
            )
            .group_by(LabSpecimen.target_unit_id, LabSpecimen.status)
            .all()
        )
        specimen_counts: dict[UUID, dict[LabSpecimenStatus, int]] = defaultdict(lambda: defaultdict(int))
        for unit_id, specimen_status, count in specimen_rows:
            specimen_counts[unit_id][specimen_status] = int(count or 0)

        pending_verification_rows = (
            self.db.query(
                LabRequest.target_unit_id,
                func.count(LabResult.id),
            )
            .join(LabRequest, LabRequest.id == (LabResult.request_item_id))
            .filter(
                LabResult.clinic_id == clinic_id,
                LabRequest.target_unit_id.in_(unit_ids),
                LabResult.status.in_(PENDING_VERIFICATION_RESULT_STATUSES),
            )
            .group_by(LabRequest.target_unit_id)
            .all()
        )
        pending_verifications_by_unit = {
            unit_id: int(count or 0)
            for unit_id, count in pending_verification_rows
        }

        alert_rows = (
            self.db.query(
                LabCriticalAlert.unit_id,
                func.count(LabCriticalAlert.id),
            )
            .filter(
                LabCriticalAlert.unit_id.in_(unit_ids),
                LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
            )
            .group_by(LabCriticalAlert.unit_id)
            .all()
        )
        alerts_by_unit = {unit_id: int(count or 0) for unit_id, count in alert_rows}

        qc_fail_rows = (
            self.db.query(
                LabQcRun.unit_id,
                func.count(LabQcRun.id),
            )
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.unit_id.in_(unit_ids),
                LabQcRun.status == LabQcStatus.FAIL,
            )
            .group_by(LabQcRun.unit_id)
            .all()
        )
        qc_fails_by_unit = {unit_id: int(count or 0) for unit_id, count in qc_fail_rows}

        revenue_by_unit: dict[UUID, int] = defaultdict(int)
        for row in today_sales_rows:
            if row.unit_id is not None:
                revenue_by_unit[row.unit_id] += row.amount_minor

        operations: list[LabManagerUnitOperationResponse] = []
        for unit in units:
            pending_specimens = specimen_counts[unit.id].get(LabSpecimenStatus.PENDING_COLLECTION, 0) + specimen_counts[unit.id].get(LabSpecimenStatus.COLLECTED, 0)
            rejected_specimens = specimen_counts[unit.id].get(LabSpecimenStatus.REJECTED, 0)
            critical_alerts = alerts_by_unit.get(unit.id, 0)
            qc_failures = qc_fails_by_unit.get(unit.id, 0)
            pending_verifications = pending_verifications_by_unit.get(unit.id, 0)
            pending_results = pending_results_by_unit.get(unit.id, 0)
            labels: list[str] = []
            if pending_verifications:
                labels.append("Verification queue")
            if pending_specimens:
                labels.append("Specimen delay")
            if critical_alerts:
                labels.append("Critical alerts")
            if qc_failures:
                labels.append("QC failure")
            if pending_results > 8:
                labels.append("Result backlog")

            operations.append(
                LabManagerUnitOperationResponse(
                    unit_id=unit.id,
                    unit_name=unit_name_map[unit.id],
                    queue_volume=pending_by_unit.get(unit.id, 0),
                    staff_on_duty=unit_staff_counts.get(unit.id, 0),
                    pending_specimens=pending_specimens,
                    pending_results=pending_results,
                    pending_verifications=pending_verifications,
                    rejected_specimens=rejected_specimens,
                    critical_alerts=critical_alerts,
                    qc_failures=qc_failures,
                    completed_today=completed_today_by_unit.get(unit.id, 0),
                    revenue_today_minor=revenue_by_unit.get(unit.id, 0),
                    bottleneck_labels=labels,
                )
            )
        return operations

    def _list_pending_verifications(
        self,
        *,
        clinic_id: UUID,
    ) -> list[LabManagerPendingVerificationResponse]:
        results = (
            self.db.query(LabResult)
            .join(LabRequest, LabRequest.id == LabResult.request_item_id)
            .filter(
                LabResult.clinic_id == clinic_id,
                LabResult.status.in_(PENDING_VERIFICATION_RESULT_STATUSES),
                LabRequest.target_unit_id.isnot(None),
            )
            .order_by(LabResult.entered_at.asc())
            .limit(80)
            .all()
        )
        if not results:
            return []

        request_ids = {result.request_item_id or result.lab_request_id for result in results}
        requests = (
            self.db.query(LabRequest)
            .filter(LabRequest.id.in_(request_ids))
            .all()
        )
        request_map = {request.id: request for request in requests}
        visit_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for request in requests},
        )
        unit_names = self._unit_name_map(
            {request.target_unit_id for request in requests if request.target_unit_id}
        )
        config_rows = (
            self.db.query(LabRequest.id, LabRequest.lab_test_config_id)
            .filter(LabRequest.id.in_(request_ids))
            .all()
        )
        config_id_map = {request_id: config_id for request_id, config_id in config_rows}
        value_flag_rows = (
            self.db.query(
                LabResultValue.result_id,
                LabResultValue.abnormal_flag,
                LabResultValue.critical_flag,
            )
            .join(LabResult, LabResult.id == LabResultValue.result_id)
            .filter(LabResultValue.result_id.in_({result.id for result in results}))
            .all()
        )
        flags_by_result: dict[UUID, dict[str, bool]] = defaultdict(lambda: {"abnormal": False, "critical": False})
        for result_id, abnormal_flag, critical_flag in value_flag_rows:
            if abnormal_flag:
                flags_by_result[result_id]["abnormal"] = True
            if critical_flag:
                flags_by_result[result_id]["critical"] = True

        config_models = (
            self.db.query(LabRequest.id, LabRequest.lab_test_config_id)
            .filter(LabRequest.id.in_(request_ids))
            .all()
        )
        config_ids = {config_id for _, config_id in config_models if config_id}
        config_map = {}
        if config_ids:
            from app.models.lab_test_config import LabTestConfig

            config_map = {
                config.id: config
                for config in self.db.query(LabTestConfig).filter(LabTestConfig.id.in_(config_ids)).all()
            }

        entered_by_ids = {result.entered_by for result in results if result.entered_by}
        entered_by_map = {
            user.id: user.full_name
            for user in self.db.query(User).filter(User.id.in_(entered_by_ids)).all()
        } if entered_by_ids else {}

        accession_rows = (
            self.db.query(LabSpecimen.request_item_id, LabSpecimen.accession_number)
            .filter(LabSpecimen.request_item_id.in_(request_ids))
            .order_by(LabSpecimen.created_at.asc())
            .all()
        )
        accession_map: dict[UUID, str] = {}
        for request_item_id, accession_number in accession_rows:
            accession_map.setdefault(request_item_id, accession_number)

        now = datetime.now(timezone.utc)
        response: list[LabManagerPendingVerificationResponse] = []
        for result in results:
            request_id = result.request_item_id or result.lab_request_id
            request = request_map.get(request_id)
            if request is None:
                continue
            flags = flags_by_result[result.id]
            config = config_map.get(config_id_map.get(request_id))
            entered_at = self._ensure_utc(result.entered_at or result.created_at)
            response.append(
                LabManagerPendingVerificationResponse(
                    request_id=request.id,
                    result_id=result.id,
                    visit_id=request.visit_id,
                    patient_id=visit_context.get(request.visit_id, {}).get("patient_id"),
                    patient_name=visit_context.get(request.visit_id, {}).get("patient_name"),
                    patient_mrn=visit_context.get(request.visit_id, {}).get("patient_mrn"),
                    accession_number=accession_map.get(request.id),
                    test_name=request.test_name,
                    unit_id=request.target_unit_id,
                    unit_name=unit_names.get(request.target_unit_id),
                    result_status=result.status,
                    abnormal=flags["abnormal"],
                    critical=flags["critical"],
                    waiting_minutes=max(int((now - entered_at).total_seconds() // 60), 0),
                    entered_by=result.entered_by,
                    entered_by_name=entered_by_map.get(result.entered_by),
                    verification_policy=config.verification_policy if config else LabVerificationPolicy.OPTIONAL,
                    created_at=result.created_at,
                )
            )
        return response

    def _list_critical_alerts(
        self,
        *,
        clinic_id: UUID,
    ) -> list[LabManagerCriticalAlertResponse]:
        alerts = (
            self.db.query(LabCriticalAlert)
            .filter(
                LabCriticalAlert.unit_id.isnot(None),
                LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
            )
            .order_by(LabCriticalAlert.created_at.desc())
            .limit(80)
            .all()
        )
        if not alerts:
            return []
        request_ids = {alert.request_item_id for alert in alerts if alert.request_item_id}
        requests = (
            self.db.query(LabRequest)
            .filter(LabRequest.id.in_(request_ids))
            .all()
            if request_ids
            else []
        )
        request_map = {request.id: request for request in requests}
        visit_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for request in requests},
        )
        unit_names = self._unit_name_map(
            {alert.unit_id for alert in alerts if alert.unit_id}
        )
        return [
            LabManagerCriticalAlertResponse(
                alert_id=alert.id,
                result_id=alert.result_id,
                request_item_id=alert.request_item_id,
                visit_id=alert.visit_id,
                patient_id=alert.patient_id,
                patient_name=visit_context.get(alert.visit_id, {}).get("patient_name"),
                patient_mrn=visit_context.get(alert.visit_id, {}).get("patient_mrn"),
                unit_id=alert.unit_id,
                unit_name=unit_names.get(alert.unit_id),
                test_name=request_map.get(alert.request_item_id).test_name
                if alert.request_item_id in request_map
                else None,
                severity=alert.severity,
                status=alert.status,
                message=alert.message,
                created_at=alert.created_at,
                acknowledged_at=alert.acknowledged_at,
                escalated_at=alert.escalated_at,
                resolved_at=alert.resolved_at,
            )
            for alert in alerts
        ]

    def _list_specimen_issues(
        self,
        *,
        clinic_id: UUID,
        end_dt: datetime,
    ) -> list[LabManagerSpecimenIssueResponse]:
        delayed_threshold = end_dt - timedelta(minutes=self.DELAYED_RECEIPT_MINUTES)
        specimens = (
            self.db.query(LabSpecimen)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                (
                    LabSpecimen.status.in_(SPECIMEN_ISSUE_STATUSES)
                    | and_(
                        LabSpecimen.status == LabSpecimenStatus.COLLECTED,
                        LabSpecimen.received_at.is_(None),
                        LabSpecimen.collected_at <= delayed_threshold,
                    )
                ),
            )
            .order_by(LabSpecimen.updated_at.desc())
            .limit(80)
            .all()
        )
        if not specimens:
            return []

        request_ids = {specimen.request_item_id for specimen in specimens}
        requests = self.db.query(LabRequest).filter(LabRequest.id.in_(request_ids)).all()
        request_map = {request.id: request for request in requests}
        visit_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for request in requests},
        )
        unit_names = self._unit_name_map({specimen.target_unit_id for specimen in specimens})
        responsible_ids = {
            specimen.rejected_by or specimen.received_by or specimen.collected_by
            for specimen in specimens
            if specimen.rejected_by or specimen.received_by or specimen.collected_by
        }
        responsible_names = {
            user.id: user.full_name
            for user in self.db.query(User).filter(User.id.in_(responsible_ids)).all()
        } if responsible_ids else {}

        response: list[LabManagerSpecimenIssueResponse] = []
        for specimen in specimens:
            request = request_map.get(specimen.request_item_id)
            if request is None:
                continue
            responsible_id = specimen.rejected_by or specimen.received_by or specimen.collected_by
            if specimen.status == LabSpecimenStatus.REJECTED:
                issue_type = "Rejected specimen"
            elif specimen.status == LabSpecimenStatus.LOST:
                issue_type = "Lost specimen"
            else:
                issue_type = "Delayed receipt"
            response.append(
                LabManagerSpecimenIssueResponse(
                    specimen_id=specimen.id,
                    accession_number=specimen.accession_number,
                    request_item_id=request.id,
                    visit_id=request.visit_id,
                    patient_id=visit_context.get(request.visit_id, {}).get("patient_id"),
                    patient_name=visit_context.get(request.visit_id, {}).get("patient_name"),
                    patient_mrn=visit_context.get(request.visit_id, {}).get("patient_mrn"),
                    unit_id=specimen.target_unit_id,
                    unit_name=unit_names.get(specimen.target_unit_id),
                    test_name=request.test_name,
                    status=specimen.status,
                    issue_type=issue_type,
                    rejection_reason_code=specimen.rejection_reason_code.value if specimen.rejection_reason_code else None,
                    rejection_reason_text=specimen.rejection_reason_text,
                    responsible_staff_id=responsible_id,
                    responsible_staff_name=responsible_names.get(responsible_id),
                    updated_at=specimen.updated_at,
                )
            )
        return response

    def _build_quality_control_summary(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
        user_name_map: dict[UUID, str | None],
    ) -> LabManagerQualityControlSummaryResponse:
        runs = (
            self.db.query(LabQcRun)
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.performed_at >= start_dt,
                LabQcRun.performed_at < end_dt,
            )
            .order_by(LabQcRun.performed_at.desc())
            .limit(80)
            .all()
        )
        if not runs:
            return LabManagerQualityControlSummaryResponse(
                total_runs=0,
                fail_runs=0,
                warning_runs=0,
                override_events=0,
                unresolved_failures=0,
                runs=[],
            )

        run_ids = [run.id for run in runs]
        result_rows = (
            self.db.query(LabQcResult.qc_run_id, LabQcResult.status, func.count(LabQcResult.id))
            .filter(LabQcResult.qc_run_id.in_(run_ids))
            .group_by(LabQcResult.qc_run_id, LabQcResult.status)
            .all()
        )
        fail_counts: dict[UUID, int] = defaultdict(int)
        warning_counts: dict[UUID, int] = defaultdict(int)
        for qc_run_id, qc_status, count in result_rows:
            if qc_status == LabQcStatus.FAIL:
                fail_counts[qc_run_id] = int(count or 0)
            elif qc_status == LabQcStatus.WARNING:
                warning_counts[qc_run_id] = int(count or 0)

        unit_names = self._unit_name_map({run.unit_id for run in runs if run.unit_id})

        override_events = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.event_type == "LAB_QC_OVERRIDE",
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
            )
            .all()
        )
        override_counts: dict[UUID, int] = defaultdict(int)
        for event in override_events:
            payload = self._parse_json(event.payload)
            metadata = payload.get("metadata_json") if isinstance(payload, dict) else {}
            for raw_run_id in (metadata or {}).get("qc_run_ids", []):
                parsed = self._parse_uuid(raw_run_id)
                if parsed is not None:
                    override_counts[parsed] += 1

        run_rows = [
            LabManagerQualityControlRunResponse(
                qc_run_id=run.id,
                unit_id=run.unit_id,
                unit_name=unit_names.get(run.unit_id),
                machine_id=run.machine_id,
                qc_level=run.qc_level,
                status=run.status,
                performed_by=run.performed_by,
                performed_by_name=user_name_map.get(run.performed_by),
                performed_at=run.performed_at,
                fail_count=fail_counts.get(run.id, 0),
                warning_count=warning_counts.get(run.id, 0),
                override_count=override_counts.get(run.id, 0),
                unresolved=run.status == LabQcStatus.FAIL,
                notes=run.notes,
            )
            for run in runs
        ]
        return LabManagerQualityControlSummaryResponse(
            total_runs=len(run_rows),
            fail_runs=sum(1 for run in runs if run.status == LabQcStatus.FAIL),
            warning_runs=sum(1 for run in runs if run.status == LabQcStatus.WARNING),
            override_events=len(override_events),
            unresolved_failures=sum(1 for run in runs if run.status == LabQcStatus.FAIL),
            runs=run_rows,
        )

    def _build_activity_audit(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
        configuration_requests: list[LabManagerConfigurationRequestResponse],
        receipt_rows: list[LabManagerSalesRevenueRowResponse],
    ) -> list[LabManagerActivityAuditItemResponse]:
        items: list[LabManagerActivityAuditItemResponse] = []

        event_rows = (
            self.db.query(EventLog, User.full_name.label("actor_name"))
            .outerjoin(User, User.id == EventLog.actor_id)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
                EventLog.event_type.in_(
                    [
                        "LAB_RESULT_ENTERED",
                        "LAB_RESULT_SUBMITTED",
                        "LAB_RESULT_VERIFIED",
                        "LAB_RESULT_RELEASED",
                        "LAB_RESULT_AMENDED",
                        "LAB_QC_OVERRIDE",
                        "LAB_STAFF_ASSIGNMENT_UPDATED",
                    ]
                ),
            )
            .order_by(EventLog.created_at.desc())
            .limit(120)
            .all()
        )
        request_ids: set[UUID] = set()
        specimen_ids: set[UUID] = set()
        patient_ids: set[UUID] = set()
        unit_ids: set[UUID] = set()
        prepared_events: list[tuple[EventLog, str | None, dict]] = []
        for event, actor_name in event_rows:
            payload = self._parse_json(event.payload)
            prepared_events.append((event, actor_name, payload))
            request_id = self._parse_uuid(payload.get("request_item_id") or payload.get("lab_request_id"))
            specimen_id = self._parse_uuid(payload.get("specimen_id"))
            unit_id = self._parse_uuid(payload.get("unit_id"))
            if request_id:
                request_ids.add(request_id)
            if specimen_id:
                specimen_ids.add(specimen_id)
            if unit_id:
                unit_ids.add(unit_id)
            if event.patient_id:
                patient_ids.add(event.patient_id)

        request_map = {
            request.id: request
            for request in self.db.query(LabRequest).filter(LabRequest.id.in_(request_ids)).all()
        } if request_ids else {}
        specimen_map = {
            specimen.id: specimen
            for specimen in self.db.query(LabSpecimen).filter(LabSpecimen.id.in_(specimen_ids)).all()
        } if specimen_ids else {}
        unit_name_map = self._unit_name_map(unit_ids | {req.target_unit_id for req in request_map.values() if req.target_unit_id})
        patient_context = self._build_patient_context_by_ids(clinic_id=clinic_id, patient_ids=patient_ids)

        for event, actor_name, payload in prepared_events:
            request_id = self._parse_uuid(payload.get("request_item_id") or payload.get("lab_request_id"))
            specimen_id = self._parse_uuid(payload.get("specimen_id"))
            unit_id = self._parse_uuid(payload.get("unit_id"))
            request = request_map.get(request_id) if request_id else None
            specimen = specimen_map.get(specimen_id) if specimen_id else None
            patient = patient_context.get(event.patient_id, {})
            summary, detail, severity = self._summarize_event_audit_item(
                event_type=event.event_type,
                request=request,
                specimen=specimen,
                payload=payload,
            )
            items.append(
                LabManagerActivityAuditItemResponse(
                    id=str(event.id),
                    source_type="EVENT_LOG",
                    action_type=event.event_type,
                    occurred_at=event.created_at,
                    actor_id=event.actor_id,
                    actor_name=actor_name,
                    actor_role=event.actor_role,
                    unit_id=unit_id or (request.target_unit_id if request else None),
                    unit_name=unit_name_map.get(unit_id or (request.target_unit_id if request else None)),
                    patient_id=event.patient_id,
                    patient_name=patient.get("patient_name"),
                    patient_mrn=patient.get("patient_mrn"),
                    visit_id=request.visit_id if request else None,
                    request_item_id=request.id if request else None,
                    result_id=self._parse_uuid(payload.get("result_id") or payload.get("lab_result_id")),
                    specimen_id=specimen.id if specimen else None,
                    accession_number=specimen.accession_number if specimen else None,
                    summary=summary,
                    detail=detail,
                    severity=severity,
                    metadata_json=payload.get("metadata_json") if isinstance(payload, dict) else None,
                )
            )

        specimen_event_rows = (
            self.db.query(
                LabSpecimenEvent,
                LabSpecimen,
                LabRequest,
                User.full_name.label("actor_name"),
            )
            .join(LabSpecimen, LabSpecimen.id == LabSpecimenEvent.specimen_id)
            .join(LabRequest, LabRequest.id == LabSpecimen.request_item_id)
            .outerjoin(User, User.id == LabSpecimenEvent.performed_by)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimenEvent.performed_at >= start_dt,
                LabSpecimenEvent.performed_at < end_dt,
                LabSpecimenEvent.event_type != LabSpecimenEventType.REJECTED,
            )
            .order_by(LabSpecimenEvent.performed_at.desc())
            .limit(120)
            .all()
        )
        patient_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for _, _, request, _ in specimen_event_rows},
        )
        for event, specimen, request, actor_name in specimen_event_rows:
            summary, detail, severity = self._summarize_specimen_event(event_type=event.event_type, request=request)
            visit_patient = patient_context.get(request.visit_id, {})
            items.append(
                LabManagerActivityAuditItemResponse(
                    id=f"specimen-event:{event.id}",
                    source_type="SPECIMEN_EVENT",
                    action_type=event.event_type.value,
                    occurred_at=event.performed_at,
                    actor_id=event.performed_by,
                    actor_name=actor_name,
                    actor_role=None,
                    unit_id=specimen.target_unit_id,
                    unit_name=unit_name_map.get(specimen.target_unit_id),
                    patient_id=visit_patient.get("patient_id"),
                    patient_name=visit_patient.get("patient_name"),
                    patient_mrn=visit_patient.get("patient_mrn"),
                    visit_id=request.visit_id,
                    request_item_id=request.id,
                    specimen_id=specimen.id,
                    accession_number=specimen.accession_number,
                    summary=summary,
                    detail=detail,
                    severity=severity,
                    metadata_json=event.metadata_json,
                )
            )

        receipt_grouped: dict[UUID, list[LabManagerSalesRevenueRowResponse]] = defaultdict(list)
        for row in receipt_rows:
            receipt_grouped[row.receipt_id].append(row)
        for receipt_id, rows in receipt_grouped.items():
            first = rows[0]
            items.append(
                LabManagerActivityAuditItemResponse(
                    id=f"receipt:{receipt_id}",
                    source_type="RECEIPT",
                    action_type="LAB_PAYMENT_CAPTURED",
                    occurred_at=first.occurred_at,
                    actor_id=None,
                    actor_name=first.cashier_name,
                    actor_role=UserRole.CASHIER.value,
                    unit_id=first.unit_id,
                    unit_name=first.unit_name,
                    patient_id=first.patient_id,
                    patient_name=first.patient_name,
                    patient_mrn=first.patient_mrn,
                    visit_id=first.visit_id,
                    receipt_number=first.receipt_number,
                    summary=f"Lab payment captured for {len(rows)} billed test item(s)",
                    detail=", ".join(sorted({row.test_name for row in rows})),
                    severity="info",
                    metadata_json={
                        "cashier_name": first.cashier_name,
                        "payment_method": first.payment_method.value
                        if isinstance(first.payment_method, BillingReasonCode)
                        else first.payment_method,
                    },
                )
            )

        for request in configuration_requests:
            items.append(
                LabManagerActivityAuditItemResponse(
                    id=f"config-request:{request.id}",
                    source_type="CONFIGURATION_REQUEST",
                    action_type=request.request_type.value,
                    occurred_at=request.created_at,
                    actor_id=request.requested_by,
                    actor_name=request.requested_by_name,
                    actor_role=UserRole.LAB_MANAGER.value,
                    unit_id=request.linked_unit_id,
                    unit_name=request.linked_unit_name,
                    summary=f"{self._format_request_type(request.request_type)} request submitted",
                    detail=request.justification,
                    severity="warning" if request.request_type == LabConfigurationRequestType.NEW_STAFF_ACCOUNT else "info",
                    metadata_json=request.request_payload_json,
                )
            )

        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[:120]

    def _build_staff_summaries(
        self,
        *,
        clinic_id: UUID,
        lab_staff: list[User],
        profile_map: dict[UUID, LabStaffAssignmentProfile],
        activity_audit: list[LabManagerActivityAuditItemResponse],
    ) -> list[LabManagerStaffSummaryResponse]:
        if not lab_staff:
            return []
        user_ids = [user.id for user in lab_staff]
        unit_rows = (
            self.db.query(
                LabUserUnitAccess.user_id,
                ServiceLine.id,
                ServiceLine.name,
            )
            .join(ServiceLine, ServiceLine.id == LabUserUnitAccess.service_line_id)
            .filter(
                LabUserUnitAccess.user_id.in_(user_ids),
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )
        units_by_user: dict[UUID, list[LabManagerLabUnitContextResponse]] = defaultdict(list)
        for user_id, unit_id, unit_name in unit_rows:
            units_by_user[user_id].append(
                LabManagerLabUnitContextResponse(id=unit_id, name=unit_name)
            )

        default_unit_ids = {user.default_lab_unit_id for user in lab_staff if user.default_lab_unit_id}
        default_name_map = self._unit_name_map(default_unit_ids)
        updater_ids = {
            profile.updated_by
            for profile in profile_map.values()
            if profile.updated_by
        }
        updater_name_map = {
            user.id: user.full_name
            for user in self.db.query(User).filter(User.id.in_(updater_ids)).all()
        } if updater_ids else {}

        recent_activity_map: dict[UUID, LabManagerActivityAuditItemResponse] = {}
        for item in activity_audit:
            if item.actor_id is not None and item.actor_id not in recent_activity_map:
                recent_activity_map[item.actor_id] = item

        return [
            LabManagerStaffSummaryResponse(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=UserRole(user.role),
                is_active=user.is_active,
                assignment_status=self._effective_assignment_status(profile_map.get(user.id)),
                coverage_note=profile_map.get(user.id).coverage_note if profile_map.get(user.id) else None,
                allowed_units=units_by_user.get(user.id, []),
                default_unit_id=user.default_lab_unit_id,
                default_unit_name=default_name_map.get(user.default_lab_unit_id),
                recent_activity_summary=recent_activity_map.get(user.id).summary if recent_activity_map.get(user.id) else None,
                recent_activity_at=recent_activity_map.get(user.id).occurred_at if recent_activity_map.get(user.id) else None,
                last_updated_at=profile_map.get(user.id).updated_at if profile_map.get(user.id) else None,
                last_updated_by_id=profile_map.get(user.id).updated_by if profile_map.get(user.id) else None,
                last_updated_by_name=updater_name_map.get(profile_map.get(user.id).updated_by) if profile_map.get(user.id) and profile_map.get(user.id).updated_by else None,
            )
            for user in lab_staff
        ]

    def _build_staff_performance(
        self,
        *,
        clinic_id: UUID,
        lab_staff: list[User],
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[LabManagerStaffPerformanceResponse]:
        if not lab_staff:
            return []
        user_ids = [user.id for user in lab_staff if user.role != UserRole.LAB_MANAGER.value]
        if not user_ids:
            return []

        unit_rows = (
            self.db.query(
                LabUserUnitAccess.user_id,
                ServiceLine.name,
            )
            .join(ServiceLine, ServiceLine.id == LabUserUnitAccess.service_line_id)
            .filter(LabUserUnitAccess.user_id.in_(user_ids))
            .order_by(ServiceLine.name.asc())
            .all()
        )
        unit_names_by_user: dict[UUID, list[str]] = defaultdict(list)
        for user_id, unit_name in unit_rows:
            unit_names_by_user[user_id].append(unit_name)

        entered_counts = defaultdict(int)
        pending_load_counts = defaultdict(int)
        turnaround_sums = defaultdict(float)
        turnaround_counts = defaultdict(int)
        result_rows = (
            self.db.query(LabResult)
            .filter(LabResult.clinic_id == clinic_id)
            .all()
        )
        for result in result_rows:
            result_created_at = self._ensure_utc(result.created_at)
            result_entered_at = self._ensure_utc(result.entered_at)
            result_verified_at = self._ensure_utc(result.verified_at) if result.verified_at else None
            result_released_at = self._ensure_utc(result.released_at) if result.released_at else None
            if result.entered_by in user_ids and start_dt <= result_created_at < end_dt:
                entered_counts[result.entered_by] += 1
            if result.entered_by in user_ids and result.status in {
                LabResultLifecycleStatus.DRAFT,
                LabResultLifecycleStatus.SUBMITTED,
                LabResultLifecycleStatus.VERIFIED,
            }:
                pending_load_counts[result.entered_by] += 1
            if (
                result.entered_by in user_ids
                and result_released_at is not None
                and start_dt <= result_released_at < end_dt
            ):
                turnaround_sums[result.entered_by] += max(
                    (result_released_at - result_entered_at).total_seconds() / 60.0,
                    0.0,
                )
                turnaround_counts[result.entered_by] += 1

        verification_counts = defaultdict(int)
        release_counts = defaultdict(int)
        for result in result_rows:
            result_verified_at = self._ensure_utc(result.verified_at) if result.verified_at else None
            result_released_at = self._ensure_utc(result.released_at) if result.released_at else None
            if result.verified_by in user_ids and result_verified_at and start_dt <= result_verified_at < end_dt:
                verification_counts[result.verified_by] += 1
            if result.released_by in user_ids and result_released_at and start_dt <= result_released_at < end_dt:
                release_counts[result.released_by] += 1

        specimen_handled = defaultdict(int)
        specimen_rejections = defaultdict(int)
        specimen_rows = (
            self.db.query(LabSpecimenEvent)
            .filter(
                LabSpecimenEvent.performed_by.in_(user_ids),
                LabSpecimenEvent.performed_at >= start_dt,
                LabSpecimenEvent.performed_at < end_dt,
            )
            .all()
        )
        for row in specimen_rows:
            if row.event_type in {
                LabSpecimenEventType.COLLECTED,
                LabSpecimenEventType.RECEIVED,
                LabSpecimenEventType.ANALYSIS_STARTED,
                LabSpecimenEventType.ANALYSIS_COMPLETED,
                LabSpecimenEventType.REJECTED,
            }:
                specimen_handled[row.performed_by] += 1
            if row.event_type == LabSpecimenEventType.REJECTED:
                specimen_rejections[row.performed_by] += 1

        qc_entries = defaultdict(int)
        qc_rows = (
            self.db.query(LabQcRun)
            .filter(
                LabQcRun.performed_by.in_(user_ids),
                LabQcRun.performed_at >= start_dt,
                LabQcRun.performed_at < end_dt,
            )
            .all()
        )
        for run in qc_rows:
            qc_entries[run.performed_by] += 1

        qc_overrides = defaultdict(int)
        patient_sets: dict[UUID, set[UUID]] = defaultdict(set)
        event_rows = (
            self.db.query(EventLog)
            .filter(
                EventLog.clinic_id == clinic_id,
                EventLog.actor_id.in_(user_ids),
                EventLog.created_at >= start_dt,
                EventLog.created_at < end_dt,
                EventLog.event_type.like("LAB_%"),
            )
            .all()
        )
        for event in event_rows:
            if event.event_type == "LAB_QC_OVERRIDE":
                qc_overrides[event.actor_id] += 1
            if event.patient_id:
                patient_sets[event.actor_id].add(event.patient_id)

        response: list[LabManagerStaffPerformanceResponse] = []
        for user in lab_staff:
            if user.id not in user_ids:
                continue
            handled = specimen_handled[user.id]
            issue_rate = round((specimen_rejections[user.id] / handled), 2) if handled else 0.0
            workload = (
                entered_counts[user.id]
                + verification_counts[user.id]
                + release_counts[user.id]
                + handled
                + qc_entries[user.id]
            )
            avg_turnaround = (
                round(turnaround_sums[user.id] / turnaround_counts[user.id], 1)
                if turnaround_counts[user.id]
                else None
            )
            response.append(
                LabManagerStaffPerformanceResponse(
                    user_id=user.id,
                    full_name=user.full_name,
                    role=UserRole(user.role),
                    unit_names=unit_names_by_user.get(user.id, []),
                    workload_volume=workload,
                    specimens_handled=handled,
                    results_entered=entered_counts[user.id],
                    verifications_completed=verification_counts[user.id],
                    releases_completed=release_counts[user.id],
                    qc_entries=qc_entries[user.id],
                    qc_overrides=qc_overrides[user.id],
                    pending_load=pending_load_counts[user.id],
                    patients_touched=len(patient_sets[user.id]),
                    specimen_issue_rate=issue_rate,
                    average_release_turnaround_minutes=avg_turnaround,
                )
            )

        response.sort(
            key=lambda item: (
                item.workload_volume,
                item.releases_completed,
                item.verifications_completed,
            ),
            reverse=True,
        )
        return response

    def _build_sales_revenue_summary(
        self,
        *,
        clinic_id: UUID,
        rows: list[LabManagerSalesRevenueRowResponse],
    ) -> LabManagerSalesRevenueSummaryResponse:
        revenue_by_unit: dict[tuple[UUID | None, str], int] = defaultdict(int)
        receipt_ids: set[UUID] = set()
        for row in rows:
            revenue_by_unit[(row.unit_id, row.unit_name or "Unassigned")] += row.amount_minor
            receipt_ids.add(row.receipt_id)
        return LabManagerSalesRevenueSummaryResponse(
            total_revenue_minor=sum(row.amount_minor for row in rows),
            paid_tests_count=len(rows),
            receipt_count=len(receipt_ids),
            blocked_unpaid_count=self._count_blocked_unpaid_requests(clinic_id=clinic_id),
            currency=rows[0].currency if rows else self._resolve_currency(clinic_id=clinic_id),
            revenue_by_unit=[
                LabManagerRevenueByUnitResponse(
                    unit_id=unit_id,
                    unit_name=unit_name,
                    revenue_minor=amount,
                )
                for (unit_id, unit_name), amount in sorted(
                    revenue_by_unit.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
            rows=rows,
        )

    def _build_receipt_register(
        self,
        *,
        rows: list[LabManagerSalesRevenueRowResponse],
    ) -> LabManagerReceiptRegisterResponse:
        grouped: dict[UUID, list[LabManagerSalesRevenueRowResponse]] = defaultdict(list)
        for row in rows:
            grouped[row.receipt_id].append(row)
        response_rows: list[LabManagerReceiptRegisterRowResponse] = []
        for receipt_id, receipt_rows in grouped.items():
            first = receipt_rows[0]
            response_rows.append(
                LabManagerReceiptRegisterRowResponse(
                    receipt_id=receipt_id,
                    receipt_number=first.receipt_number,
                    occurred_at=first.occurred_at,
                    patient_id=first.patient_id,
                    patient_name=first.patient_name,
                    patient_mrn=first.patient_mrn,
                    visit_id=first.visit_id,
                    cashier_name=first.cashier_name,
                    amount_minor=sum(row.amount_minor for row in receipt_rows),
                    currency=first.currency,
                    payment_method=first.payment_method,
                    status="PAID",
                    unit_names=sorted({row.unit_name or "Unassigned" for row in receipt_rows}),
                    linked_test_items=sorted({row.test_name for row in receipt_rows}),
                )
            )
        response_rows.sort(key=lambda row: row.occurred_at, reverse=True)
        return LabManagerReceiptRegisterResponse(
            currency=response_rows[0].currency if response_rows else "NGN",
            rows=response_rows,
        )

    def _build_reports_analytics(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
        sales_rows: list[LabManagerSalesRevenueRowResponse],
        staff_performance: list[LabManagerStaffPerformanceResponse],
    ) -> LabManagerReportsAnalyticsResponse:
        day_buckets: dict[str, int] = defaultdict(int)
        for request in (
            self.db.query(LabRequest)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.created_at >= start_dt,
                LabRequest.created_at < end_dt,
            )
            .all()
        ):
            day_buckets[request.created_at.date().isoformat()] += 1

        revenue_by_unit: dict[tuple[UUID | None, str], int] = defaultdict(int)
        for row in sales_rows:
            revenue_by_unit[(row.unit_id, row.unit_name or "Unassigned")] += row.amount_minor

        common_test_rows = (
            self.db.query(LabRequest.test_name, func.count(LabRequest.id))
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.created_at >= start_dt,
                LabRequest.created_at < end_dt,
            )
            .group_by(LabRequest.test_name)
            .order_by(func.count(LabRequest.id).desc(), LabRequest.test_name.asc())
            .limit(10)
            .all()
        )

        critical_alert_rows = (
            self.db.query(ServiceLine.name, func.count(LabCriticalAlert.id))
            .join(ServiceLine, ServiceLine.id == LabCriticalAlert.unit_id)
            .filter(
                LabCriticalAlert.created_at >= start_dt,
                LabCriticalAlert.created_at < end_dt,
                LabCriticalAlert.alert_type.isnot(None),
            )
            .group_by(ServiceLine.name)
            .order_by(func.count(LabCriticalAlert.id).desc())
            .all()
        )

        rejection_rows = (
            self.db.query(func.date(LabSpecimen.updated_at), func.count(LabSpecimen.id))
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimen.status == LabSpecimenStatus.REJECTED,
                LabSpecimen.updated_at >= start_dt,
                LabSpecimen.updated_at < end_dt,
            )
            .group_by(func.date(LabSpecimen.updated_at))
            .order_by(func.date(LabSpecimen.updated_at).asc())
            .all()
        )

        verification_turnaround_values = [
            max((result.verified_at - result.entered_at).total_seconds() / 60.0, 0.0)
            for result in self.db.query(LabResult)
            .filter(
                LabResult.clinic_id == clinic_id,
                LabResult.verified_at.isnot(None),
                LabResult.verified_at >= start_dt,
                LabResult.verified_at < end_dt,
            )
            .all()
            if result.verified_at is not None and result.entered_at is not None
        ]
        verification_turnaround = self._avg_minutes(
            sum(verification_turnaround_values) / len(verification_turnaround_values)
            if verification_turnaround_values
            else None
        )

        completion_turnaround_values = [
            max((request.completed_at - request.created_at).total_seconds() / 60.0, 0.0)
            for request in self.db.query(LabRequest)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.completed_at.isnot(None),
                LabRequest.completed_at >= start_dt,
                LabRequest.completed_at < end_dt,
            )
            .all()
            if request.completed_at is not None and request.created_at is not None
        ]
        completion_turnaround = self._avg_minutes(
            sum(completion_turnaround_values) / len(completion_turnaround_values)
            if completion_turnaround_values
            else None
        )

        qc_rows = (
            self.db.query(LabQcRun.status, func.count(LabQcRun.id))
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.performed_at >= start_dt,
                LabQcRun.performed_at < end_dt,
            )
            .group_by(LabQcRun.status)
            .all()
        )

        return LabManagerReportsAnalyticsResponse(
            test_volume_by_day=[
                {"label": label, "count": count, "amount_minor": None}
                for label, count in sorted(day_buckets.items())
            ],
            revenue_by_unit=[
                LabManagerRevenueByUnitResponse(
                    unit_id=unit_id,
                    unit_name=unit_name,
                    revenue_minor=amount,
                )
                for (unit_id, unit_name), amount in sorted(
                    revenue_by_unit.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ],
            common_tests_ordered=[
                {"label": test_name, "count": int(count or 0)}
                for test_name, count in common_test_rows
            ],
            critical_result_frequency=[
                {"label": unit_name or "Unassigned", "count": int(count or 0)}
                for unit_name, count in critical_alert_rows
            ],
            specimen_rejection_trend=[
                {"label": day.isoformat() if hasattr(day, "isoformat") else str(day), "count": int(count or 0), "amount_minor": None}
                for day, count in rejection_rows
            ],
            verification_turnaround_minutes=verification_turnaround,
            completion_turnaround_minutes=completion_turnaround,
            qc_pass_fail_trend=[
                {"label": qc_status.value if hasattr(qc_status, "value") else str(qc_status), "count": int(count or 0)}
                for qc_status, count in qc_rows
            ],
            staff_workload_trend=[
                {"label": item.full_name or str(item.user_id), "count": item.workload_volume}
                for item in staff_performance[:10]
            ],
        )

    def _list_configuration_requests(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[LabManagerConfigurationRequestResponse]:
        rows = (
            self.db.query(LabConfigurationRequest)
            .filter(
                LabConfigurationRequest.clinic_id == clinic_id,
                LabConfigurationRequest.created_at >= start_dt,
                LabConfigurationRequest.created_at < end_dt,
            )
            .order_by(LabConfigurationRequest.created_at.desc())
            .limit(80)
            .all()
        )
        if not rows:
            return []
        requester_ids = {row.requested_by for row in rows}
        linked_staff_ids = {row.linked_staff_id for row in rows if row.linked_staff_id}
        linked_unit_ids = {row.linked_unit_id for row in rows if row.linked_unit_id}

        user_name_map = {
            user.id: user.full_name
            for user in self.db.query(User).filter(User.id.in_(requester_ids | linked_staff_ids)).all()
        }
        unit_name_map = self._unit_name_map(linked_unit_ids)
        return [
            LabManagerConfigurationRequestResponse(
                id=row.id,
                request_type=row.request_type,
                status=row.status,
                department_name=row.department_name,
                justification=row.justification,
                requested_by=row.requested_by,
                requested_by_name=user_name_map.get(row.requested_by),
                linked_staff_id=row.linked_staff_id,
                linked_staff_name=user_name_map.get(row.linked_staff_id),
                linked_unit_id=row.linked_unit_id,
                linked_unit_name=unit_name_map.get(row.linked_unit_id),
                linked_test_code=row.linked_test_code,
                request_payload_json=row.request_payload_json,
                created_at=row.created_at,
                updated_at=row.updated_at,
                resolved_at=row.resolved_at,
            )
            for row in rows
        ]

    def _fetch_sales_rows(
        self,
        *,
        clinic_id: UUID,
        start_dt: datetime,
        end_dt: datetime,
    ) -> list[LabManagerSalesRevenueRowResponse]:
        rows = (
            self.db.query(
                PaymentReceiptItem,
                PaymentReceipt,
                BillingItem,
                LabRequest,
                User.full_name.label("cashier_name"),
                ServiceLine.name.label("unit_name"),
            )
            .join(
                PaymentReceipt,
                and_(
                    PaymentReceipt.id == PaymentReceiptItem.receipt_id,
                    PaymentReceipt.clinic_id == PaymentReceiptItem.clinic_id,
                ),
            )
            .join(
                BillingItem,
                and_(
                    BillingItem.id == PaymentReceiptItem.billing_item_id,
                    BillingItem.clinic_id == PaymentReceiptItem.clinic_id,
                ),
            )
            .join(
                LabRequest,
                and_(
                    LabRequest.billing_item_id == BillingItem.id,
                    LabRequest.clinic_id == BillingItem.clinic_id,
                ),
            )
            .join(User, User.id == PaymentReceipt.collected_by)
            .outerjoin(ServiceLine, ServiceLine.id == LabRequest.target_unit_id)
            .filter(
                PaymentReceipt.clinic_id == clinic_id,
                PaymentReceipt.occurred_at >= start_dt,
                PaymentReceipt.occurred_at < end_dt,
            )
            .order_by(PaymentReceipt.occurred_at.desc(), PaymentReceiptItem.created_at.asc())
            .all()
        )
        if not rows:
            return []

        patient_context = self._build_patient_context_by_ids(
            clinic_id=clinic_id,
            patient_ids={receipt.patient_id for _, receipt, _, _, _, _ in rows},
        )
        return [
            LabManagerSalesRevenueRowResponse(
                receipt_id=receipt.id,
                receipt_number=receipt.receipt_number,
                occurred_at=receipt.occurred_at,
                patient_id=receipt.patient_id,
                patient_name=patient_context.get(receipt.patient_id, {}).get("patient_name"),
                patient_mrn=patient_context.get(receipt.patient_id, {}).get("patient_mrn"),
                visit_id=receipt.visit_id,
                test_name=lab_request.test_name,
                unit_id=lab_request.target_unit_id,
                unit_name=unit_name,
                quantity=billing_item.quantity,
                amount_minor=int(item.amount_minor),
                currency=receipt.currency,
                payment_method=receipt.payment_method,
                cashier_name=cashier_name,
                status=billing_item.status.value if hasattr(billing_item.status, "value") else str(billing_item.status),
            )
            for item, receipt, billing_item, lab_request, cashier_name, unit_name in rows
        ]

    def _resolve_date_range(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date, datetime, datetime]:
        today = datetime.now(timezone.utc).date()
        resolved_start = start_date or today
        resolved_end = end_date or resolved_start
        if resolved_end < resolved_start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="end_date cannot be before start_date",
            )
        start_dt = datetime.combine(resolved_start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return resolved_start, resolved_end, start_dt, end_dt

    def _resolve_currency(self, *, clinic_id: UUID) -> str:
        return (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

    def _list_lab_staff(self, *, clinic_id: UUID) -> list[User]:
        return (
            self.db.query(User)
            .filter(
                User.clinic_id == clinic_id,
                User.role.in_(LAB_WORKFORCE_ROLE_VALUES),
            )
            .order_by(User.full_name.asc(), User.created_at.asc())
            .all()
        )

    def _profile_map(
        self,
        *,
        clinic_id: UUID,
        user_ids: list[UUID],
    ) -> dict[UUID, LabStaffAssignmentProfile]:
        if not user_ids:
            return {}
        rows = (
            self.db.query(LabStaffAssignmentProfile)
            .filter(
                LabStaffAssignmentProfile.clinic_id == clinic_id,
                LabStaffAssignmentProfile.user_id.in_(user_ids),
            )
            .all()
        )
        return {row.user_id: row for row in rows}

    def _build_patient_context_by_ids(
        self,
        *,
        clinic_id: UUID,
        patient_ids: set[UUID],
    ) -> dict[UUID, dict]:
        if not patient_ids:
            return {}
        patients = self.db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
        patient_map = {patient.id: patient.full_name for patient in patients}
        canonical_map = {
            patient_id: self._resolve_canonical_patient_id(clinic_id=clinic_id, patient_id=patient_id)
            for patient_id in patient_ids
        }
        mrn_rows = (
            self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id.in_(set(canonical_map.values())),
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .all()
        )
        mrn_map = {patient_id: mrn for patient_id, mrn in mrn_rows}
        return {
            patient_id: {
                "patient_name": patient_map.get(patient_id),
                "patient_mrn": mrn_map.get(canonical_map.get(patient_id, patient_id)),
            }
            for patient_id in patient_ids
        }

    def _effective_assignment_status(
        self,
        profile: LabStaffAssignmentProfile | None,
    ) -> LabStaffAssignmentStatus:
        return profile.assignment_status if profile else LabStaffAssignmentStatus.ACTIVE

    def _get_or_create_assignment_profile(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
    ) -> LabStaffAssignmentProfile:
        profile = (
            self.db.query(LabStaffAssignmentProfile)
            .filter(
                LabStaffAssignmentProfile.clinic_id == clinic_id,
                LabStaffAssignmentProfile.user_id == user_id,
            )
            .first()
        )
        if profile is not None:
            return profile
        profile = LabStaffAssignmentProfile(
            clinic_id=clinic_id,
            user_id=user_id,
            assignment_status=LabStaffAssignmentStatus.ACTIVE,
        )
        self.db.add(profile)
        self.db.flush()
        return profile

    def _get_lab_staff_user(self, *, clinic_id: UUID, user_id: UUID) -> User:
        user = (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.clinic_id == clinic_id,
                User.role.in_(LAB_WORKFORCE_ROLE_VALUES),
            )
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab staff user not found",
            )
        return user

    def _get_manager_user(self, *, clinic_id: UUID, user_id: UUID) -> User:
        user = (
            self.db.query(User)
            .filter(
                User.id == user_id,
                User.clinic_id == clinic_id,
                User.role == UserRole.LAB_MANAGER.value,
            )
            .first()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab manager access required",
            )
        return user

    def _count_blocked_unpaid_requests(self, *, clinic_id: UUID) -> int:
        return (
            self.db.query(LabRequest.id)
            .join(BillingItem, BillingItem.id == LabRequest.billing_item_id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                BillingItem.status != BillingItemStatus.PAID,
                LabRequest.status == LabRequestStatus.PENDING,
            )
            .count()
        )

    def _active_leaf_lab_units(self, *, clinic_id: UUID) -> list[ServiceLine]:
        units = self._active_lab_units(clinic_id=clinic_id)
        parent_ids = {unit.parent_id for unit in units if unit.parent_id}
        return [unit for unit in units if unit.id not in parent_ids]

    def _parse_json(self, raw_payload) -> dict:
        if isinstance(raw_payload, dict):
            return raw_payload
        if not raw_payload:
            return {}
        try:
            value = json.loads(raw_payload)
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def _parse_uuid(self, raw_value) -> UUID | None:
        if raw_value in {None, ""}:
            return None
        try:
            return UUID(str(raw_value))
        except Exception:
            return None

    def _format_request_type(self, request_type: LabConfigurationRequestType) -> str:
        return request_type.value.replace("_", " ").title()

    def _summarize_event_audit_item(
        self,
        *,
        event_type: str,
        request: LabRequest | None,
        specimen: LabSpecimen | None,
        payload: dict,
    ) -> tuple[str, str | None, str]:
        if event_type == "LAB_RESULT_ENTERED":
            return (
                f"Result entered for {request.test_name if request else 'lab test'}",
                "Structured lab result saved for review",
                "info",
            )
        if event_type == "LAB_RESULT_SUBMITTED":
            return (
                f"Result submitted for {request.test_name if request else 'lab test'}",
                "Awaiting verification or release policy check",
                "info",
            )
        if event_type == "LAB_RESULT_VERIFIED":
            return (
                f"Result verified for {request.test_name if request else 'lab test'}",
                "Verification completed under lab authority policy",
                "info",
            )
        if event_type == "LAB_RESULT_RELEASED":
            return (
                f"Result released for {request.test_name if request else 'lab test'}",
                "Released result became visible to clinicians",
                "info",
            )
        if event_type == "LAB_RESULT_AMENDED":
            return (
                f"Result amended for {request.test_name if request else 'lab test'}",
                "A new amendment version was created",
                "warning",
            )
        if event_type == "LAB_QC_OVERRIDE":
            analytes = ((payload.get("metadata_json") or {}).get("blocking_analytes") or [])
            detail = ", ".join(analytes) if analytes else "Supervisor QC override recorded"
            return (
                f"QC override recorded for {request.test_name if request else 'lab result'}",
                detail,
                "warning",
            )
        if event_type == "LAB_STAFF_ASSIGNMENT_UPDATED":
            return (
                "Lab staff assignment updated",
                payload.get("target_user_name") or "Department staffing assignment was changed",
                "info",
            )
        return (
            event_type.replace("_", " ").title(),
            specimen.accession_number if specimen else None,
            "info",
        )

    def _summarize_specimen_event(
        self,
        *,
        event_type: LabSpecimenEventType,
        request: LabRequest,
    ) -> tuple[str, str | None, str]:
        if event_type == LabSpecimenEventType.COLLECTED:
            return (f"Specimen collected for {request.test_name}", "Collection logged", "info")
        if event_type == LabSpecimenEventType.RECEIVED:
            return (f"Specimen received for {request.test_name}", "Received into laboratory workflow", "info")
        if event_type == LabSpecimenEventType.LABEL_PRINTED:
            return (f"Specimen label printed for {request.test_name}", "Label print was logged", "info")
        if event_type == LabSpecimenEventType.RECOLLECTION_REQUESTED:
            return (f"Recollection requested for {request.test_name}", "Specimen needs recollection", "warning")
        if event_type == LabSpecimenEventType.LOST:
            return (f"Specimen marked lost for {request.test_name}", "Specimen workflow issue recorded", "critical")
        if event_type == LabSpecimenEventType.ANALYSIS_STARTED:
            return (f"Analysis started for {request.test_name}", "Specimen entered bench workflow", "info")
        if event_type == LabSpecimenEventType.ANALYSIS_COMPLETED:
            return (f"Analysis completed for {request.test_name}", "Bench work marked complete", "info")
        if event_type == LabSpecimenEventType.DISPOSED:
            return (f"Specimen disposed for {request.test_name}", "Lifecycle closed", "info")
        return (event_type.value.replace("_", " ").title(), request.test_name, "info")

    def _avg_minutes(self, raw_value) -> float | None:
        if raw_value is None:
            return None
        try:
            return round(float(raw_value), 1)
        except Exception:
            return None

    def _ensure_utc(self, raw_value: datetime | None) -> datetime:
        if raw_value is None:
            return datetime.now(timezone.utc)
        if raw_value.tzinfo is None:
            return raw_value.replace(tzinfo=timezone.utc)
        return raw_value
