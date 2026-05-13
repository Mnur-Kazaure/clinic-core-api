import base64
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.admission import Admission
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.patient_mrn import PatientMRN
from app.models.prescription import Prescription
from app.models.visit import Visit
from app.services.access_log_service import AccessLogService
from app.shared.enums import MRNStatus, VisitStatus, AdmissionStatus, UserRole


class PMRService:
    def __init__(self, db: Session):
        self.db = db

    def get_pmr(
        self,
        *,
        patient_id: UUID,
        clinic_id: UUID,
        actor,
        purpose_of_use,
        justification: str,
        limit: int = 20,
        cursor: str | None = None,
        detail_level: str | None = None,
        break_glass: bool,
    ) -> dict:
        requested_patient = self._get_patient(patient_id, clinic_id)
        try:
            canonical_id = self._resolve_canonical_patient_id(
                patient_id=requested_patient.id,
                clinic_id=clinic_id,
            )
        except HTTPException as exc:
            AccessLogService(self.db).log_pmr_read(
                actor=actor,
                clinic_id=clinic_id,
                patient_id_requested=requested_patient.id,
                patient_id_canonical=requested_patient.id,
                purpose_of_use=purpose_of_use,
                justification=justification,
                break_glass=break_glass,
                extra_payload={"error": "IDENTITY_MAP_CYCLE_DETECTED"},
            )
            raise exc

        closure_ids = self._resolve_identity_closure(
            canonical_id=canonical_id,
            clinic_id=clinic_id,
        )

        effective_detail_level = "SUMMARY"
        detail_level_downgraded = False
        if detail_level and detail_level != "SUMMARY":
            # v1.1.1 is summary-first; any non-SUMMARY request is downgraded.
            detail_level_downgraded = True

        authorized = self._is_authorized(actor, closure_ids)
        if not authorized and not break_glass:
            # Keep the denial actionable for clinicians; reception is handled in _is_authorized.
            detail = (
                "PMR access requires an active visit assigned to you"
                if actor.role == UserRole.DOCTOR
                else "PMR access denied"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )

        access_log = AccessLogService(self.db).log_pmr_read(
            actor=actor,
            clinic_id=clinic_id,
            patient_id_requested=requested_patient.id,
            patient_id_canonical=canonical_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            break_glass=break_glass,
        )

        canonical_patient = self._get_patient(canonical_id, clinic_id)
        active_mrn = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == canonical_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .first()
        )
        retired_mrns = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id.in_(closure_ids),
                PatientMRN.status == MRNStatus.RETIRED,
            )
            .order_by(PatientMRN.retired_at.desc().nullslast())
            .all()
        )

        visits_page, visits_has_more, visits_next_cursor = self._get_paged_visits(
            clinic_id=clinic_id,
            identity_closure_ids=closure_ids,
            limit=limit,
            cursor=cursor,
        )

        admissions = (
            self.db.query(Admission)
            .filter(
                Admission.clinic_id == clinic_id,
                Admission.patient_id.in_(closure_ids),
            )
            .order_by(Admission.admitted_at.desc())
            .all()
        )

        clinical_history = self._build_clinical_history(
            clinic_id=clinic_id,
            visits=visits_page,
        )

        return {
            "patient_id_requested": requested_patient.id,
            "patient_id_canonical": canonical_id,
            "access_log_id": access_log.id,
            "identity_state": canonical_patient.identity_state.value
            if hasattr(canonical_patient.identity_state, "value")
            else canonical_patient.identity_state,
            "full_name": canonical_patient.full_name,
            "date_of_birth": canonical_patient.date_of_birth,
            "gender": canonical_patient.gender,
            "phone_number": canonical_patient.phone_number,
            "address": canonical_patient.address,
            "occupation": canonical_patient.occupation,
            "active_mrn": active_mrn,
            "retired_mrns": retired_mrns,
            "identity_closure_ids": closure_ids,
            "visits": visits_page,
            "admissions": admissions,
            "effective_detail_level": effective_detail_level,
            "detail_level_downgraded": detail_level_downgraded,
            "clinical_history_page": {
                "limit": limit,
                "next_cursor": visits_next_cursor,
                "has_more": visits_has_more,
                "generated_at": datetime.now(timezone.utc),
            },
            "clinical_history": clinical_history,
        }

    def _get_patient(self, patient_id: UUID, clinic_id: UUID) -> Patient:
        patient = (
            self.db.query(Patient)
            .filter(
                Patient.id == patient_id,
                Patient.clinic_id == clinic_id,
            )
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    def _encode_cursor(self, *, started_at: datetime, visit_id: UUID) -> str:
        payload = {
            "started_at": started_at.isoformat(),
            "visit_id": str(visit_id),
        }
        return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    def _decode_cursor(self, cursor: str) -> tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
            data = json.loads(raw)
            started_at = datetime.fromisoformat(data["started_at"])
            visit_id = UUID(str(data["visit_id"]))
            return started_at, visit_id
        except Exception as exc:  # noqa: BLE001 - explicit validation for external input
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor",
            ) from exc

    def _get_paged_visits(
        self,
        *,
        clinic_id: UUID,
        identity_closure_ids: list[UUID],
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Visit], bool, str | None]:
        q = (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.patient_id.in_(identity_closure_ids),
            )
            .order_by(Visit.started_at.desc(), Visit.id.desc())
        )

        if cursor:
            cursor_started_at, cursor_visit_id = self._decode_cursor(cursor)
            q = q.filter(
                (Visit.started_at < cursor_started_at)
                | ((Visit.started_at == cursor_started_at) & (Visit.id < cursor_visit_id))
            )

        rows = q.limit(limit + 1).all()
        has_more = len(rows) > limit
        visits = rows[:limit]
        next_cursor = None
        if has_more and visits:
            last = visits[-1]
            next_cursor = self._encode_cursor(started_at=last.started_at, visit_id=last.id)
        return visits, has_more, next_cursor

    def _truncate_preview(self, text: str | None, max_len: int = 200) -> tuple[str | None, bool]:
        if not text:
            return None, False
        cleaned = text.strip()
        if len(cleaned) <= max_len:
            return cleaned, False
        return cleaned[:max_len], True

    def _build_clinical_history(self, *, clinic_id: UUID, visits: list[Visit]) -> list[dict]:
        if not visits:
            return []

        visit_ids = [v.id for v in visits]

        consultations = (
            self.db.query(Consultation)
            .filter(
                Consultation.clinic_id == clinic_id,
                Consultation.visit_id.in_(visit_ids),
            )
            .all()
        )
        consultation_by_visit = {c.visit_id: c for c in consultations}

        prescriptions = (
            self.db.query(Prescription)
            .filter(
                Prescription.clinic_id == clinic_id,
                Prescription.visit_id.in_(visit_ids),
            )
            .order_by(Prescription.issued_at.desc(), Prescription.id.desc())
            .all()
        )
        prescriptions_by_visit: dict[UUID, list[Prescription]] = {}
        for p in prescriptions:
            prescriptions_by_visit.setdefault(p.visit_id, []).append(p)

        lab_requests = (
            self.db.query(LabRequest)
            .filter(
                LabRequest.clinic_id == clinic_id,
                LabRequest.visit_id.in_(visit_ids),
            )
            .order_by(LabRequest.created_at.desc(), LabRequest.id.desc())
            .all()
        )
        lab_requests_by_visit: dict[UUID, list[LabRequest]] = {}
        lab_request_ids = []
        for lr in lab_requests:
            lab_requests_by_visit.setdefault(lr.visit_id, []).append(lr)
            lab_request_ids.append(lr.id)

        lab_results_by_request: dict[UUID, list[LabResult]] = {}
        if lab_request_ids:
            lab_results = (
                self.db.query(LabResult)
                .filter(
                    LabResult.clinic_id == clinic_id,
                    LabResult.lab_request_id.in_(lab_request_ids),
                )
                .order_by(LabResult.created_at.desc(), LabResult.id.desc())
                .all()
            )
            for r in lab_results:
                lab_results_by_request.setdefault(r.lab_request_id, []).append(r)

        history: list[dict] = []
        for v in visits:
            consult = consultation_by_visit.get(v.id)
            if consult:
                pc_preview, _ = self._truncate_preview(consult.presenting_complaints)
                dx_preview, _ = self._truncate_preview(consult.diagnosis)
                note_preview_text, note_trunc = self._truncate_preview(consult.notes)
                consult_section = {
                    "exists": True,
                    "missing_reason": None,
                    "item": {
                        "consultation_id": consult.id,
                        "created_at": consult.started_at,
                        "completed_at": consult.completed_at,
                        "clinician_id": consult.doctor_id,
                        "presenting_complaint_preview": pc_preview,
                        "diagnosis_summary": dx_preview,
                        "plan_preview": None,
                        "note_preview": {
                            "text": note_preview_text,
                            "max_len": 200,
                            "truncated": note_trunc,
                        },
                    },
                }
            else:
                consult_section = {
                    "exists": False,
                    "missing_reason": "NO_DATA",
                    "item": None,
                }

            presc_items = []
            for p in prescriptions_by_visit.get(v.id, []):
                presc_items.append(
                    {
                        "prescription_id": p.id,
                        "created_at": p.issued_at,
                        "clinician_id": p.prescribed_by,
                        "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                        "drugs": [
                            {
                                "name": p.drug_name,
                                "dose": p.dosage,
                                "frequency": p.frequency,
                                "duration": p.duration,
                            }
                        ],
                    }
                )
            prescriptions_section = {
                "exists": bool(presc_items),
                "missing_reason": None if presc_items else "NO_DATA",
                "count": len(presc_items),
                "items": presc_items,
            }

            lab_request_items = []
            for lr in lab_requests_by_visit.get(v.id, []):
                results = lab_results_by_request.get(lr.id, [])
                results_summary = []
                for r in results:
                    results_summary.append(
                        {
                            "test_name": lr.test_name,
                            "value": r.result_value,
                            "unit": r.result_unit,
                            "reference_range": r.reference_range,
                        }
                    )
                lab_request_items.append(
                    {
                        "lab_request_id": lr.id,
                        "created_at": lr.created_at,
                        "ordered_by_id": lr.requested_by,
                        "status": lr.status.value if hasattr(lr.status, "value") else str(lr.status),
                        "tests": [
                            {
                                "code": None,
                                "name": lr.test_name,
                            }
                        ],
                        "special_instructions": lr.special_instructions,
                        "results_available": bool(results),
                        "results_summary": results_summary,
                    }
                )
            labs_section = {
                "exists": bool(lab_request_items),
                "missing_reason": None if lab_request_items else "NO_DATA",
                "count": len(lab_request_items),
                "requests": lab_request_items,
            }

            history.append(
                {
                    "visit_id": v.id,
                    "visit_status": v.status,
                    "visit_started_at": v.started_at,
                    "visit_closed_at": v.completed_at,
                    "assigned_doctor_id": v.assigned_doctor_id,
                    "sections": {
                        "consultation": consult_section,
                        "prescriptions": prescriptions_section,
                        "labs": labs_section,
                    },
                }
            )
        return history

    def _resolve_canonical_patient_id(self, *, patient_id: UUID, clinic_id: UUID) -> UUID:
        visited = set()
        current = patient_id
        for _ in range(10):
            if current in visited:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Identity mapping cycle detected",
                )
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity resolution exceeded hop limit",
        )

    def _resolve_identity_closure(self, *, canonical_id: UUID, clinic_id: UUID) -> list[UUID]:
        seen = {canonical_id}
        queue = [canonical_id]
        while queue:
            target = queue.pop()
            mappings = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.to_patient_id == target,
                )
                .all()
            )
            for mapping in mappings:
                revoked = (
                    self.db.query(IdentityMapRevocation)
                    .filter(
                        IdentityMapRevocation.clinic_id == clinic_id,
                        IdentityMapRevocation.map_id == mapping.id,
                    )
                    .first()
                )
                if revoked:
                    continue
                if mapping.from_patient_id not in seen:
                    seen.add(mapping.from_patient_id)
                    queue.append(mapping.from_patient_id)
        return list(seen)

    def _has_active_context(self, *, clinic_id: UUID, identity_closure_ids: list[UUID]) -> bool:
        active_visit = (
            self.db.query(Visit)
            .filter(
                Visit.clinic_id == clinic_id,
                Visit.patient_id.in_(identity_closure_ids),
                Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
            )
            .first()
        )
        if active_visit:
            return True
        active_admission = (
            self.db.query(Admission)
            .filter(
                Admission.clinic_id == clinic_id,
                Admission.patient_id.in_(identity_closure_ids),
                Admission.status == AdmissionStatus.ACTIVE,
            )
            .first()
        )
        return active_admission is not None

    def _is_authorized(self, actor, identity_closure_ids: list[UUID]) -> bool:
        if actor.role in {UserRole.CLINIC_ADMIN, UserRole.CMD}:
            return True
        if actor.role == UserRole.RECEPTION:
            # Reception/records officers may view PMR for any patient in their clinic (audit logged).
            return True
        if actor.role in {UserRole.DOCTOR, UserRole.CHEW, UserRole.MIDWIFE}:
            # Clinicians may view SUMMARY-only PMR only for patients in an active visit
            # assigned to them. This supports ANC/maternity continuity without granting
            # clinic-wide PMR access.
            active_visits = (
                self.db.query(Visit)
                .filter(
                    Visit.clinic_id == actor.clinic_id,
                    Visit.patient_id.in_(identity_closure_ids),
                    Visit.assigned_doctor_id == actor.id,
                    Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
                )
                .count()
            )
            return active_visits > 0
        return False
