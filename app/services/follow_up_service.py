import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admission import Admission
from app.models.chronic_recall import ChronicRecall
from app.models.condition_profile import ConditionProfile
from app.models.diagnosis_condition_map import DiagnosisConditionMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.patient_identity_map import PatientIdentityMap
from app.models.visit import Visit
from app.services.access_log_service import AccessLogService
from app.shared.enums import (
    AdmissionDischargeDisposition,
    AdmissionStatus,
    RecallSuggestionConfidence,
    UserRole,
    VisitStatus,
)


STRUCTURED_DIAGNOSIS_PATTERN = re.compile(
    r"\b(?P<system>ICD10|ICPC2|LOCAL)\s*[:\-]\s*(?P<code>[A-Z0-9.]+)\b",
    re.IGNORECASE,
)


class FollowUpConfigurationService:
    def __init__(self, db: Session):
        self.db = db
        self.access_log_service = AccessLogService(db)

    def list_condition_profiles(self, *, clinic_id: UUID, actor) -> list[ConditionProfile]:
        self._ensure_clinic_admin(actor)
        profiles = (
            self.db.query(ConditionProfile)
            .filter(ConditionProfile.clinic_id == clinic_id)
            .order_by(ConditionProfile.display_name.asc())
            .all()
        )
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification="Condition profile list",
            resource="CONDITION_PROFILE",
            action="READ",
        )
        return profiles

    def create_condition_profile(self, *, clinic_id: UUID, actor, payload) -> ConditionProfile:
        self._ensure_clinic_admin(actor)
        profile = ConditionProfile(
            clinic_id=clinic_id,
            code=payload.code,
            display_name=payload.display_name,
            recall_enabled=payload.recall_enabled,
            default_interval_value=payload.default_interval_value,
            default_interval_unit=payload.default_interval_unit,
            default_priority=payload.default_priority,
            cooldown_days=payload.cooldown_days,
            keyword_synonyms=payload.keyword_synonyms,
            created_by=actor.id,
        )
        self.db.add(profile)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Condition profile already exists for this clinic",
            ) from exc
        self.db.refresh(profile)
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification=payload.justification,
            resource="CONDITION_PROFILE",
            action="WRITE",
            extra_payload={
                "condition_profile_id": str(profile.id),
                "operation": "CREATE",
            },
        )
        return profile

    def update_condition_profile(
        self,
        *,
        clinic_id: UUID,
        profile_id: UUID,
        actor,
        payload,
    ) -> ConditionProfile:
        self._ensure_clinic_admin(actor)
        profile = (
            self.db.query(ConditionProfile)
            .filter(
                ConditionProfile.id == profile_id,
                ConditionProfile.clinic_id == clinic_id,
            )
            .first()
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Condition profile not found")

        if payload.display_name is not None:
            profile.display_name = payload.display_name
        if payload.recall_enabled is not None:
            profile.recall_enabled = payload.recall_enabled
        if payload.default_interval_value is not None:
            profile.default_interval_value = payload.default_interval_value
        if payload.default_interval_unit is not None:
            profile.default_interval_unit = payload.default_interval_unit
        if payload.default_priority is not None:
            profile.default_priority = payload.default_priority
        if payload.cooldown_days is not None:
            profile.cooldown_days = payload.cooldown_days
        if payload.keyword_synonyms is not None:
            profile.keyword_synonyms = payload.keyword_synonyms

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Condition profile conflicts with existing clinic record",
            ) from exc
        self.db.refresh(profile)
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification=payload.justification,
            resource="CONDITION_PROFILE",
            action="WRITE",
            extra_payload={
                "condition_profile_id": str(profile.id),
                "operation": "UPDATE",
            },
        )
        return profile

    def list_diagnosis_mappings(self, *, clinic_id: UUID, actor) -> list[DiagnosisConditionMap]:
        self._ensure_clinic_admin(actor)
        rows = (
            self.db.query(DiagnosisConditionMap)
            .filter(DiagnosisConditionMap.clinic_id == clinic_id)
            .order_by(
                DiagnosisConditionMap.active.desc(),
                DiagnosisConditionMap.diagnosis_system.asc(),
                DiagnosisConditionMap.diagnosis_code.asc(),
            )
            .all()
        )
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification="Diagnosis mapping list",
            resource="CONDITION_PROFILE",
            action="READ",
        )
        return rows

    def create_diagnosis_mapping(
        self,
        *,
        clinic_id: UUID,
        actor,
        payload,
    ) -> DiagnosisConditionMap:
        self._ensure_clinic_admin(actor)
        profile_exists = (
            self.db.query(ConditionProfile.id)
            .filter(
                ConditionProfile.id == payload.condition_profile_id,
                ConditionProfile.clinic_id == clinic_id,
            )
            .first()
        )
        if profile_exists is None:
            raise HTTPException(status_code=404, detail="Condition profile not found")

        mapping = DiagnosisConditionMap(
            clinic_id=clinic_id,
            diagnosis_system=payload.diagnosis_system,
            diagnosis_code=payload.diagnosis_code,
            condition_profile_id=payload.condition_profile_id,
            confidence=payload.confidence,
            active=True,
            created_by=actor.id,
        )
        self.db.add(mapping)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active diagnosis mapping already exists for this code",
            ) from exc
        self.db.refresh(mapping)
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification=payload.justification,
            resource="CONDITION_PROFILE",
            action="WRITE",
            extra_payload={
                "diagnosis_mapping_id": str(mapping.id),
                "operation": "CREATE_MAPPING",
            },
        )
        return mapping

    def set_mapping_active(
        self,
        *,
        clinic_id: UUID,
        mapping_id: UUID,
        actor,
        active: bool,
        justification: str,
    ) -> DiagnosisConditionMap:
        self._ensure_clinic_admin(actor)
        mapping = (
            self.db.query(DiagnosisConditionMap)
            .filter(
                DiagnosisConditionMap.id == mapping_id,
                DiagnosisConditionMap.clinic_id == clinic_id,
            )
            .first()
        )
        if mapping is None:
            raise HTTPException(status_code=404, detail="Diagnosis mapping not found")

        mapping.active = active
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to update diagnosis mapping active state",
            ) from exc
        self.db.refresh(mapping)
        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            purpose_of_use="OPERATIONS",
            justification=justification,
            resource="CONDITION_PROFILE",
            action="WRITE",
            extra_payload={
                "diagnosis_mapping_id": str(mapping.id),
                "operation": "SET_MAPPING_ACTIVE",
                "active": active,
            },
        )
        return mapping

    def _ensure_clinic_admin(self, actor) -> None:
        role_value = getattr(actor.role, "value", actor.role)
        if role_value != UserRole.CLINIC_ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinic Admin access required",
            )


