from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.billing_item import BillingItem
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.service_line import ServiceLine
from app.models.visit import Visit
from app.schemas.lab_workflow import (
    LabRequestWorkflowStateResponse,
    LabSpecimenDefaultsResponse,
    LabWorkflowChecklistItemResponse,
    LabWorkflowStatusChipResponse,
)
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_foundation_service import LabFoundationService
from app.shared.enums import (
    BillingItemStatus,
    LabRequestStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    LabVerificationPolicy,
    VisitStatus,
)


READY_SPECIMEN_STATUSES = (
    LabSpecimenStatus.RECEIVED,
    LabSpecimenStatus.IN_PROCESS,
)
ACTIVE_RESULT_STATUSES = (
    LabResultLifecycleStatus.DRAFT,
    LabResultLifecycleStatus.SUBMITTED,
    LabResultLifecycleStatus.VERIFIED,
    LabResultLifecycleStatus.RELEASED,
    LabResultLifecycleStatus.AMENDED,
)

TEST_CODE_SPECIMEN_DEFAULTS: dict[str, LabSpecimenDefaultsResponse] = {
    "CHEM_FBS": LabSpecimenDefaultsResponse(
        specimen_type="Blood",
        specimen_source="Blood",
        container_type="Fluoride oxalate / plain tube",
    ),
    "CHEM_RBS": LabSpecimenDefaultsResponse(
        specimen_type="Blood",
        specimen_source="Blood",
        container_type="Fluoride oxalate / plain tube",
    ),
}


class LabRequestWorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.foundation_service = LabFoundationService(db)

    def get_workflow_state(self, *, lab_request: LabRequest) -> LabRequestWorkflowStateResponse:
        lab_request, _ = self.foundation_service.reconcile_request_configuration(
            lab_request=lab_request,
            auto_commit=True,
        )
        billing_paid = BillingWorkflowService(self.db).is_lab_request_paid(lab_request=lab_request)
        ready_specimen_exists = self._ready_specimen_exists(lab_request_id=lab_request.id)
        latest_result = self._get_latest_result(lab_request_id=lab_request.id)
        visit = self._get_visit(lab_request=lab_request)
        config = self._get_test_config(lab_request=lab_request)
        verification_policy = (
            config.verification_policy if config is not None else LabVerificationPolicy.OPTIONAL
        )
        has_abnormal, has_critical = self._get_result_flags(result=latest_result)
        verification_required = self._is_verification_required(
            verification_policy=verification_policy,
            has_abnormal=has_abnormal,
            has_critical=has_critical,
        )
        result_entered = latest_result is not None
        result_verified = latest_result is not None and latest_result.status in (
            LabResultLifecycleStatus.VERIFIED,
            LabResultLifecycleStatus.RELEASED,
            LabResultLifecycleStatus.AMENDED,
        )
        result_released = latest_result is not None and latest_result.status in (
            LabResultLifecycleStatus.RELEASED,
            LabResultLifecycleStatus.AMENDED,
        )
        visit_ready_for_completion = bool(
            visit is not None and visit.status == VisitStatus.LAB_REQUESTED
        )
        can_complete = (
            lab_request.status != LabRequestStatus.COMPLETED
            and billing_paid
            and result_released
            and visit_ready_for_completion
        )

        unit_name = None
        if lab_request.target_unit_id is not None:
            unit = (
                self.db.query(ServiceLine)
                .filter(ServiceLine.id == lab_request.target_unit_id)
                .first()
            )
            unit_name = unit.name if unit is not None else None

        completion_message = self._build_completion_message(
            billing_paid=billing_paid,
            ready_specimen_exists=ready_specimen_exists,
            result_entered=result_entered,
            result_released=result_released,
            verification_required=verification_required,
            result_verified=result_verified,
            visit_ready_for_completion=visit_ready_for_completion,
            completed=lab_request.status == LabRequestStatus.COMPLETED,
        )

        return LabRequestWorkflowStateResponse(
            request_id=lab_request.id,
            request_status=lab_request.status.value,
            workflow_status=lab_request.workflow_status.value if lab_request.workflow_status else None,
            unit_id=lab_request.target_unit_id,
            unit_name=unit_name,
            verification_policy=verification_policy,
            completion_message=completion_message,
            can_complete=can_complete,
            status_chips=self._build_status_chips(
                billing_paid=billing_paid,
                ready_specimen_exists=ready_specimen_exists,
                latest_result=latest_result,
                can_complete=can_complete,
                completed=lab_request.status == LabRequestStatus.COMPLETED,
            ),
            checklist=self._build_checklist(
                billing_paid=billing_paid,
                ready_specimen_exists=ready_specimen_exists,
                result_entered=result_entered,
                result_verified=result_verified,
                result_released=result_released,
                verification_required=verification_required,
                visit_ready_for_completion=visit_ready_for_completion,
                can_complete=can_complete,
                completed=lab_request.status == LabRequestStatus.COMPLETED,
            ),
            specimen_defaults=self._build_specimen_defaults(
                lab_request=lab_request,
                config=config,
            ),
        )

    def _ready_specimen_exists(self, *, lab_request_id: UUID) -> bool:
        return (
            self.db.query(LabSpecimen.id)
            .filter(
                LabSpecimen.request_item_id == lab_request_id,
                LabSpecimen.status.in_(READY_SPECIMEN_STATUSES),
            )
            .first()
            is not None
        )

    def _get_latest_result(self, *, lab_request_id: UUID) -> LabResult | None:
        return (
            self.db.query(LabResult)
            .filter(
                LabResult.request_item_id == lab_request_id,
                LabResult.status.in_(ACTIVE_RESULT_STATUSES),
            )
            .order_by(LabResult.released_at.desc().nullslast(), LabResult.created_at.desc())
            .first()
        )

    def _get_result_flags(self, *, result: LabResult | None) -> tuple[bool, bool]:
        if result is None:
            return False, False
        flags = (
            self.db.query(LabResultValue.abnormal_flag, LabResultValue.critical_flag)
            .filter(LabResultValue.result_id == result.id)
            .all()
        )
        return (
            any(row.abnormal_flag for row in flags),
            any(row.critical_flag for row in flags),
        )

    def _get_visit(self, *, lab_request: LabRequest) -> Visit | None:
        return self.db.query(Visit).filter(Visit.id == lab_request.visit_id).first()

    def _get_test_config(self, *, lab_request: LabRequest) -> LabTestConfig | None:
        if lab_request.lab_test_config_id is None:
            return None
        return (
            self.db.query(LabTestConfig)
            .filter(LabTestConfig.id == lab_request.lab_test_config_id)
            .first()
        )

    def _is_verification_required(
        self,
        *,
        verification_policy: LabVerificationPolicy,
        has_abnormal: bool,
        has_critical: bool,
    ) -> bool:
        if verification_policy == LabVerificationPolicy.REQUIRED_BEFORE_RELEASE:
            return True
        if verification_policy == LabVerificationPolicy.REQUIRED_IF_ABNORMAL:
            return has_abnormal
        if verification_policy == LabVerificationPolicy.REQUIRED_IF_CRITICAL:
            return has_critical
        return False

    def _build_completion_message(
        self,
        *,
        billing_paid: bool,
        ready_specimen_exists: bool,
        result_entered: bool,
        result_released: bool,
        verification_required: bool,
        result_verified: bool,
        visit_ready_for_completion: bool,
        completed: bool,
    ) -> str:
        if completed:
            return "This lab request has already been completed."
        if not billing_paid:
            return "Payment must be verified before this lab request can be completed."
        if not visit_ready_for_completion:
            return "The visit must be in LAB_REQUESTED before this lab request can be completed."
        if not ready_specimen_exists:
            return "A received specimen is required before this lab request can be completed."
        if not result_entered:
            return "A released result is required before this lab request can be completed."
        if verification_required and not result_verified:
            return "A verified and released result is required before this lab request can be completed."
        if not result_released:
            return "A released result is required before this lab request can be completed."
        return "This lab request is ready to be completed."

    def _build_status_chips(
        self,
        *,
        billing_paid: bool,
        ready_specimen_exists: bool,
        latest_result: LabResult | None,
        can_complete: bool,
        completed: bool,
    ) -> list[LabWorkflowStatusChipResponse]:
        result_value = (
            latest_result.status.value.replace("_", " ").title()
            if latest_result is not None and latest_result.status is not None
            else "Pending"
        )
        return [
            LabWorkflowStatusChipResponse(
                key="payment",
                label="Payment",
                value="Paid" if billing_paid else "Unpaid",
                tone="success" if billing_paid else "warning",
            ),
            LabWorkflowStatusChipResponse(
                key="specimen",
                label="Specimen",
                value="Received" if ready_specimen_exists else "Pending",
                tone="success" if ready_specimen_exists else "warning",
            ),
            LabWorkflowStatusChipResponse(
                key="result",
                label="Result",
                value=result_value,
                tone="success"
                if latest_result is not None and latest_result.status == LabResultLifecycleStatus.RELEASED
                else "info"
                if latest_result is not None
                else "warning",
            ),
            LabWorkflowStatusChipResponse(
                key="completion",
                label="Completion",
                value="Completed" if completed else "Ready" if can_complete else "Blocked",
                tone="success" if completed or can_complete else "warning",
            ),
        ]

    def _build_checklist(
        self,
        *,
        billing_paid: bool,
        ready_specimen_exists: bool,
        result_entered: bool,
        result_verified: bool,
        result_released: bool,
        verification_required: bool,
        visit_ready_for_completion: bool,
        can_complete: bool,
        completed: bool,
    ) -> list[LabWorkflowChecklistItemResponse]:
        verification_detail = (
            None
            if verification_required
            else "Not required by the current verification policy."
        )
        return [
            LabWorkflowChecklistItemResponse(
                key="paid-request",
                label="Paid request",
                state="complete" if billing_paid else "blocked",
                detail=None if billing_paid else "Waiting for cashier payment verification.",
            ),
            LabWorkflowChecklistItemResponse(
                key="specimen-received",
                label="Specimen received",
                state="complete" if ready_specimen_exists else "pending",
                detail=None if ready_specimen_exists else "Register or receive the specimen first.",
            ),
            LabWorkflowChecklistItemResponse(
                key="result-entered",
                label="Result entered",
                state="complete" if result_entered else "pending",
                detail=None if result_entered else "Enter results through the configured template.",
            ),
            LabWorkflowChecklistItemResponse(
                key="result-verified",
                label="Result verified",
                state="complete" if result_verified or not verification_required else "pending",
                detail=verification_detail
                if result_verified or not verification_required
                else "Verification is still required before release.",
            ),
            LabWorkflowChecklistItemResponse(
                key="result-released",
                label="Result released",
                state="complete" if result_released else "pending",
                detail=None if result_released else "Release the latest result before completion.",
            ),
            LabWorkflowChecklistItemResponse(
                key="completion-eligible",
                label="Completion eligible",
                state="complete" if completed or can_complete else "blocked",
                detail=None
                if completed or can_complete
                else (
                    "Move the visit to LAB_REQUESTED before completion."
                    if not visit_ready_for_completion
                    else "Complete this request after all release requirements are satisfied."
                ),
            ),
        ]

    def _build_specimen_defaults(
        self,
        *,
        lab_request: LabRequest,
        config: LabTestConfig | None,
    ) -> LabSpecimenDefaultsResponse:
        if lab_request.test_code and lab_request.test_code in TEST_CODE_SPECIMEN_DEFAULTS:
            return TEST_CODE_SPECIMEN_DEFAULTS[lab_request.test_code]

        catalog = None
        if lab_request.lab_test_catalog_id is not None:
            catalog = (
                self.db.query(LabTestCatalog)
                .filter(LabTestCatalog.id == lab_request.lab_test_catalog_id)
                .first()
            )
        specimen_type = catalog.specimen_type if catalog is not None else None
        specimen_source = specimen_type if specimen_type else None

        if config is not None and config.billing_name:
            if config.billing_name in {"Fasting Blood Sugar (FBS)", "Random Blood Sugar (RBS)"}:
                return LabSpecimenDefaultsResponse(
                    specimen_type=specimen_type or "Blood",
                    specimen_source=specimen_source or "Blood",
                    container_type="Fluoride oxalate / plain tube",
                )

        return LabSpecimenDefaultsResponse(
            specimen_type=specimen_type,
            specimen_source=specimen_source,
        )
