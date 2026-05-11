from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_qc_result import LabQcResult
from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_specimen import LabSpecimen
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.patient_mrn import PatientMRN
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab_workspace import (
    LabManagerCriticalAlertSummaryResponse,
    LabManagerOverviewResponse,
    LabManagerQcFailureSummaryResponse,
    LabManagerRequestSummaryResponse,
    LabManagerSpecimenIssueSummaryResponse,
    LabManagerUnitMetricResponse,
    LabWorkspaceOverviewResponse,
    LabWorkspaceQcRunSummaryResponse,
    LabWorkspaceSpecimenSummaryResponse,
)
from app.shared.enums import (
    BillingItemStatus,
    LabCriticalAlertStatus,
    LabQcStatus,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    ServiceLineKind,
)
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_foundation_service import LabFoundationService


READY_SPECIMEN_STATUSES = (
    LabSpecimenStatus.RECEIVED,
    LabSpecimenStatus.IN_PROCESS,
)
PENDING_VERIFICATION_RESULT_STATUSES = (
    LabResultLifecycleStatus.DRAFT,
    LabResultLifecycleStatus.SUBMITTED,
)
UNRESOLVED_ALERT_STATUSES = (
    LabCriticalAlertStatus.CREATED,
    LabCriticalAlertStatus.DELIVERED,
    LabCriticalAlertStatus.ACKNOWLEDGED,
    LabCriticalAlertStatus.ESCALATED,
)
SPECIMEN_ISSUE_STATUSES = (
    LabSpecimenStatus.REJECTED,
    LabSpecimenStatus.LOST,
)


class LabWorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def list_unit_requests(
        self,
        *,
        clinic_id: UUID,
        unit_id: UUID,
        status: LabRequestStatus | None = None,
        workflow_status: LabRequestWorkflowStatus | None = None,
    ) -> list[LabRequest]:
        self._reconcile_pending_request_configuration(clinic_id=clinic_id)
        query = (
            self.db.query(LabRequest)
            .join(BillingItem, BillingItem.id == LabRequest.billing_item_id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.target_unit_id == unit_id,
                BillingItem.status == BillingItemStatus.PAID,
            )
        )
        if status is not None:
            query = query.filter(LabRequest.status == status)
        if workflow_status is not None:
            query = query.filter(LabRequest.workflow_status == workflow_status)

        requests = query.order_by(LabRequest.created_at.desc()).all()
        self._attach_request_context(clinic_id=clinic_id, lab_requests=requests)
        BillingWorkflowService(self.db).attach_lab_request_billing(lab_requests=requests)
        self._attach_request_operational_context(lab_requests=requests)
        return requests

    def get_unit_overview(
        self,
        *,
        clinic_id: UUID,
        unit: ServiceLine,
    ) -> LabWorkspaceOverviewResponse:
        pending_requests = self.list_unit_requests(
            clinic_id=clinic_id,
            unit_id=unit.id,
            status=LabRequestStatus.PENDING,
        )
        completed_today = (
            self.db.query(LabRequest.id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.target_unit_id == unit.id,
                LabRequest.status == LabRequestStatus.COMPLETED,
                func.date(LabRequest.completed_at) == datetime.now(timezone.utc).date(),
            )
            .count()
        )
        critical_alerts = (
            self.db.query(LabCriticalAlert.id)
            .filter(
                LabCriticalAlert.unit_id == unit.id,
                LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
            )
            .count()
        )
        qc_failures = (
            self.db.query(LabQcRun.id)
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.unit_id == unit.id,
                LabQcRun.status == LabQcStatus.FAIL,
            )
            .count()
        )
        unrouted_requests = self._count_unrouted_requests(clinic_id=clinic_id)

        awaiting_specimen = sum(1 for request in pending_requests if getattr(request, "ready_specimen_count", 0) == 0)
        pending_verifications = sum(
            1
            for request in pending_requests
            if getattr(request, "latest_result_status", None) in PENDING_VERIFICATION_RESULT_STATUSES
        )

        return LabWorkspaceOverviewResponse(
            unit_id=unit.id,
            unit_name=unit.name,
            pending_requests=len(pending_requests),
            awaiting_specimen=awaiting_specimen,
            pending_verifications=pending_verifications,
            critical_alerts=critical_alerts,
            completed_today=completed_today,
            qc_failures=qc_failures,
            unrouted_requests=unrouted_requests,
        )

    def list_unit_specimens(
        self,
        *,
        clinic_id: UUID,
        unit_id: UUID,
        status: LabSpecimenStatus | None = None,
    ) -> list[LabWorkspaceSpecimenSummaryResponse]:
        query = (
            self.db.query(LabSpecimen)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimen.target_unit_id == unit_id,
            )
            .order_by(LabSpecimen.updated_at.desc())
        )
        if status is not None:
            query = query.filter(LabSpecimen.status == status)

        specimens = query.all()
        if not specimens:
            return []

        request_ids = {specimen.request_item_id for specimen in specimens}
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
        unit_names = self._unit_name_map({unit_id})

        return [
            LabWorkspaceSpecimenSummaryResponse(
                id=specimen.id,
                accession_number=specimen.accession_number,
                request_item_id=specimen.request_item_id,
                visit_id=request_map[specimen.request_item_id].visit_id,
                patient_id=visit_context[request_map[specimen.request_item_id].visit_id]["patient_id"],
                patient_name=visit_context[request_map[specimen.request_item_id].visit_id]["patient_name"],
                patient_mrn=visit_context[request_map[specimen.request_item_id].visit_id]["patient_mrn"],
                test_name=request_map[specimen.request_item_id].test_name,
                target_unit_id=specimen.target_unit_id,
                target_unit_name=unit_names.get(specimen.target_unit_id),
                status=specimen.status,
                specimen_type=specimen.specimen_type,
                specimen_source=specimen.specimen_source,
                container_type=specimen.container_type,
                collection_site=specimen.collection_site,
                collected_at=specimen.collected_at,
                received_at=specimen.received_at,
                rejection_reason_code=specimen.rejection_reason_code,
                rejection_reason_text=specimen.rejection_reason_text,
                created_at=specimen.created_at,
                updated_at=specimen.updated_at,
            )
            for specimen in specimens
            if specimen.request_item_id in request_map
        ]

    def list_unit_qc_runs(
        self,
        *,
        clinic_id: UUID,
        unit_id: UUID,
    ) -> list[LabWorkspaceQcRunSummaryResponse]:
        runs = (
            self.db.query(LabQcRun)
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcRun.unit_id == unit_id,
            )
            .order_by(LabQcRun.performed_at.desc())
            .limit(25)
            .all()
        )
        if not runs:
            return []

        run_ids = [run.id for run in runs]
        qc_rows = (
            self.db.query(LabQcResult)
            .filter(LabQcResult.qc_run_id.in_(run_ids))
            .all()
        )
        fail_counts: dict[UUID, int] = defaultdict(int)
        warning_counts: dict[UUID, int] = defaultdict(int)
        for row in qc_rows:
            if row.status == LabQcStatus.FAIL:
                fail_counts[row.qc_run_id] += 1
            elif row.status == LabQcStatus.WARNING:
                warning_counts[row.qc_run_id] += 1

        unit_names = self._unit_name_map({unit_id})
        return [
            LabWorkspaceQcRunSummaryResponse(
                id=run.id,
                unit_id=run.unit_id,
                unit_name=unit_names.get(run.unit_id),
                machine_id=run.machine_id,
                qc_level=run.qc_level,
                status=run.status,
                performed_by=run.performed_by,
                performed_at=run.performed_at,
                fail_count=fail_counts.get(run.id, 0),
                warning_count=warning_counts.get(run.id, 0),
                notes=run.notes,
                created_at=run.created_at,
                updated_at=run.updated_at,
            )
            for run in runs
        ]

    def get_manager_overview(self, *, clinic_id: UUID) -> LabManagerOverviewResponse:
        units = self._active_lab_units(clinic_id=clinic_id)
        unit_metrics = [self._build_manager_unit_metric(clinic_id=clinic_id, unit=unit) for unit in units]
        pending_verifications = self._list_pending_verifications(clinic_id=clinic_id)
        critical_alerts = self._list_critical_alerts(clinic_id=clinic_id)
        qc_failures = self._list_qc_failures(clinic_id=clinic_id)
        specimen_issues = self._list_specimen_issues(clinic_id=clinic_id)
        return LabManagerOverviewResponse(
            total_pending_requests=sum(item.pending_requests for item in unit_metrics),
            total_pending_verifications=sum(item.pending_verifications for item in unit_metrics),
            total_critical_alerts=len(critical_alerts),
            total_qc_failures=len(qc_failures),
            total_specimen_issues=len(specimen_issues),
            unrouted_requests=self._count_unrouted_requests(clinic_id=clinic_id),
            unit_metrics=unit_metrics,
            pending_verifications=pending_verifications,
            critical_alerts=critical_alerts,
            qc_failures=qc_failures,
            specimen_issues=specimen_issues,
        )

    def _build_manager_unit_metric(
        self,
        *,
        clinic_id: UUID,
        unit: ServiceLine,
    ) -> LabManagerUnitMetricResponse:
        overview = self.get_unit_overview(clinic_id=clinic_id, unit=unit)
        specimen_issues = (
            self.db.query(LabSpecimen.id)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimen.target_unit_id == unit.id,
                LabSpecimen.status.in_(SPECIMEN_ISSUE_STATUSES),
            )
            .count()
        )
        return LabManagerUnitMetricResponse(
            unit_id=unit.id,
            unit_name=unit.name,
            pending_requests=overview.pending_requests,
            awaiting_specimen=overview.awaiting_specimen,
            pending_verifications=overview.pending_verifications,
            critical_alerts=overview.critical_alerts,
            qc_failures=overview.qc_failures,
            specimen_issues=specimen_issues,
            completed_today=overview.completed_today,
        )

    def _list_pending_verifications(self, *, clinic_id: UUID) -> list[LabManagerRequestSummaryResponse]:
        results = (
            self.db.query(LabResult)
            .join(LabRequest, LabRequest.id == (LabResult.request_item_id))
            .filter(
                LabResult.clinic_id == clinic_id,
                LabResult.status.in_(PENDING_VERIFICATION_RESULT_STATUSES),
                LabRequest.target_unit_id.isnot(None),
            )
            .order_by(LabResult.entered_at.desc())
            .limit(20)
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
        unit_names = self._unit_name_map({request.target_unit_id for request in requests if request.target_unit_id})

        return [
            LabManagerRequestSummaryResponse(
                request_id=request.id,
                visit_id=request.visit_id,
                patient_id=visit_context[request.visit_id]["patient_id"],
                patient_name=visit_context[request.visit_id]["patient_name"],
                patient_mrn=visit_context[request.visit_id]["patient_mrn"],
                test_name=request.test_name,
                status=request.status,
                workflow_status=request.workflow_status,
                unit_id=request.target_unit_id,
                unit_name=unit_names.get(request.target_unit_id),
                latest_result_id=result.id,
                latest_result_status=result.status,
                created_at=request.created_at,
            )
            for result in results
            if (request := request_map.get(result.request_item_id or result.lab_request_id)) is not None
        ]

    def _list_critical_alerts(self, *, clinic_id: UUID) -> list[LabManagerCriticalAlertSummaryResponse]:
        alerts = (
            self.db.query(LabCriticalAlert)
            .filter(
                LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
                LabCriticalAlert.unit_id.isnot(None),
            )
            .order_by(LabCriticalAlert.created_at.desc())
            .limit(20)
            .all()
        )
        if not alerts:
            return []

        request_ids = {alert.request_item_id for alert in alerts if alert.request_item_id}
        requests = self.db.query(LabRequest).filter(LabRequest.id.in_(request_ids)).all() if request_ids else []
        request_map = {request.id: request for request in requests}
        visit_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for request in requests},
        )
        unit_names = self._unit_name_map({alert.unit_id for alert in alerts if alert.unit_id})

        return [
            LabManagerCriticalAlertSummaryResponse(
                alert_id=alert.id,
                result_id=alert.result_id,
                request_item_id=alert.request_item_id,
                visit_id=alert.visit_id,
                patient_id=alert.patient_id,
                patient_name=visit_context.get(alert.visit_id, {}).get("patient_name"),
                patient_mrn=visit_context.get(alert.visit_id, {}).get("patient_mrn"),
                test_name=request_map.get(alert.request_item_id).test_name if alert.request_item_id in request_map else None,
                unit_id=alert.unit_id,
                unit_name=unit_names.get(alert.unit_id),
                severity=alert.severity,
                status=alert.status,
                message=alert.message,
                created_at=alert.created_at,
            )
            for alert in alerts
        ]

    def _list_qc_failures(self, *, clinic_id: UUID) -> list[LabManagerQcFailureSummaryResponse]:
        rows = (
            self.db.query(LabQcResult, LabQcRun)
            .join(LabQcRun, LabQcRun.id == LabQcResult.qc_run_id)
            .filter(
                LabQcRun.clinic_id == clinic_id,
                LabQcResult.status == LabQcStatus.FAIL,
            )
            .order_by(LabQcRun.performed_at.desc())
            .limit(20)
            .all()
        )
        if not rows:
            return []
        unit_names = self._unit_name_map({run.unit_id for _, run in rows})
        return [
            LabManagerQcFailureSummaryResponse(
                qc_run_id=run.id,
                qc_result_id=result.id,
                unit_id=run.unit_id,
                unit_name=unit_names.get(run.unit_id),
                qc_level=run.qc_level,
                analyte_name=result.analyte_name,
                expected_min=float(result.expected_min) if result.expected_min is not None else None,
                expected_max=float(result.expected_max) if result.expected_max is not None else None,
                observed_value=float(result.observed_value),
                performed_at=run.performed_at,
            )
            for result, run in rows
        ]

    def _list_specimen_issues(self, *, clinic_id: UUID) -> list[LabManagerSpecimenIssueSummaryResponse]:
        specimens = (
            self.db.query(LabSpecimen)
            .filter(
                LabSpecimen.clinic_id == clinic_id,
                LabSpecimen.status.in_(SPECIMEN_ISSUE_STATUSES),
            )
            .order_by(LabSpecimen.updated_at.desc())
            .limit(20)
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
        return [
            LabManagerSpecimenIssueSummaryResponse(
                specimen_id=specimen.id,
                accession_number=specimen.accession_number,
                request_item_id=specimen.request_item_id,
                visit_id=request_map[specimen.request_item_id].visit_id,
                patient_id=visit_context[request_map[specimen.request_item_id].visit_id]["patient_id"],
                patient_name=visit_context[request_map[specimen.request_item_id].visit_id]["patient_name"],
                patient_mrn=visit_context[request_map[specimen.request_item_id].visit_id]["patient_mrn"],
                test_name=request_map[specimen.request_item_id].test_name,
                unit_id=specimen.target_unit_id,
                unit_name=unit_names.get(specimen.target_unit_id),
                status=specimen.status,
                rejection_reason_code=specimen.rejection_reason_code,
                rejection_reason_text=specimen.rejection_reason_text,
                updated_at=specimen.updated_at,
            )
            for specimen in specimens
            if specimen.request_item_id in request_map
        ]

    def _attach_request_context(self, *, clinic_id: UUID, lab_requests: list[LabRequest]) -> None:
        if not lab_requests:
            return
        visit_context = self._build_visit_context(
            clinic_id=clinic_id,
            visit_ids={request.visit_id for request in lab_requests},
        )
        requester_ids = {request.requested_by for request in lab_requests}
        users = self.db.query(User).filter(User.id.in_(requester_ids)).all()
        user_map = {user.id: user for user in users}
        unit_names = self._unit_name_map(
            {request.target_unit_id for request in lab_requests if request.target_unit_id}
        )

        for request in lab_requests:
            context = visit_context.get(request.visit_id, {})
            request.patient_id = context.get("patient_id")
            request.patient_name = context.get("patient_name")
            request.patient_mrn = context.get("patient_mrn")
            requester = user_map.get(request.requested_by)
            request.requested_by_name = requester.full_name if requester else None
            request.requested_by_role = requester.role if requester else None
            request.target_unit_name = unit_names.get(request.target_unit_id)

    def _attach_request_operational_context(self, *, lab_requests: list[LabRequest]) -> None:
        if not lab_requests:
            return
        request_ids = [request.id for request in lab_requests]

        ready_specimen_counts = {
            request_item_id: count
            for request_item_id, count in (
                self.db.query(
                    LabSpecimen.request_item_id,
                    func.count(LabSpecimen.id),
                )
                .filter(
                    LabSpecimen.request_item_id.in_(request_ids),
                    LabSpecimen.status.in_(READY_SPECIMEN_STATUSES),
                )
                .group_by(LabSpecimen.request_item_id)
                .all()
            )
        }

        alert_counts = {
            request_item_id: count
            for request_item_id, count in (
                self.db.query(
                    LabCriticalAlert.request_item_id,
                    func.count(LabCriticalAlert.id),
                )
                .filter(
                    LabCriticalAlert.request_item_id.in_(request_ids),
                    LabCriticalAlert.status.in_(UNRESOLVED_ALERT_STATUSES),
                )
                .group_by(LabCriticalAlert.request_item_id)
                .all()
            )
        }

        latest_results: dict[UUID, LabResult] = {}
        result_rows = (
            self.db.query(LabResult)
            .filter(
                LabResult.request_item_id.in_(request_ids),
                LabResult.status.in_(
                    (
                        LabResultLifecycleStatus.DRAFT,
                        LabResultLifecycleStatus.SUBMITTED,
                        LabResultLifecycleStatus.VERIFIED,
                        LabResultLifecycleStatus.RELEASED,
                        LabResultLifecycleStatus.AMENDED,
                    )
                ),
            )
            .order_by(LabResult.released_at.desc().nullslast(), LabResult.created_at.desc())
            .all()
        )
        for result in result_rows:
            request_id = result.request_item_id or result.lab_request_id
            if request_id not in latest_results:
                latest_results[request_id] = result

        for request in lab_requests:
            request.ready_specimen_count = ready_specimen_counts.get(request.id, 0)
            request.critical_alert_count = alert_counts.get(request.id, 0)
            latest_result = latest_results.get(request.id)
            request.active_result_id = latest_result.id if latest_result else None
            request.latest_result_status = latest_result.status if latest_result else None

    def _build_visit_context(self, *, clinic_id: UUID, visit_ids: set[UUID]) -> dict[UUID, dict]:
        if not visit_ids:
            return {}
        visits = self.db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
        patient_ids = {visit.patient_id for visit in visits}
        patients = self.db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
        patient_map = {patient.id: patient.full_name for patient in patients}
        canonical_map = {
            patient_id: self._resolve_canonical_patient_id(clinic_id=clinic_id, patient_id=patient_id)
            for patient_id in patient_ids
        }
        canonical_ids = set(canonical_map.values())
        mrns = (
            self.db.query(PatientMRN.patient_id, PatientMRN.mrn)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id.in_(canonical_ids),
            )
            .all()
        )
        mrn_map = {patient_id: mrn for patient_id, mrn in mrns}
        return {
            visit.id: {
                "patient_id": visit.patient_id,
                "patient_name": patient_map.get(visit.patient_id),
                "patient_mrn": mrn_map.get(canonical_map.get(visit.patient_id, visit.patient_id)),
            }
            for visit in visits
        }

    def _resolve_canonical_patient_id(self, *, clinic_id: UUID, patient_id: UUID) -> UUID:
        visited = set()
        current = patient_id
        for _ in range(10):
            if current in visited:
                return patient_id
            visited.add(current)
            mapping = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.from_patient_id == current,
                )
                .first()
            )
            if not mapping:
                return current
            revoked = (
                self.db.query(IdentityMapRevocation)
                .filter(
                    IdentityMapRevocation.clinic_id == clinic_id,
                    IdentityMapRevocation.map_id == mapping.id,
                )
                .first()
            )
            if revoked:
                return current
            current = mapping.to_patient_id
        return patient_id

    def _unit_name_map(self, unit_ids: set[UUID]) -> dict[UUID, str]:
        if not unit_ids:
            return {}
        rows = (
            self.db.query(ServiceLine.id, ServiceLine.name)
            .filter(ServiceLine.id.in_(unit_ids))
            .all()
        )
        return {row.id: row.name for row in rows}

    def _active_lab_units(self, *, clinic_id: UUID) -> list[ServiceLine]:
        return (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.is_active == True,
                ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            )
            .order_by(ServiceLine.name.asc())
            .all()
        )

    def _count_unrouted_requests(self, *, clinic_id: UUID) -> int:
        return (
            self.db.query(LabRequest.id)
            .join(BillingItem, BillingItem.id == LabRequest.billing_item_id)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.target_unit_id.is_(None),
                LabRequest.status == LabRequestStatus.PENDING,
                BillingItem.status == BillingItemStatus.PAID,
            )
            .count()
        )

    def _reconcile_pending_request_configuration(self, *, clinic_id: UUID) -> None:
        LabFoundationService(self.db).reconcile_request_configuration_for_clinic(
            clinic_id=clinic_id,
        )