class RecallSuggestionService:
    def __init__(self, db: Session):
        self.db = db

    def resolve(
        self,
        *,
        clinic_id: UUID,
        patient_id: UUID,
        diagnosis_text: str | None,
    ) -> list[dict]:
        if not diagnosis_text or not diagnosis_text.strip():
            return []

        profile_candidates: dict[UUID, tuple[ConditionProfile, RecallSuggestionConfidence]] = {}

        structured_codes = self._extract_structured_codes(diagnosis_text)
        if structured_codes:
            rows = (
                self.db.query(DiagnosisConditionMap, ConditionProfile)
                .join(
                    ConditionProfile,
                    (ConditionProfile.id == DiagnosisConditionMap.condition_profile_id)
                    & (ConditionProfile.clinic_id == DiagnosisConditionMap.clinic_id),
                )
                .filter(
                    DiagnosisConditionMap.clinic_id == clinic_id,
                    DiagnosisConditionMap.active.is_(True),
                    ConditionProfile.recall_enabled.is_(True),
                )
                .all()
            )
            structured_lookup = {(system, code) for system, code in structured_codes}
            for mapping, profile in rows:
                key = (mapping.diagnosis_system.value, mapping.diagnosis_code.upper())
                if key not in structured_lookup:
                    continue
                profile_candidates[profile.id] = (
                    profile,
                    RecallSuggestionConfidence.HIGH,
                )
        else:
            diagnosis_lower = diagnosis_text.lower()
            rows = (
                self.db.query(ConditionProfile)
                .filter(
                    ConditionProfile.clinic_id == clinic_id,
                    ConditionProfile.recall_enabled.is_(True),
                )
                .all()
            )
            for profile in rows:
                synonyms = profile.keyword_synonyms or []
                if any(s.lower() in diagnosis_lower for s in synonyms):
                    profile_candidates[profile.id] = (
                        profile,
                        RecallSuggestionConfidence.LOW,
                    )

        if not profile_candidates:
            return []

        if self._is_patient_deceased(clinic_id=clinic_id, patient_id=patient_id):
            return []

        active_profile_ids = {
            row.condition_profile_id
            for row in self.db.query(ChronicRecall.condition_profile_id)
            .filter(
                ChronicRecall.clinic_id == clinic_id,
                ChronicRecall.patient_id_canonical == patient_id,
                ChronicRecall.active.is_(True),
            )
            .all()
        }

        now = datetime.now(timezone.utc)
        suggestions: list[dict] = []
        for profile, confidence in profile_candidates.values():
            if profile.id in active_profile_ids:
                continue
            if self._is_profile_in_cooldown(
                clinic_id=clinic_id,
                patient_id=patient_id,
                condition_profile_id=profile.id,
                cooldown_days=profile.cooldown_days,
                now=now,
            ):
                continue
            suggestions.append(
                {
                    "condition_profile_id": profile.id,
                    "condition_code": profile.code,
                    "display_name": profile.display_name,
                    "default_interval_value": profile.default_interval_value,
                    "default_interval_unit": profile.default_interval_unit,
                    "default_priority": profile.default_priority,
                    "confidence": confidence,
                }
            )

        suggestions.sort(
            key=lambda item: (
                0 if item["confidence"] == RecallSuggestionConfidence.HIGH else 1,
                item["display_name"].lower(),
            )
        )
        return suggestions

    def _extract_structured_codes(self, diagnosis_text: str) -> list[tuple[str, str]]:
        matches = STRUCTURED_DIAGNOSIS_PATTERN.finditer(diagnosis_text.upper())
        structured: list[tuple[str, str]] = []
        for match in matches:
            system = match.group("system").upper()
            code = match.group("code").upper()
            structured.append((system, code))
        return structured

    def _is_profile_in_cooldown(
        self,
        *,
        clinic_id: UUID,
        patient_id: UUID,
        condition_profile_id: UUID,
        cooldown_days: int,
        now: datetime,
    ) -> bool:
        if cooldown_days <= 0:
            return False

        threshold = now - timedelta(days=cooldown_days)
        row = (
            self.db.query(ChronicRecall.id)
            .filter(
                ChronicRecall.clinic_id == clinic_id,
                ChronicRecall.patient_id_canonical == patient_id,
                ChronicRecall.condition_profile_id == condition_profile_id,
                ChronicRecall.active.is_(False),
                ChronicRecall.deactivated_at.is_not(None),
                ChronicRecall.deactivated_at >= threshold,
            )
            .first()
        )
        return row is not None

    def _is_patient_deceased(self, *, clinic_id: UUID, patient_id: UUID) -> bool:
        deceased_admission = (
            self.db.query(Admission.id)
            .filter(
                Admission.clinic_id == clinic_id,
                Admission.patient_id == patient_id,
                Admission.status == AdmissionStatus.DISCHARGED,
                Admission.discharge_disposition == AdmissionDischargeDisposition.DECEASED,
            )
            .first()
        )
        return deceased_admission is not None


