from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_critical_alert_event import LabCriticalAlertEvent
from app.models.lab_qc_result import LabQcResult
from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.lab_test_config import LabTestConfig
from app.models.visit import Visit
from app.schemas.lab_safety import (
    LabResultAmendCreate,
    LabQcResultCreate,
    LabQcRunCreate,
    LabResultReleaseRequest,
    StructuredLabResultCreate,
)
from app.shared.enums import (
    LabCriticalAlertEventType,
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabCriticalAlertType,
    LabQcStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    LabVerificationPolicy,
    RecordStatus,
    UserRole,
)
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_foundation_service import LabFoundationService
from app.services.event_service import EventService
from app.services.lab_role_access_service import LabRoleAccessService


RESULT_ENTRY_ALLOWED_SPECIMEN_STATUSES = {
    LabSpecimenStatus.RECEIVED,
    LabSpecimenStatus.IN_PROCESS,
}


class LabSafetyService:
    def __init__(self, db: Session):
        self.db = db
        self.foundation_service = LabFoundationService(db)
        self.event_service = EventService(db)
        self.role_access = LabRoleAccessService(db)

    def submit_structured_result(
        self,
        *,
        lab_request: LabRequest,
        actor_id: UUID,
        payload: StructuredLabResultCreate,
    ) -> LabResult:
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_enter_result(actor=actor)

        existing_active_result = (
            self.db.query(LabResult.id)
            .filter(
                LabResult.request_item_id == lab_request.id,
                LabResult.status.in_(
                    (
                        LabResultLifecycleStatus.DRAFT,
                        LabResultLifecycleStatus.SUBMITTED,
                        LabResultLifecycleStatus.VERIFIED,
                        LabResultLifecycleStatus.RELEASED,
                    )
                ),
            )
            .first()
        )
        if existing_active_result is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active structured result already exists for this lab request",
            )

        if not BillingWorkflowService(self.db).is_lab_request_paid(lab_request=lab_request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab access denied until payment is verified",
            )

        specimen_exists = (
            self.db.query(LabSpecimen.id)
            .filter(
                LabSpecimen.request_item_id == lab_request.id,
                LabSpecimen.status.in_(tuple(status.value for status in RESULT_ENTRY_ALLOWED_SPECIMEN_STATUSES)),
            )
            .first()
        )
        if specimen_exists is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Structured result entry requires a received specimen",
            )

        template_data = self.foundation_service.get_request_template(lab_request=lab_request)
        template_id = template_data["id"]
        template_version = template_data["version"]
        template_fields: list[LabResultTemplateField] = template_data["fields"]
        field_map = {field.id: field for field in template_fields}

        provided_field_ids = [item.template_field_id for item in payload.values]
        if len(set(provided_field_ids)) != len(provided_field_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Each template field may only be submitted once per result",
            )

        for field_id in provided_field_ids:
            if field_id not in field_map:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Result contains values for fields outside the configured template",
                )

        required_field_ids = {
            field.id for field in template_fields if field.is_required
        }
        missing_required = required_field_ids - set(provided_field_ids)
        if missing_required:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One or more required result fields are missing",
            )

        config = self._get_test_config(lab_request=lab_request)
        verification_policy = (
            config.verification_policy if config else LabVerificationPolicy.OPTIONAL
        )
        visit = self._get_visit_for_request(lab_request=lab_request)
        now = datetime.now(timezone.utc)

        result = LabResult(
            lab_request_id=lab_request.id,
            request_item_id=lab_request.id,
            clinic_id=lab_request.clinic_id,
            technician_id=actor_id,
            template_id=template_id,
            template_version=template_version,
            status=LabResultLifecycleStatus.SUBMITTED,
            entered_by=actor_id,
            entered_at=now,
            result_value=self._build_summary_text(payload=payload, field_map=field_map),
            result_unit=None,
            reference_range=None,
            record_status=RecordStatus.DRAFT,
        )
        self.db.add(result)
        self.db.flush()

        critical_alert_count = 0
        for item in payload.values:
            field = field_map[item.template_field_id]
            abnormal_flag = self._is_abnormal(field=field, payload_item=item)
            critical_rule = self._resolve_critical_rule(field=field, config=config)
            critical_flag, severity, message = self._is_critical(
                field=field,
                payload_item=item,
                rule=critical_rule,
            )

            value_row = LabResultValue(
                result_id=result.id,
                template_field_id=field.id,
                value_string=item.value_string,
                value_number=item.value_number,
                value_boolean=item.value_boolean,
                value_json=item.value_json,
                abnormal_flag=abnormal_flag,
                critical_flag=critical_flag,
            )
            self.db.add(value_row)
            self.db.flush()

            if critical_flag:
                critical_alert_count += 1
                self._create_critical_result_alert(
                    result=result,
                    result_value=value_row,
                    lab_request=lab_request,
                    visit=visit,
                    field=field,
                    severity=severity or LabCriticalAlertSeverity.CRITICAL,
                    message=message
                    or f"Critical lab result: {field.field_name} for {lab_request.test_name}",
                )

        lab_request.workflow_status = LabRequestWorkflowStatus.RESULT_ENTERED
        self.db.add(lab_request)
        self._append_lab_audit_event(
            event_type="LAB_RESULT_ENTERED",
            actor=actor,
            visit=visit,
            unit_id=lab_request.target_unit_id,
            request_item_id=lab_request.id,
            result_id=result.id,
            metadata_json={
                "template_id": str(template_id),
                "template_version": template_version,
                "status": result.status.value,
            },
        )
        self._append_lab_audit_event(
            event_type="LAB_RESULT_SUBMITTED",
            actor=actor,
            visit=visit,
            unit_id=lab_request.target_unit_id,
            request_item_id=lab_request.id,
            result_id=result.id,
            metadata_json={
                "template_id": str(template_id),
                "template_version": template_version,
                "critical_alert_count": critical_alert_count,
                "status": result.status.value,
            },
        )
        self.db.commit()
        self.db.refresh(result)
        result._verification_policy = verification_policy
        result._critical_alert_count = critical_alert_count
        result._value_rows = self._list_result_values(result_id=result.id)
        return result

    def verify_result(self, *, result_id: UUID, clinic_id: UUID, actor_id: UUID) -> LabResult:
        result = self._get_result(result_id=result_id, clinic_id=clinic_id)
        actor = self.role_access.get_actor(actor_id=actor_id)
        lab_request = self._get_request_for_result(result=result)
        config = self._get_test_config(lab_request=lab_request)
        verification_policy = (
            config.verification_policy if config else LabVerificationPolicy.OPTIONAL
        )
        value_rows = self._list_result_values(result_id=result.id)
        has_critical = any(row.critical_flag for row in value_rows)
        self.role_access.assert_can_verify_result(
            actor=actor,
            result=result,
            config=config,
            has_critical=has_critical,
        )
        if result.status == LabResultLifecycleStatus.RELEASED:
            result._verification_policy = verification_policy
            result._critical_alert_count = self._count_result_alerts(result_id=result.id)
            result._value_rows = value_rows
            return result
        if result.status == LabResultLifecycleStatus.VERIFIED:
            result._verification_policy = verification_policy
            result._critical_alert_count = self._count_result_alerts(result_id=result.id)
            result._value_rows = value_rows
            return result
        if result.status not in {
            LabResultLifecycleStatus.SUBMITTED,
            LabResultLifecycleStatus.DRAFT,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft or submitted results may be verified",
            )

        result.status = LabResultLifecycleStatus.VERIFIED
        result.verified_by = actor_id
        result.verified_at = datetime.now(timezone.utc)

        lab_request.workflow_status = LabRequestWorkflowStatus.VERIFIED
        self.db.add_all([result, lab_request])
        self._append_lab_audit_event(
            event_type="LAB_RESULT_VERIFIED",
            actor=actor,
            visit=self._get_visit_for_request(lab_request=lab_request),
            unit_id=lab_request.target_unit_id,
            request_item_id=lab_request.id,
            result_id=result.id,
            metadata_json={
                "verification_policy": verification_policy.value,
                "critical_result": has_critical,
                "verified_status": result.status.value,
            },
        )
        self.db.commit()
        self.db.refresh(result)
        result._verification_policy = verification_policy
        result._critical_alert_count = self._count_result_alerts(result_id=result.id)
        result._value_rows = value_rows
        return result

    def release_result(
        self,
        *,
        result_id: UUID,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabResultReleaseRequest | None = None,
    ) -> LabResult:
        result = self._get_result(result_id=result_id, clinic_id=clinic_id)
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_release_result(actor=actor)
        if result.status == LabResultLifecycleStatus.RELEASED:
            return result
        if result.status == LabResultLifecycleStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rejected results cannot be released",
            )

        lab_request = self._get_request_for_result(result=result)
        config = self._get_test_config(lab_request=lab_request)
        verification_policy = (
            config.verification_policy if config else LabVerificationPolicy.OPTIONAL
        )
        value_rows = self._list_result_values(result_id=result.id)
        has_abnormal = any(row.abnormal_flag for row in value_rows)
        has_critical = any(row.critical_flag for row in value_rows)
        qc_override_reason = payload.qc_override_reason.strip() if payload and payload.qc_override_reason else None

        verification_required = self.role_access.requires_verification(
            verification_policy=verification_policy,
            has_abnormal=has_abnormal,
            has_critical=has_critical,
        )
        if has_critical:
            if result.status != LabResultLifecycleStatus.VERIFIED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Critical results require supervisor verification before release",
                )
            verifier = self.role_access.get_actor(actor_id=result.verified_by) if result.verified_by else None
            if verifier is None or verifier.role != UserRole.LAB_SUPERVISOR:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Critical results require supervisor verification before release",
                )
        if verification_required and result.status != LabResultLifecycleStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verification is required before this result can be released",
            )
        if result.status not in {
            LabResultLifecycleStatus.SUBMITTED,
            LabResultLifecycleStatus.VERIFIED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only submitted or verified results may be released",
            )

        blocking_qc_failures = self._get_blocking_qc_failures(
            lab_request=lab_request,
            result=result,
            value_rows=value_rows,
        )
        if blocking_qc_failures and not qc_override_reason:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="QC failure blocks release for this result scope until a supervisor override is recorded",
            )
        if blocking_qc_failures and qc_override_reason:
            self.role_access.assert_can_override_qc(actor=actor)
            self._append_lab_audit_event(
                event_type="LAB_QC_OVERRIDE",
                actor=actor,
                visit=self._get_visit_for_request(lab_request=lab_request),
                unit_id=lab_request.target_unit_id,
                request_item_id=lab_request.id,
                result_id=result.id,
                metadata_json={
                    "override_reason": qc_override_reason,
                    "blocking_analytes": [row.analyte_name for row in blocking_qc_failures],
                    "qc_run_ids": [str(row.qc_run_id) for row in blocking_qc_failures],
                },
            )

        result.status = LabResultLifecycleStatus.RELEASED
        result.released_by = actor_id
        result.released_at = datetime.now(timezone.utc)
        result.record_status = RecordStatus.SIGNED
        result.signed_at = result.released_at

        lab_request.workflow_status = LabRequestWorkflowStatus.RELEASED
        self.db.add_all([result, lab_request])

        alerts = (
            self.db.query(LabCriticalAlert)
            .filter(
                LabCriticalAlert.result_id == result.id,
                LabCriticalAlert.alert_type == LabCriticalAlertType.CRITICAL_RESULT,
            )
            .all()
        )
        for alert in alerts:
            if alert.status == LabCriticalAlertStatus.CREATED:
                alert.status = LabCriticalAlertStatus.DELIVERED
                self.db.add(alert)
                self._append_alert_event(
                    alert=alert,
                    event_type=LabCriticalAlertEventType.DELIVERED,
                    actor_id=actor_id,
                    notes="Critical alert delivered with released result",
                    metadata_json=None,
                )

        self._append_lab_audit_event(
            event_type="LAB_RESULT_RELEASED",
            actor=actor,
            visit=self._get_visit_for_request(lab_request=lab_request),
            unit_id=lab_request.target_unit_id,
            request_item_id=lab_request.id,
            result_id=result.id,
            metadata_json={
                "verification_policy": verification_policy.value,
                "critical_result": has_critical,
                "abnormal_result": has_abnormal,
                "qc_override": bool(qc_override_reason),
            },
        )
        self.db.commit()
        self.db.refresh(result)
        result._verification_policy = verification_policy
        result._critical_alert_count = len(alerts)
        result._value_rows = value_rows
        return result

    def list_result_alerts(self, *, result_id: UUID, clinic_id: UUID) -> list[LabCriticalAlert]:
        self._get_result(result_id=result_id, clinic_id=clinic_id)
        return (
            self.db.query(LabCriticalAlert)
            .filter(LabCriticalAlert.result_id == result_id)
            .order_by(LabCriticalAlert.created_at.asc())
            .all()
        )

    def amend_result(
        self,
        *,
        result_id: UUID,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabResultAmendCreate,
    ) -> LabResult:
        original = self._get_result(result_id=result_id, clinic_id=clinic_id)
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_amend_result(actor=actor)
        if original.status != LabResultLifecycleStatus.RELEASED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only released results may be amended",
            )
        if original.entered_by == actor_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Result amendment requires separation of duties",
            )

        lab_request = self._get_request_for_result(result=original)
        config = self._get_test_config(lab_request=lab_request)
        verification_policy = (
            config.verification_policy if config else LabVerificationPolicy.OPTIONAL
        )
        template_data = self.foundation_service.get_request_template(lab_request=lab_request)
        template_id = template_data["id"]
        template_version = template_data["version"]
        template_fields: list[LabResultTemplateField] = template_data["fields"]
        field_map = {field.id: field for field in template_fields}
        provided_field_ids = [item.template_field_id for item in payload.values]
        if len(set(provided_field_ids)) != len(provided_field_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Each template field may only be submitted once per amendment",
            )
        required_field_ids = {
            field.id for field in template_fields if field.is_required
        }
        if required_field_ids - set(provided_field_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="One or more required result fields are missing",
            )
        for field_id in provided_field_ids:
            if field_id not in field_map:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Amendment contains values for fields outside the configured template",
                )

        visit = self._get_visit_for_request(lab_request=lab_request)
        now = datetime.now(timezone.utc)
        amended = LabResult(
            lab_request_id=original.lab_request_id,
            request_item_id=original.request_item_id,
            clinic_id=original.clinic_id,
            technician_id=original.technician_id,
            template_id=template_id,
            template_version=template_version,
            status=LabResultLifecycleStatus.RELEASED,
            amended_from_result_id=original.id,
            amendment_reason=payload.amendment_reason.strip(),
            entered_by=original.entered_by,
            entered_at=original.entered_at,
            verified_by=actor_id,
            verified_at=now,
            released_by=actor_id,
            released_at=now,
            result_value=self._build_summary_text(payload=payload, field_map=field_map),
            result_unit=original.result_unit,
            reference_range=original.reference_range,
            record_status=RecordStatus.SIGNED,
            signed_at=now,
        )
        self.db.add(amended)
        self.db.flush()

        critical_alert_count = 0
        for item in payload.values:
            field = field_map[item.template_field_id]
            abnormal_flag = self._is_abnormal(field=field, payload_item=item)
            critical_rule = self._resolve_critical_rule(field=field, config=config)
            critical_flag, severity, message = self._is_critical(
                field=field,
                payload_item=item,
                rule=critical_rule,
            )
            value_row = LabResultValue(
                result_id=amended.id,
                template_field_id=field.id,
                value_string=item.value_string,
                value_number=item.value_number,
                value_boolean=item.value_boolean,
                value_json=item.value_json,
                abnormal_flag=abnormal_flag,
                critical_flag=critical_flag,
            )
            self.db.add(value_row)
            self.db.flush()
            if critical_flag:
                critical_alert_count += 1
                self._create_critical_result_alert(
                    result=amended,
                    result_value=value_row,
                    lab_request=lab_request,
                    visit=visit,
                    field=field,
                    severity=severity or LabCriticalAlertSeverity.CRITICAL,
                    message=message
                    or f"Critical lab result amendment: {field.field_name} for {lab_request.test_name}",
                )

        original.record_status = RecordStatus.AMENDED
        self.db.add(original)
        self._append_lab_audit_event(
            event_type="LAB_RESULT_AMENDED",
            actor=actor,
            visit=visit,
            unit_id=lab_request.target_unit_id,
            request_item_id=lab_request.id,
            result_id=amended.id,
            metadata_json={
                "amended_from_result_id": str(original.id),
                "amendment_reason": amended.amendment_reason,
                "critical_alert_count": critical_alert_count,
            },
        )
        self.db.commit()
        self.db.refresh(amended)
        amended._verification_policy = verification_policy
        amended._critical_alert_count = critical_alert_count
        amended._value_rows = self._list_result_values(result_id=amended.id)
        return amended

    def create_qc_run(
        self,
        *,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabQcRunCreate,
        expected_unit_id: UUID | None = None,
    ) -> LabQcRun:
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_enter_qc(actor=actor)
        if expected_unit_id is not None and payload.unit_id != expected_unit_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected lab unit does not match the QC run unit",
            )
        qc_run = LabQcRun(
            clinic_id=clinic_id,
            unit_id=payload.unit_id,
            machine_id=payload.machine_id,
            qc_level=payload.qc_level.strip(),
            performed_by=actor_id,
            status=LabQcStatus.PASS,
            notes=payload.notes.strip() if payload.notes else None,
        )
        self.db.add(qc_run)
        self.db.commit()
        self.db.refresh(qc_run)
        return qc_run

    def record_qc_result(
        self,
        *,
        qc_run_id: UUID,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabQcResultCreate,
        expected_unit_id: UUID | None = None,
    ) -> LabQcResult:
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_enter_qc(actor=actor)
        qc_run = (
            self.db.query(LabQcRun)
            .filter(
                LabQcRun.id == qc_run_id,
                LabQcRun.clinic_id == clinic_id,
            )
            .first()
        )
        if qc_run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QC run not found",
            )
        if expected_unit_id is not None and qc_run.unit_id != expected_unit_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Selected lab unit does not match this QC run",
            )

        qc_status = self._determine_qc_status(
            expected_min=payload.expected_min,
            expected_max=payload.expected_max,
            observed_value=payload.observed_value,
        )
        qc_result = LabQcResult(
            qc_run_id=qc_run.id,
            analyte_name=payload.analyte_name.strip(),
            expected_min=payload.expected_min,
            expected_max=payload.expected_max,
            observed_value=payload.observed_value,
            status=qc_status,
        )
        self.db.add(qc_result)
        self.db.flush()

        all_statuses = [
            row.status
            for row in self.db.query(LabQcResult)
            .filter(LabQcResult.qc_run_id == qc_run.id)
            .all()
        ]
        all_statuses.append(qc_status)
        qc_run.status = self._worst_qc_status(all_statuses)
        self.db.add(qc_run)

        if qc_status == LabQcStatus.FAIL:
            alert = LabCriticalAlert(
                result_id=None,
                result_value_id=None,
                request_item_id=None,
                visit_id=None,
                patient_id=None,
                unit_id=qc_run.unit_id,
                alert_type=LabCriticalAlertType.QC_FAILURE,
                severity=LabCriticalAlertSeverity.HIGH,
                message=f"QC failure detected for {payload.analyte_name.strip()}",
                target_role="LAB_SUPERVISOR",
                target_user_id=None,
                status=LabCriticalAlertStatus.CREATED,
            )
            self.db.add(alert)
            self.db.flush()
            self._append_alert_event(
                alert=alert,
                event_type=LabCriticalAlertEventType.CREATED,
                actor_id=actor_id,
                notes="QC failure alert created",
                metadata_json={
                    "qc_run_id": str(qc_run.id),
                    "qc_result_id": str(qc_result.id),
                },
            )

        self.db.commit()
        self.db.refresh(qc_result)
        return qc_result

    def _get_request_for_result(self, *, result: LabResult) -> LabRequest:
        request_id = result.request_item_id or result.lab_request_id
        lab_request = self.db.query(LabRequest).filter(LabRequest.id == request_id).first()
        if lab_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab request not found for result",
            )
        return lab_request

    def _get_result(self, *, result_id: UUID, clinic_id: UUID) -> LabResult:
        result = (
            self.db.query(LabResult)
            .filter(
                LabResult.id == result_id,
                LabResult.clinic_id == clinic_id,
            )
            .first()
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab result not found",
            )
        return result

    def _get_test_config(self, *, lab_request: LabRequest) -> LabTestConfig | None:
        lab_request, _ = self.foundation_service.reconcile_request_configuration(
            lab_request=lab_request,
            auto_commit=True,
        )
        if lab_request.lab_test_config_id is None:
            return None
        return (
            self.db.query(LabTestConfig)
            .filter(LabTestConfig.id == lab_request.lab_test_config_id)
            .first()
        )

    def _get_visit_for_request(self, *, lab_request: LabRequest) -> Visit:
        visit = self.db.query(Visit).filter(Visit.id == lab_request.visit_id).first()
        if visit is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Visit not found for lab request",
            )
        return visit

    def _list_result_values(self, *, result_id: UUID) -> list[LabResultValue]:
        return (
            self.db.query(LabResultValue)
            .filter(LabResultValue.result_id == result_id)
            .order_by(LabResultValue.created_at.asc())
            .all()
        )

    def _count_result_alerts(self, *, result_id: UUID) -> int:
        return (
            self.db.query(LabCriticalAlert.id)
            .filter(LabCriticalAlert.result_id == result_id)
            .count()
        )

    def _build_summary_text(
        self,
        *,
        payload: StructuredLabResultCreate,
        field_map: dict[UUID, LabResultTemplateField],
    ) -> str:
        summaries: list[str] = []
        for item in payload.values[:3]:
            field = field_map[item.template_field_id]
            value = (
                item.value_string
                if item.value_string is not None
                else item.value_number
                if item.value_number is not None
                else item.value_boolean
                if item.value_boolean is not None
                else "json"
            )
            summaries.append(f"{field.field_name}: {value}")
        return "; ".join(str(part) for part in summaries)

    def _is_abnormal(self, *, field: LabResultTemplateField, payload_item) -> bool:
        if payload_item.value_number is None:
            return False
        min_value = self._as_float(field.reference_min)
        max_value = self._as_float(field.reference_max)
        if min_value is not None and payload_item.value_number < min_value:
            return True
        if max_value is not None and payload_item.value_number > max_value:
            return True
        return False

    def _resolve_critical_rule(
        self,
        *,
        field: LabResultTemplateField,
        config: LabTestConfig | None,
    ) -> dict | None:
        base_rule = (
            dict(field.critical_rules_json)
            if isinstance(field.critical_rules_json, dict)
            else None
        )
        override_rule = None
        rules = config.critical_rules_json if config else None
        if isinstance(rules, dict):
            if field.field_code in rules and isinstance(rules[field.field_code], dict):
                override_rule = dict(rules[field.field_code])
            elif isinstance(rules.get("fields"), dict) and isinstance(
                rules["fields"].get(field.field_code), dict
            ):
                override_rule = dict(rules["fields"][field.field_code])
            elif "critical_low" in rules or "critical_high" in rules or "critical_equals" in rules:
                override_rule = dict(rules)
        elif isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict) and rule.get("field_code") == field.field_code:
                    override_rule = dict(rule)
                    break

        if base_rule is None and override_rule is None:
            return None
        merged = {}
        if base_rule:
            merged.update(base_rule)
        if override_rule:
            merged.update(override_rule)
        return merged

    def _is_critical(
        self,
        *,
        field: LabResultTemplateField,
        payload_item,
        rule: dict | None,
    ) -> tuple[bool, LabCriticalAlertSeverity | None, str | None]:
        if not rule:
            return False, None, None

        severity = None
        if rule.get("severity"):
            severity = LabCriticalAlertSeverity(rule["severity"])

        if payload_item.value_number is not None:
            critical_low = self._coerce_number(rule.get("critical_low"))
            critical_high = self._coerce_number(rule.get("critical_high"))
            value = payload_item.value_number
            if critical_low is not None and value < critical_low:
                return True, severity, rule.get("message")
            if critical_high is not None and value > critical_high:
                return True, severity, rule.get("message")

        if payload_item.value_string is not None and rule.get("critical_equals") is not None:
            equals_rule = rule["critical_equals"]
            expected_values = (
                equals_rule if isinstance(equals_rule, list) else [equals_rule]
            )
            if payload_item.value_string in expected_values:
                return True, severity, rule.get("message")

        return False, None, None

    def _get_blocking_qc_failures(
        self,
        *,
        lab_request: LabRequest,
        result: LabResult,
        value_rows: list[LabResultValue],
    ) -> list[LabQcResult]:
        if lab_request.target_unit_id is None:
            return []

        analyte_keys: set[str] = set()
        field_ids = [row.template_field_id for row in value_rows if row.template_field_id is not None]
        if field_ids:
            template_fields = (
                self.db.query(LabResultTemplateField)
                .filter(LabResultTemplateField.id.in_(field_ids))
                .all()
            )
            for field in template_fields:
                analyte_keys.add(field.field_name.strip().lower())
                analyte_keys.add(field.field_code.strip().lower())

        if result.result_value:
            analyte_keys.add(lab_request.test_name.strip().lower())

        if not analyte_keys:
            return []

        qc_rows = (
            self.db.query(LabQcResult, LabQcRun)
            .join(LabQcRun, LabQcRun.id == LabQcResult.qc_run_id)
            .filter(
                LabQcRun.clinic_id == lab_request.clinic_id,
                LabQcRun.unit_id == lab_request.target_unit_id,
            )
            .order_by(LabQcResult.analyte_name.asc(), LabQcRun.performed_at.desc())
            .all()
        )
        latest_by_analyte: dict[str, tuple[LabQcResult, LabQcRun]] = {}
        for qc_result, qc_run in qc_rows:
            key = qc_result.analyte_name.strip().lower()
            if key not in latest_by_analyte:
                latest_by_analyte[key] = (qc_result, qc_run)

        blocking: list[LabQcResult] = []
        for analyte_key in analyte_keys:
            row = latest_by_analyte.get(analyte_key)
            if row is None:
                continue
            qc_result, _ = row
            if qc_result.status == LabQcStatus.FAIL:
                blocking.append(qc_result)
        return blocking

    def _append_lab_audit_event(
        self,
        *,
        event_type: str,
        actor,
        visit: Visit | None,
        unit_id: UUID | None,
        request_item_id: UUID | None = None,
        specimen_id: UUID | None = None,
        result_id: UUID | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        payload = {
            "user_id": str(actor.user.id),
            "role": actor.role.value,
            "action_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "unit_id": str(unit_id) if unit_id else None,
            "request_item_id": str(request_item_id) if request_item_id else None,
            "specimen_id": str(specimen_id) if specimen_id else None,
            "result_id": str(result_id) if result_id else None,
            "metadata_json": metadata_json or {},
        }
        self.event_service.build_event(
            event_type=event_type,
            actor_id=actor.user.id,
            actor_role=actor.role.value,
            clinic_id=actor.user.clinic_id,
            patient_id=visit.patient_id if visit else None,
            emitter="lab",
            payload=payload,
        )

    def _create_critical_result_alert(
        self,
        *,
        result: LabResult,
        result_value: LabResultValue,
        lab_request: LabRequest,
        visit: Visit,
        field: LabResultTemplateField,
        severity: LabCriticalAlertSeverity,
        message: str,
    ) -> None:
        alert = LabCriticalAlert(
            result_id=result.id,
            result_value_id=result_value.id,
            request_item_id=lab_request.id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            unit_id=lab_request.target_unit_id,
            alert_type=LabCriticalAlertType.CRITICAL_RESULT,
            severity=severity,
            message=message,
            target_role="DOCTOR",
            target_user_id=visit.assigned_doctor_id,
            status=LabCriticalAlertStatus.CREATED,
        )
        self.db.add(alert)
        self.db.flush()
        self._append_alert_event(
            alert=alert,
            event_type=LabCriticalAlertEventType.CREATED,
            actor_id=result.entered_by,
            notes=f"Critical alert created for {field.field_name}",
            metadata_json={"result_value_id": str(result_value.id)},
        )

    def _append_alert_event(
        self,
        *,
        alert: LabCriticalAlert,
        event_type: LabCriticalAlertEventType,
        actor_id: UUID | None,
        notes: str | None,
        metadata_json,
    ) -> None:
        self.db.add(
            LabCriticalAlertEvent(
                alert_id=alert.id,
                event_type=event_type,
                performed_by=actor_id,
                performed_at=datetime.now(timezone.utc),
                notes=notes,
                metadata_json=metadata_json,
            )
        )

    def _determine_qc_status(
        self,
        *,
        expected_min: float | None,
        expected_max: float | None,
        observed_value: float,
    ) -> LabQcStatus:
        if expected_min is None and expected_max is None:
            return LabQcStatus.WARNING
        if expected_min is not None and observed_value < expected_min:
            return LabQcStatus.FAIL
        if expected_max is not None and observed_value > expected_max:
            return LabQcStatus.FAIL
        return LabQcStatus.PASS

    def _worst_qc_status(self, statuses: list[LabQcStatus]) -> LabQcStatus:
        if any(status == LabQcStatus.FAIL for status in statuses):
            return LabQcStatus.FAIL
        if any(status == LabQcStatus.WARNING for status in statuses):
            return LabQcStatus.WARNING
        return LabQcStatus.PASS

    def _coerce_number(self, value) -> float | None:
        if value is None:
            return None
        if isinstance(value, (float, int)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _as_float(self, value) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
