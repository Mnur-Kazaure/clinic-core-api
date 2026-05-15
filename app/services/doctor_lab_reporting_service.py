from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.doctor_lab_reporting import (
    DoctorLabResultAlertResponse,
    DoctorLabResultDetailResponse,
    DoctorLabResultFieldValueResponse,
    DoctorLabResultVersionResponse,
    DoctorLabSpecimenContextResponse,
    DoctorLabVisitResultSummaryResponse,
    DoctorPatientLabHistoryEntryResponse,
)
from app.shared.enums import (
    LabResultFieldType,
    LabResultLifecycleStatus,
    MRNStatus,
)


class DoctorLabReportingService:
    def __init__(self, db: Session):
        self.db = db

    def list_visit_results(
        self,
        *,
        visit: Visit,
    ) -> list[DoctorLabVisitResultSummaryResponse]:
        lab_requests = self._get_visit_requests(visit_id=visit.id)
        if not lab_requests:
            return []

        request_map = {request.id: request for request in lab_requests}
        result_map = self._get_active_released_results_for_requests(
            request_ids=list(request_map.keys())
        )
        if not result_map:
            return []

        request_ids = list(result_map.keys())
        specimen_map = self._get_specimens_by_request(request_ids=request_ids)
        unit_name_map = self._get_unit_names(
            unit_ids=[request.target_unit_id for request in request_map.values()]
        )
        value_rows_map = self._get_value_rows_map(
            result_ids=[result.id for result in result_map.values()]
        )
        alert_count_map = self._get_alert_count_map(
            result_ids=[result.id for result in result_map.values()]
        )
        superseded_ids = self._get_superseded_result_ids(
            result_ids=[result.id for result in result_map.values()]
        )

        summaries: list[DoctorLabVisitResultSummaryResponse] = []
        for request_id, result in result_map.items():
            request = request_map[request_id]
            value_rows = value_rows_map.get(result.id, [])
            specimens = specimen_map.get(request_id, [])
            summaries.append(
                DoctorLabVisitResultSummaryResponse(
                    result_id=result.id,
                    lab_request_id=request.id,
                    request_item_id=result.request_item_id,
                    test_name=request.test_name,
                    test_code=request.test_code,
                    unit_id=request.target_unit_id,
                    unit_name=unit_name_map.get(request.target_unit_id),
                    requested_at=request.created_at,
                    released_at=result.released_at or result.created_at,
                    status=result.status,
                    has_abnormal=any(row.abnormal_flag for row in value_rows),
                    has_critical=any(row.critical_flag for row in value_rows),
                    is_amended=result.amended_from_result_id is not None,
                    is_superseded=result.id in superseded_ids,
                    critical_alert_count=alert_count_map.get(result.id, 0),
                    accession_numbers=[specimen.accession_number for specimen in specimens],
                    specimen_count=len(specimens),
                )
            )

        return sorted(
            summaries,
            key=lambda item: item.released_at,
            reverse=True,
        )

    def get_visit_result_detail(
        self,
        *,
        visit: Visit,
        result_id: UUID,
    ) -> DoctorLabResultDetailResponse:
        result = (
            self.db.query(LabResult)
            .join(LabRequest, LabRequest.id == LabResult.lab_request_id)
            .filter(
                LabResult.id == result_id,
                LabResult.status == LabResultLifecycleStatus.RELEASED,
                LabRequest.visit_id == visit.id,
                LabRequest.clinic_id == visit.clinic_id,
            )
            .first()
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Released lab result not found for this visit",
            )

        request = self._get_request_for_result(result=result)
        patient = self._get_patient(patient_id=visit.patient_id, clinic_id=visit.clinic_id)
        patient_mrn = self._get_active_mrn(patient_id=patient.id, clinic_id=visit.clinic_id)
        specimens = self._get_specimens_by_request(request_ids=[request.id]).get(request.id, [])
        alerts = self._get_alerts_map(result_ids=[result.id]).get(result.id, [])
        value_rows_map = self._get_value_rows_map(result_ids=[result.id])
        value_rows = value_rows_map.get(result.id, [])
        unit_name_map = self._get_unit_names(unit_ids=[request.target_unit_id])
        user_name_map = self._get_user_names(
            user_ids=[
                request.requested_by,
                result.entered_by,
                result.verified_by,
                result.released_by,
            ]
        )

        field_values = self._build_field_values(result=result, value_rows=value_rows)
        version_rows = self._get_request_result_versions(request_id=request.id)
        superseded_ids = {
            row.amended_from_result_id
            for row in version_rows
            if row.amended_from_result_id is not None
        }
        prior_versions = [
            DoctorLabResultVersionResponse(
                result_id=row.id,
                released_at=row.released_at,
                entered_at=row.entered_at,
                status=row.status,
                is_amended=row.amended_from_result_id is not None,
                is_superseded=row.id in superseded_ids,
                amendment_reason=self._get_amendment_reason(row),
            )
            for row in version_rows
            if row.id != result.id
        ]

        has_abnormal = any(value.abnormal_flag for value in field_values)
        has_critical = any(value.critical_flag for value in field_values)
        is_superseded = result.id in superseded_ids

        return DoctorLabResultDetailResponse(
            result_id=result.id,
            visit_id=visit.id,
            patient_id=patient.id,
            patient_name=patient.full_name,
            patient_mrn=patient_mrn,
            test_name=request.test_name,
            test_code=request.test_code,
            unit_id=request.target_unit_id,
            unit_name=unit_name_map.get(request.target_unit_id),
            requested_at=request.created_at,
            status=result.status,
            released_at=result.released_at,
            entered_at=result.entered_at,
            verified_at=result.verified_at,
            entered_by=result.entered_by,
            entered_by_name=user_name_map.get(result.entered_by),
            verified_by=result.verified_by,
            verified_by_name=user_name_map.get(result.verified_by),
            released_by=result.released_by,
            released_by_name=user_name_map.get(result.released_by),
            accession_numbers=[specimen.accession_number for specimen in specimens],
            has_abnormal=has_abnormal,
            has_critical=has_critical,
            is_amended=result.amended_from_result_id is not None,
            is_superseded=is_superseded,
            state_labels=self._build_state_labels(
                is_amended=result.amended_from_result_id is not None,
                is_superseded=is_superseded,
                has_abnormal=has_abnormal,
                has_critical=has_critical,
            ),
            amendment_reason=self._get_amendment_reason(result),
            values=field_values,
            specimens=[
                DoctorLabSpecimenContextResponse(
                    specimen_id=specimen.id,
                    accession_number=specimen.accession_number,
                    specimen_type=specimen.specimen_type,
                    specimen_source=specimen.specimen_source,
                    container_type=specimen.container_type,
                    collection_site=specimen.collection_site,
                    specimen_sequence=specimen.specimen_sequence,
                    specimen_label_suffix=specimen.specimen_label_suffix,
                    status=specimen.status,
                    collected_at=specimen.collected_at,
                    received_at=specimen.received_at,
                )
                for specimen in specimens
            ],
            alerts=[
                DoctorLabResultAlertResponse(
                    alert_id=alert.id,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    status=alert.status,
                    message=alert.message,
                    created_at=alert.created_at,
                    acknowledged_at=alert.acknowledged_at,
                    resolved_at=alert.resolved_at,
                    escalated_at=alert.escalated_at,
                )
                for alert in alerts
            ],
            prior_versions=prior_versions,
            attachments=[],
        )

    def list_patient_history(
        self,
        *,
        patient_id: UUID,
        clinic_id: UUID,
        test_identifier: str,
    ) -> list[DoctorPatientLabHistoryEntryResponse]:
        request_rows = (
            self.db.query(LabRequest)
            .join(Visit, Visit.id == LabRequest.visit_id)
            .filter(
                Visit.patient_id == patient_id,
                Visit.clinic_id == clinic_id,
                func.lower(func.coalesce(LabRequest.test_code, LabRequest.test_name))
                == test_identifier.lower(),
            )
            .order_by(LabRequest.created_at.desc())
            .all()
        )
        if not request_rows:
            return []

        request_map = {request.id: request for request in request_rows}
        active_results = self._get_active_released_results_for_requests(
            request_ids=list(request_map.keys())
        )
        if not active_results:
            return []

        result_ids = [result.id for result in active_results.values()]
        value_rows_map = self._get_value_rows_map(result_ids=result_ids)
        specimen_map = self._get_specimens_by_request(request_ids=list(active_results.keys()))

        history: list[DoctorPatientLabHistoryEntryResponse] = []
        for request_id, result in active_results.items():
            request = request_map[request_id]
            field_values = self._build_field_values(
                result=result,
                value_rows=value_rows_map.get(result.id, []),
            )
            history.append(
                DoctorPatientLabHistoryEntryResponse(
                    result_id=result.id,
                    visit_id=request.visit_id,
                    released_at=result.released_at or result.created_at,
                    test_name=request.test_name,
                    test_code=request.test_code,
                    has_abnormal=any(value.abnormal_flag for value in field_values),
                    has_critical=any(value.critical_flag for value in field_values),
                    is_amended=result.amended_from_result_id is not None,
                    accession_numbers=[
                        specimen.accession_number
                        for specimen in specimen_map.get(request_id, [])
                    ],
                    values=field_values,
                )
            )

        return sorted(history, key=lambda item: item.released_at, reverse=True)

    def _get_visit_requests(self, *, visit_id: UUID) -> list[LabRequest]:
        return (
            self.db.query(LabRequest)
            .filter(LabRequest.visit_id == visit_id)
            .order_by(LabRequest.created_at.desc())
            .all()
        )

    def _get_active_released_results_for_requests(
        self,
        *,
        request_ids: list[UUID],
    ) -> dict[UUID, LabResult]:
        if not request_ids:
            return {}

        released_results = (
            self.db.query(LabResult)
            .filter(
                LabResult.lab_request_id.in_(request_ids),
                LabResult.status == LabResultLifecycleStatus.RELEASED,
            )
            .order_by(LabResult.released_at.desc().nullslast(), LabResult.created_at.desc())
            .all()
        )
        if not released_results:
            return {}

        superseded_ids = {
            result.amended_from_result_id
            for result in released_results
            if result.amended_from_result_id is not None
        }

        active_map: dict[UUID, LabResult] = {}
        for result in released_results:
            request_id = result.request_item_id or result.lab_request_id
            if result.id in superseded_ids:
                continue
            if request_id not in active_map:
                active_map[request_id] = result
        return active_map

    def _get_value_rows_map(
        self,
        *,
        result_ids: list[UUID],
    ) -> dict[UUID, list[LabResultValue]]:
        if not result_ids:
            return {}
        rows = (
            self.db.query(LabResultValue)
            .filter(LabResultValue.result_id.in_(result_ids))
            .all()
        )
        result: dict[UUID, list[LabResultValue]] = defaultdict(list)
        for row in rows:
            result[row.result_id].append(row)
        return result

    def _get_specimens_by_request(
        self,
        *,
        request_ids: list[UUID],
    ) -> dict[UUID, list[LabSpecimen]]:
        if not request_ids:
            return {}
        rows = (
            self.db.query(LabSpecimen)
            .filter(LabSpecimen.request_item_id.in_(request_ids))
            .order_by(
                LabSpecimen.specimen_sequence.asc(),
                LabSpecimen.created_at.asc(),
            )
            .all()
        )
        result: dict[UUID, list[LabSpecimen]] = defaultdict(list)
        for row in rows:
            result[row.request_item_id].append(row)
        return result

    def _get_alert_count_map(self, *, result_ids: list[UUID]) -> dict[UUID, int]:
        if not result_ids:
            return {}
        rows = (
            self.db.query(
                LabCriticalAlert.result_id,
                func.count(LabCriticalAlert.id),
            )
            .filter(
                LabCriticalAlert.result_id.in_(result_ids),
            )
            .group_by(LabCriticalAlert.result_id)
            .all()
        )
        return {result_id: count for result_id, count in rows if result_id is not None}

    def _get_alerts_map(
        self,
        *,
        result_ids: list[UUID],
    ) -> dict[UUID, list[LabCriticalAlert]]:
        if not result_ids:
            return {}
        rows = (
            self.db.query(LabCriticalAlert)
            .filter(LabCriticalAlert.result_id.in_(result_ids))
            .order_by(LabCriticalAlert.created_at.asc())
            .all()
        )
        result: dict[UUID, list[LabCriticalAlert]] = defaultdict(list)
        for row in rows:
            if row.result_id is not None:
                result[row.result_id].append(row)
        return result

    def _get_superseded_result_ids(self, *, result_ids: list[UUID]) -> set[UUID]:
        if not result_ids:
            return set()
        rows = (
            self.db.query(LabResult.amended_from_result_id)
            .filter(
                LabResult.amended_from_result_id.in_(result_ids),
                LabResult.status == LabResultLifecycleStatus.RELEASED,
            )
            .all()
        )
        return {row[0] for row in rows if row[0] is not None}

    def _get_unit_names(self, *, unit_ids: list[UUID | None]) -> dict[UUID, str]:
        filtered_ids = [unit_id for unit_id in unit_ids if unit_id is not None]
        if not filtered_ids:
            return {}
        rows = (
            self.db.query(ServiceLine.id, ServiceLine.name)
            .filter(ServiceLine.id.in_(filtered_ids))
            .all()
        )
        return {unit_id: name for unit_id, name in rows}

    def _get_user_names(self, *, user_ids: list[UUID | None]) -> dict[UUID, str]:
        filtered_ids = [user_id for user_id in user_ids if user_id is not None]
        if not filtered_ids:
            return {}
        rows = (
            self.db.query(User.id, User.full_name)
            .filter(User.id.in_(filtered_ids))
            .all()
        )
        return {user_id: full_name for user_id, full_name in rows if full_name}

    def _get_request_for_result(self, *, result: LabResult) -> LabRequest:
        request_id = result.request_item_id or result.lab_request_id
        row = self.db.query(LabRequest).filter(LabRequest.id == request_id).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab request not found for result",
            )
        return row

    def _get_request_result_versions(self, *, request_id: UUID) -> list[LabResult]:
        return (
            self.db.query(LabResult)
            .filter(
                func.coalesce(LabResult.request_item_id, LabResult.lab_request_id) == request_id,
                LabResult.status == LabResultLifecycleStatus.RELEASED,
            )
            .order_by(LabResult.released_at.asc().nullslast(), LabResult.created_at.asc())
            .all()
        )

    def _get_patient(self, *, patient_id: UUID, clinic_id: UUID) -> Patient:
        patient = (
            self.db.query(Patient)
            .filter(
                Patient.id == patient_id,
                Patient.clinic_id == clinic_id,
            )
            .first()
        )
        if patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )
        return patient

    def _get_active_mrn(self, *, patient_id: UUID, clinic_id: UUID) -> str | None:
        row = (
            self.db.query(PatientMRN.mrn)
            .filter(
                PatientMRN.patient_id == patient_id,
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .order_by(PatientMRN.issued_at.desc())
            .first()
        )
        return row[0] if row else None

    def _build_field_values(
        self,
        *,
        result: LabResult,
        value_rows: list[LabResultValue],
    ) -> list[DoctorLabResultFieldValueResponse]:
        if result.template_id is None:
            return [
                DoctorLabResultFieldValueResponse(
                    template_field_id=None,
                    field_code="legacy_result",
                    field_name="Result",
                    field_type=LabResultFieldType.TEXT,
                    unit=result.result_unit,
                    reference_range_text=result.reference_range,
                    reference_min=None,
                    reference_max=None,
                    reference_unit=result.result_unit,
                    options_json=None,
                    value_string=result.result_value,
                    value_number=None,
                    value_boolean=None,
                    value_json=None,
                    abnormal_flag=False,
                    critical_flag=False,
                )
            ]

        field_ids = [row.template_field_id for row in value_rows]
        field_rows = (
            self.db.query(LabResultTemplateField)
            .filter(LabResultTemplateField.id.in_(field_ids))
            .order_by(LabResultTemplateField.display_order.asc())
            .all()
        )
        value_map = {row.template_field_id: row for row in value_rows}

        result_values: list[DoctorLabResultFieldValueResponse] = []
        for field in field_rows:
            row = value_map.get(field.id)
            if row is None:
                continue
            result_values.append(
                DoctorLabResultFieldValueResponse(
                    template_field_id=field.id,
                    field_code=field.field_code,
                    field_name=field.field_name,
                    field_type=field.field_type,
                    unit=field.unit,
                    reference_range_text=field.reference_range_text,
                    reference_min=self._coerce_number(field.reference_min),
                    reference_max=self._coerce_number(field.reference_max),
                    reference_unit=field.reference_unit,
                    options_json=field.options_json,
                    value_string=row.value_string,
                    value_number=self._coerce_number(row.value_number),
                    value_boolean=row.value_boolean,
                    value_json=row.value_json,
                    abnormal_flag=row.abnormal_flag,
                    critical_flag=row.critical_flag,
                )
            )
        return result_values

    def _build_state_labels(
        self,
        *,
        is_amended: bool,
        is_superseded: bool,
        has_abnormal: bool,
        has_critical: bool,
    ) -> list[str]:
        labels = ["Released"]
        if is_amended:
            labels.append("Amended")
        if is_superseded:
            labels.append("Superseded")
        if has_critical:
            labels.append("Critical")
        elif has_abnormal:
            labels.append("Abnormal")
        return labels

    def _get_amendment_reason(self, result: LabResult) -> str | None:
        if result.amended_from_result_id is None:
            return None
        return result.void_reason

    def _coerce_number(self, value: Decimal | float | int | None) -> float | None:
        if value is None:
            return None
        return float(value)