class ChronicRecallService:
    def __init__(self, db: Session):
        self.db = db
        self.access_log_service = AccessLogService(db)

    def create_recall(self, *, clinic_id: UUID, actor, payload) -> ChronicRecall:
        if actor.role not in {UserRole.DOCTOR, UserRole.CHEW, UserRole.MIDWIFE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinical recall creation access denied",
            )

        patient_id_requested = payload.patient_id
        patient_id_canonical = self._resolve_canonical_patient_id(
            patient_id=patient_id_requested,
            clinic_id=clinic_id,
        )
        identity_closure_ids = self._resolve_identity_closure(
            canonical_id=patient_id_canonical,
            clinic_id=clinic_id,
        )

        self._ensure_assigned_context(
            clinic_id=clinic_id,
            actor_id=actor.id,
            patient_ids=identity_closure_ids,
            origin_visit_id=payload.origin_visit_id,
        )

        profile = (
            self.db.query(ConditionProfile)
            .filter(
                ConditionProfile.id == payload.condition_profile_id,
                ConditionProfile.clinic_id == clinic_id,
            )
            .first()
        )
        if profile is None:
            raise HTTPException(status_code=404, detail="Condition profile not found")

        interval_value = (
            payload.interval_value_override
            if payload.interval_value_override is not None
            else profile.default_interval_value
        )
        interval_unit = (
            payload.interval_unit_override
            if payload.interval_unit_override is not None
            else profile.default_interval_unit
        )
        if payload.interval_unit_override is not None and payload.interval_value_override is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="interval_value_override is required when interval_unit_override is provided",
            )

        now = datetime.now(timezone.utc)
        next_due_at = _advance_due(now, interval_value, interval_unit)

        recall = ChronicRecall(
            clinic_id=clinic_id,
            patient_id_canonical=patient_id_canonical,
            condition_profile_id=payload.condition_profile_id,
            assigned_clinician_id=actor.id,
            interval_value=interval_value,
            interval_unit=interval_unit,
            next_due_at=next_due_at,
            active=True,
            created_by=actor.id,
        )
        self.db.add(recall)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active chronic recall already exists for this condition",
            ) from exc
        self.db.refresh(recall)

        self.access_log_service.log_operation(
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id_canonical,
            purpose_of_use="TREATMENT",
            justification=payload.justification,
            resource="FOLLOW_UP",
            action="WRITE",
            extra_payload={
                "operation": "CREATE_CHRONIC_RECALL",
                "chronic_recall_id": str(recall.id),
                "condition_profile_id": str(payload.condition_profile_id),
                "patient_id_requested": str(patient_id_requested),
                "patient_id_canonical": str(patient_id_canonical),
                "origin_visit_id": str(payload.origin_visit_id)
                if payload.origin_visit_id
                else None,
            },
        )
        return recall

    def _ensure_assigned_context(
        self,
        *,
        clinic_id: UUID,
        actor_id: UUID,
        patient_ids: list[UUID],
        origin_visit_id: UUID | None,
    ) -> None:
        query = self.db.query(Visit.id).filter(
            Visit.clinic_id == clinic_id,
            Visit.patient_id.in_(patient_ids),
            Visit.assigned_doctor_id == actor_id,
            Visit.status.notin_([VisitStatus.COMPLETED, VisitStatus.CANCELLED]),
        )
        if origin_visit_id is not None:
            query = query.filter(Visit.id == origin_visit_id)
        assigned_visit = query.first()
        if assigned_visit is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Recall creation requires assigned active visit context",
            )

    def _resolve_canonical_patient_id(self, *, patient_id: UUID, clinic_id: UUID) -> UUID:
        visited: set[UUID] = set()
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


def _advance_due(base: datetime, interval_value: int, interval_unit) -> datetime:
    if interval_unit.value == "DAYS":
        return base + timedelta(days=interval_value)
    if interval_unit.value == "WEEKS":
        return base + timedelta(weeks=interval_value)
    # Approximate monthly cadence using 30-day operational interval for PHC planning.
    return base + timedelta(days=interval_value * 30)
