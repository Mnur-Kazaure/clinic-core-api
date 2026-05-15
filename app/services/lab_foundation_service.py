from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.lab_request import LabRequest
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_specimen import LabSpecimen
from app.models.lab_specimen_event import LabSpecimenEvent
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.schemas.lab_foundation import LabSpecimenCreate, LabSpecimenEventCreate
from app.shared.enums import (
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabSpecimenEventType,
    LabSpecimenRejectionReasonCode,
    LabSpecimenStatus,
)
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.event_service import EventService
from app.services.lab_role_access_service import LabRoleAccessService


SPECIMEN_CREATE_ALLOWED_STATUSES = {
    LabSpecimenStatus.PENDING_COLLECTION,
    LabSpecimenStatus.COLLECTED,
    LabSpecimenStatus.RECEIVED,
}


class LabFoundationService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.role_access = LabRoleAccessService(db)

    def resolve_catalog_config_for_order(
        self,
        *,
        clinic_id: UUID,
        test_name: str,
        test_code: str | None,
    ) -> tuple[LabTestCatalog | None, LabTestConfig | None]:
        query = (
            self.db.query(LabTestCatalog, LabTestConfig)
            .join(
                LabTestConfig,
                LabTestConfig.catalog_test_id == LabTestCatalog.id,
            )
            .filter(
                LabTestCatalog.clinic_id == clinic_id,
                LabTestCatalog.is_active.is_(True),
                LabTestConfig.clinic_id == clinic_id,
                LabTestConfig.is_enabled.is_(True),
            )
        )

        if test_code:
            row = query.filter(LabTestCatalog.test_code == test_code.strip()).first()
            if row is not None:
                return row

        normalized_name = test_name.strip().lower()
        row = query.filter(
            or_(
                func.lower(LabTestCatalog.test_name) == normalized_name,
                func.lower(LabTestConfig.billing_name) == normalized_name,
            )
        ).first()
        if row is not None:
            return row
        return None, None

    def reconcile_request_configuration(
        self,
        *,
        lab_request: LabRequest,
        auto_commit: bool = False,
    ) -> tuple[LabRequest, bool]:
        changed = False

        catalog = None
        if lab_request.lab_test_catalog_id is not None:
            catalog = (
                self.db.query(LabTestCatalog)
                .filter(LabTestCatalog.id == lab_request.lab_test_catalog_id)
                .first()
            )

        config = None
        if lab_request.lab_test_config_id is not None:
            config = (
                self.db.query(LabTestConfig)
                .filter(LabTestConfig.id == lab_request.lab_test_config_id)
                .first()
            )

        if catalog is None and config is not None:
            catalog = (
                self.db.query(LabTestCatalog)
                .filter(LabTestCatalog.id == config.catalog_test_id)
                .first()
            )
        if config is None and catalog is not None:
            config = (
                self.db.query(LabTestConfig)
                .filter(
                    LabTestConfig.clinic_id == lab_request.clinic_id,
                    LabTestConfig.catalog_test_id == catalog.id,
                    LabTestConfig.is_enabled.is_(True),
                )
                .first()
            )

        if catalog is None or config is None or lab_request.target_unit_id is None:
            resolved_catalog, resolved_config = self.resolve_catalog_config_for_order(
                clinic_id=lab_request.clinic_id,
                test_name=lab_request.test_name,
                test_code=lab_request.test_code,
            )
            catalog = catalog or resolved_catalog
            config = config or resolved_config

        if catalog is not None and lab_request.lab_test_catalog_id != catalog.id:
            lab_request.lab_test_catalog_id = catalog.id
            changed = True
        if config is not None and lab_request.lab_test_config_id != config.id:
            lab_request.lab_test_config_id = config.id
            changed = True

        desired_unit_id = (
            config.unit_id
            if config is not None
            else catalog.unit_id
            if catalog is not None
            else None
        )
        if desired_unit_id is not None and lab_request.target_unit_id is None:
            lab_request.target_unit_id = desired_unit_id
            changed = True

        if changed:
            self.db.add(lab_request)
            self.db.flush()
            if auto_commit:
                self.db.commit()
                self.db.refresh(lab_request)

        return lab_request, changed

    def reconcile_request_configuration_for_clinic(
        self,
        *,
        clinic_id: UUID,
    ) -> int:
        lab_requests = (
            self.db.query(LabRequest)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.status == LabRequestStatus.PENDING,
                or_(
                    LabRequest.lab_test_catalog_id.is_(None),
                    LabRequest.lab_test_config_id.is_(None),
                    LabRequest.target_unit_id.is_(None),
                ),
            )
            .all()
        )

        repaired = 0
        for lab_request in lab_requests:
            _, changed = self.reconcile_request_configuration(
                lab_request=lab_request,
                auto_commit=False,
            )
            repaired += int(changed)

        if repaired:
            self.db.commit()

        return repaired

    def get_request_template(self, *, lab_request: LabRequest) -> dict:
        lab_request, _ = self.reconcile_request_configuration(
            lab_request=lab_request,
            auto_commit=True,
        )

        template_id = None
        if lab_request.lab_test_catalog_id is not None:
            catalog = (
                self.db.query(LabTestCatalog)
                .filter(LabTestCatalog.id == lab_request.lab_test_catalog_id)
                .first()
            )
            template_id = catalog.default_template_id if catalog else None

        if template_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No result template configured for this lab request",
            )

        return self.get_template_by_id(template_id=template_id)

    def get_template_by_id(self, *, template_id: UUID) -> dict:
        template = (
            self.db.query(LabResultTemplate)
            .filter(LabResultTemplate.id == template_id)
            .first()
        )
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Result template not found",
            )

        fields = (
            self.db.query(LabResultTemplateField)
            .filter(LabResultTemplateField.template_id == template.id)
            .order_by(LabResultTemplateField.display_order.asc())
            .all()
        )
        return {
            "id": template.id,
            "code": template.code,
            "name": template.name,
            "result_type": template.result_type,
            "version": template.version,
            "description": template.description,
            "is_active": template.is_active,
            "fields": fields,
        }

    def list_specimens_for_request(self, *, lab_request_id: UUID) -> list[LabSpecimen]:
        return (
            self.db.query(LabSpecimen)
            .filter(LabSpecimen.request_item_id == lab_request_id)
            .order_by(
                LabSpecimen.specimen_sequence.asc(),
                LabSpecimen.created_at.asc(),
            )
            .all()
        )

    def create_specimen(
        self,
        *,
        lab_request: LabRequest,
        actor_id: UUID,
        payload: LabSpecimenCreate,
    ) -> LabSpecimen:
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_handle_specimen(actor=actor)
        if not BillingWorkflowService(self.db).is_lab_request_paid(lab_request=lab_request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab access denied until payment is verified",
            )

        if payload.status not in SPECIMEN_CREATE_ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Specimen can only be created in pending, collected, or received state",
            )

        target_unit_id = payload.target_unit_id or lab_request.target_unit_id
        if target_unit_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Target lab unit is required before specimen creation",
            )
        if lab_request.target_unit_id is not None and target_unit_id != lab_request.target_unit_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Specimen unit must remain aligned with the routed lab request unit",
            )

        self._lock_clinic_row(clinic_id=lab_request.clinic_id)
        accession_number = self._generate_accession_number(clinic_id=lab_request.clinic_id)
        now = datetime.now(timezone.utc)

        collected_by = None
        collected_at = payload.collected_at
        received_by = None
        received_at = payload.received_at
        if payload.status in {LabSpecimenStatus.COLLECTED, LabSpecimenStatus.RECEIVED}:
            collected_by = actor_id
            collected_at = collected_at or now
        if payload.status == LabSpecimenStatus.RECEIVED:
            received_by = actor_id
            received_at = received_at or now

        specimen = LabSpecimen(
            clinic_id=lab_request.clinic_id,
            accession_number=accession_number,
            request_item_id=lab_request.id,
            target_unit_id=target_unit_id,
            specimen_type=payload.specimen_type.strip(),
            specimen_source=payload.specimen_source.strip(),
            container_type=payload.container_type.strip() if payload.container_type else None,
            collection_site=payload.collection_site.strip() if payload.collection_site else None,
            specimen_sequence=payload.specimen_sequence,
            specimen_label_suffix=payload.specimen_label_suffix.strip()
            if payload.specimen_label_suffix
            else None,
            collected_by=collected_by,
            collected_at=collected_at,
            received_by=received_by,
            received_at=received_at,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        self.db.add(specimen)
        self.db.flush()

        self._append_specimen_event(
            specimen=specimen,
            event_type=LabSpecimenEventType.CREATED,
            actor_id=actor_id,
            notes="Specimen accession created",
            metadata_json={"accession_number": accession_number},
            performed_at=now,
        )
        if payload.status in {LabSpecimenStatus.COLLECTED, LabSpecimenStatus.RECEIVED}:
            self._append_specimen_event(
                specimen=specimen,
                event_type=LabSpecimenEventType.COLLECTED,
                actor_id=actor_id,
                notes="Specimen collected at creation",
                metadata_json=None,
                performed_at=collected_at or now,
            )
        if payload.status == LabSpecimenStatus.RECEIVED:
            self._append_specimen_event(
                specimen=specimen,
                event_type=LabSpecimenEventType.RECEIVED,
                actor_id=actor_id,
                notes="Specimen received at creation",
                metadata_json=None,
                performed_at=received_at or now,
            )
        if payload.print_label:
            self._append_specimen_event(
                specimen=specimen,
                event_type=LabSpecimenEventType.LABEL_PRINTED,
                actor_id=actor_id,
                notes="Specimen label marked for print",
                metadata_json=None,
                performed_at=now,
            )

        if lab_request.workflow_status in {
            LabRequestWorkflowStatus.ORDERED,
            LabRequestWorkflowStatus.PAID,
        }:
            lab_request.workflow_status = LabRequestWorkflowStatus.AWAITING_SPECIMEN
            self.db.add(lab_request)

        self.db.commit()
        self.db.refresh(specimen)
        return specimen

    def record_specimen_event(
        self,
        *,
        specimen_id: UUID,
        clinic_id: UUID,
        actor_id: UUID,
        payload: LabSpecimenEventCreate,
    ) -> LabSpecimenEvent:
        actor = self.role_access.get_actor(actor_id=actor_id)
        self.role_access.assert_can_handle_specimen(actor=actor)
        specimen = (
            self.db.query(LabSpecimen)
            .filter(
                LabSpecimen.id == specimen_id,
                LabSpecimen.clinic_id == clinic_id,
            )
            .first()
        )
        if specimen is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Specimen not found",
            )

        request_item = (
            self.db.query(LabRequest)
            .filter(LabRequest.id == specimen.request_item_id)
            .first()
        )
        if request_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab request not found for specimen",
            )

        performed_at = payload.performed_at or datetime.now(timezone.utc)

        if payload.event_type == LabSpecimenEventType.CREATED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Specimen creation event is system-managed",
            )
        if payload.event_type == LabSpecimenEventType.COLLECTED:
            if specimen.status != LabSpecimenStatus.PENDING_COLLECTION:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only pending specimens can be marked collected",
                )
            specimen.status = LabSpecimenStatus.COLLECTED
            specimen.collected_by = actor_id
            specimen.collected_at = performed_at
        elif payload.event_type == LabSpecimenEventType.RECEIVED:
            if specimen.status not in {
                LabSpecimenStatus.PENDING_COLLECTION,
                LabSpecimenStatus.COLLECTED,
            }:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only pending or collected specimens can be marked received",
                )
            if specimen.collected_at is None:
                specimen.collected_by = specimen.collected_by or actor_id
                specimen.collected_at = performed_at
            specimen.status = LabSpecimenStatus.RECEIVED
            specimen.received_by = actor_id
            specimen.received_at = performed_at
        elif payload.event_type == LabSpecimenEventType.ROUTED_TO_UNIT:
            if payload.target_unit_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Target unit is required when routing a specimen",
                )
            if payload.target_unit_id != specimen.target_unit_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Specimen rerouting is not enabled in the current sealed workflow",
                )
        elif payload.event_type == LabSpecimenEventType.REJECTED:
            if specimen.status in {LabSpecimenStatus.DISPOSED, LabSpecimenStatus.LOST}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Disposed or lost specimens cannot be rejected",
                )
            if payload.rejection_reason_code is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Structured rejection reason is required",
                )
            self.role_access.assert_can_reject_specimen(
                actor=actor,
                reason_code=payload.rejection_reason_code,
            )
            specimen.status = LabSpecimenStatus.REJECTED
            specimen.rejection_reason_code = payload.rejection_reason_code
            specimen.rejection_reason_text = payload.rejection_reason_text
            specimen.rejected_by = actor_id
            specimen.rejected_at = performed_at
            request_item.workflow_status = LabRequestWorkflowStatus.AWAITING_SPECIMEN
        elif payload.event_type == LabSpecimenEventType.RECOLLECTION_REQUESTED:
            request_item.workflow_status = LabRequestWorkflowStatus.AWAITING_SPECIMEN
        elif payload.event_type == LabSpecimenEventType.LOST:
            specimen.status = LabSpecimenStatus.LOST
        elif payload.event_type == LabSpecimenEventType.ANALYSIS_STARTED:
            if specimen.status != LabSpecimenStatus.RECEIVED:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only received specimens can start analysis",
                )
            specimen.status = LabSpecimenStatus.IN_PROCESS
            request_item.workflow_status = LabRequestWorkflowStatus.IN_ANALYSIS
        elif payload.event_type == LabSpecimenEventType.ANALYSIS_COMPLETED:
            if specimen.status != LabSpecimenStatus.IN_PROCESS:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only in-process specimens can complete analysis",
                )
        elif payload.event_type == LabSpecimenEventType.DISPOSED:
            if specimen.status not in {
                LabSpecimenStatus.IN_PROCESS,
                LabSpecimenStatus.REJECTED,
                LabSpecimenStatus.LOST,
                LabSpecimenStatus.RECEIVED,
            }:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Specimen cannot be disposed from its current state",
                )
            specimen.status = LabSpecimenStatus.DISPOSED
        elif payload.event_type == LabSpecimenEventType.LABEL_PRINTED:
            pass

        specimen.updated_at = performed_at
        self.db.add(specimen)
        self.db.add(request_item)
        if payload.event_type == LabSpecimenEventType.REJECTED:
            self._append_lab_audit_event(
                event_type="LAB_SPECIMEN_REJECTED",
                actor=actor,
                patient_id=None,
                unit_id=specimen.target_unit_id,
                request_item_id=request_item.id,
                specimen_id=specimen.id,
                metadata_json={
                    "rejection_reason_code": specimen.rejection_reason_code.value
                    if specimen.rejection_reason_code
                    else None,
                    "rejection_reason_text": specimen.rejection_reason_text,
                },
            )
        event = self._append_specimen_event(
            specimen=specimen,
            event_type=payload.event_type,
            actor_id=actor_id,
            notes=payload.notes,
            metadata_json=payload.metadata_json,
            performed_at=performed_at,
        )
        self.db.commit()
        self.db.refresh(event)
        return event

    def _append_specimen_event(
        self,
        *,
        specimen: LabSpecimen,
        event_type: LabSpecimenEventType,
        actor_id: UUID,
        notes: str | None,
        metadata_json,
        performed_at: datetime,
    ) -> LabSpecimenEvent:
        event = LabSpecimenEvent(
            specimen_id=specimen.id,
            event_type=event_type,
            performed_by=actor_id,
            performed_at=performed_at,
            notes=notes,
            metadata_json=metadata_json,
        )
        self.db.add(event)
        return event

    def _append_lab_audit_event(
        self,
        *,
        event_type: str,
        actor,
        patient_id: UUID | None,
        unit_id: UUID | None,
        request_item_id: UUID | None,
        specimen_id: UUID | None,
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
            "metadata_json": metadata_json or {},
        }
        self.event_service.build_event(
            event_type=event_type,
            actor_id=actor.user.id,
            actor_role=actor.role.value,
            clinic_id=actor.user.clinic_id,
            patient_id=patient_id,
            emitter="lab",
            payload=payload,
        )

    def _generate_accession_number(self, *, clinic_id: UUID) -> str:
        date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"LAB-{date_prefix}-"
        last_specimen = (
            self.db.query(LabSpecimen)
            .filter(
                LabSpecimen.accession_number.like(f"{prefix}%"),
            )
            .order_by(LabSpecimen.accession_number.desc())
            .first()
        )
        sequence = 1
        if last_specimen is not None:
            sequence = int(last_specimen.accession_number.rsplit("-", 1)[-1]) + 1
        return f"{prefix}{sequence:05d}"

    def _lock_clinic_row(self, *, clinic_id: UUID) -> None:
        clinic = (
            self.db.query(Clinic)
            .filter(Clinic.id == clinic_id)
            .with_for_update()
            .first()
        )
        if clinic is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clinic not found",
            )
