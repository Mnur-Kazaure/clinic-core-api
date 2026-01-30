# app/services/identity_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.patient_alias import PatientAlias
from app.models.identity_case import IdentityCase
from app.models.identity_evidence import IdentityEvidence
from app.models.identity_approval import IdentityApproval
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.services.event_service import EventService
from app.shared.enums import (
    IdentityState,
    IdentityCaseStatus,
    IdentityCaseType,
    IdentityApprovalRole,
    IdentityApprovalDecision,
    Gender,
    UserRole,
)


class IdentityService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    def create_provisional_patient(self, *, payload, current_user) -> Patient:
        if current_user.role not in {UserRole.RECEPTION, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Identity provisional access denied",
            )
        full_name = payload.full_name or "Unknown Patient"
        date_of_birth = payload.date_of_birth or datetime(1900, 1, 1, tzinfo=timezone.utc).date()
        phone_number = payload.phone_number or "UNKNOWN"
        address = payload.address or "UNKNOWN"
        occupation = payload.occupation or "UNKNOWN"
        gender = payload.gender or Gender.UNKNOWN
        patient = Patient(
            clinic_id=current_user.clinic_id,
            full_name=full_name,
            date_of_birth=date_of_birth,
            gender=gender,
            phone_number=phone_number,
            address=address,
            occupation=occupation,
            identity_state=IdentityState.PROVISIONAL,
            created_reason=payload.created_reason,
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)

        self.event_service.emit(
            event_type="PROVISIONAL_CREATED",
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=current_user.clinic_id,
            patient_id=patient.id,
            emitter="identity",
            payload={
                "clinic_id": str(current_user.clinic_id),
                "patient_id": str(patient.id),
                "actor_id": str(current_user.id),
                "actor_role": current_user.role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return patient

    def create_case(self, *, payload, current_user) -> IdentityCase:
        if current_user.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Identity case creation denied",
            )
        self._ensure_patient_in_clinic(payload.primary_patient_id, current_user.clinic_id)
        if payload.target_patient_id:
            self._ensure_patient_in_clinic(payload.target_patient_id, current_user.clinic_id)

        case = IdentityCase(
            clinic_id=current_user.clinic_id,
            case_type=payload.case_type,
            status=IdentityCaseStatus.OPEN,
            created_by=current_user.id,
            reason=payload.reason,
            primary_patient_id=payload.primary_patient_id,
            target_patient_id=payload.target_patient_id,
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def add_evidence(self, *, case_id: UUID, payload, current_user) -> IdentityEvidence:
        if current_user.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Identity evidence access denied",
            )
        case = self._get_case(case_id, current_user.clinic_id)
        if case.status == IdentityCaseStatus.REJECTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rejected case cannot accept evidence",
            )
        evidence = IdentityEvidence(
            clinic_id=case.clinic_id,
            case_id=case.id,
            evidence_type=payload.evidence_type,
            ref=payload.ref,
            notes=payload.notes,
            added_by=current_user.id,
            added_at=datetime.now(timezone.utc),
        )
        self.db.add(evidence)
        if case.status == IdentityCaseStatus.OPEN:
            case.status = IdentityCaseStatus.UNDER_REVIEW
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def approve_case(self, *, case_id: UUID, payload, current_user) -> IdentityApproval:
        case = self._get_case(case_id, current_user.clinic_id)
        if case.status not in {IdentityCaseStatus.OPEN, IdentityCaseStatus.UNDER_REVIEW}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case not eligible for approval",
            )
        approver_role = self._map_approval_role(current_user.role)
        if approver_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approval access denied",
            )

        if payload.decision == IdentityApprovalDecision.APPROVE:
            self._require_evidence_minimum(case)

        existing = (
            self.db.query(IdentityApproval)
            .filter(
                IdentityApproval.case_id == case.id,
                IdentityApproval.clinic_id == case.clinic_id,
                IdentityApproval.approver_role == approver_role,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval already recorded for this role",
            )
        existing_by_user = (
            self.db.query(IdentityApproval)
            .filter(
                IdentityApproval.case_id == case.id,
                IdentityApproval.clinic_id == case.clinic_id,
                IdentityApproval.approver_id == current_user.id,
            )
            .first()
        )
        if existing_by_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approver already recorded",
            )

        approval = IdentityApproval(
            clinic_id=case.clinic_id,
            case_id=case.id,
            approver_role=approver_role,
            approver_id=current_user.id,
            decision=payload.decision,
            decision_reason=payload.decision_reason,
            decided_at=datetime.now(timezone.utc),
        )
        self.db.add(approval)
        self.db.flush()
        if payload.decision == IdentityApprovalDecision.REJECT:
            case.status = IdentityCaseStatus.REJECTED
        else:
            case.status = IdentityCaseStatus.UNDER_REVIEW
            if self._has_required_approvals(case):
                case.status = IdentityCaseStatus.APPROVED
        self.db.commit()
        self.db.refresh(approval)
        return approval

    def apply_case(self, *, case_id: UUID, current_user) -> IdentityCase:
        case = self._get_case(case_id, current_user.clinic_id)
        if current_user.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Identity apply access denied",
            )
        if case.status != IdentityCaseStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case must be approved before apply",
            )
        approvals = self._get_approvals(case)

        if case.case_type in {IdentityCaseType.MERGE, IdentityCaseType.SPLIT}:
            self._require_dual_approval(approvals)
        elif case.case_type == IdentityCaseType.VERIFY:
            self._require_single_approval(approvals)

        if case.case_type == IdentityCaseType.VERIFY:
            patient = self._get_patient(case.primary_patient_id, case.clinic_id)
            before_state = patient.identity_state
            patient.identity_state = IdentityState.VERIFIED
            patient.verified_at = datetime.now(timezone.utc)
            patient.verified_by = current_user.id
            case.status = IdentityCaseStatus.APPLIED
            self.db.commit()
            self._emit_identity_event(
                event_type="IDENTITY_VERIFIED",
                case=case,
                current_user=current_user,
                before_after={
                    "primary_before": before_state.value,
                    "primary_after": IdentityState.VERIFIED.value,
                },
            )
            return case

        if case.case_type == IdentityCaseType.MERGE:
            if not case.target_patient_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target patient required for merge",
                )
            self._require_evidence_minimum(case)
            self._ensure_no_identity_cycle(case.primary_patient_id, case.target_patient_id, case.clinic_id)
            primary = self._get_patient(case.primary_patient_id, case.clinic_id)
            target = self._get_patient(case.target_patient_id, case.clinic_id)
            before_primary = primary.identity_state
            before_target = target.identity_state
            mapping = PatientIdentityMap(
                clinic_id=case.clinic_id,
                from_patient_id=case.primary_patient_id,
                to_patient_id=case.target_patient_id,
                mapped_at=datetime.now(timezone.utc),
                mapped_by=current_user.id,
            )
            self.db.add(mapping)
            self.db.flush()
            primary.identity_state = IdentityState.MERGED
            case.status = IdentityCaseStatus.APPLIED
            self.db.commit()
            self._emit_identity_event(
                event_type="IDENTITY_MERGED",
                case=case,
                current_user=current_user,
                extra={"map_id": str(mapping.id)},
                before_after={
                    "primary_before": before_primary.value,
                    "primary_after": IdentityState.MERGED.value,
                    "target_before": before_target.value,
                    "target_after": target.identity_state.value,
                },
            )
            return case

        if case.case_type == IdentityCaseType.SPLIT:
            if not case.target_patient_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target patient required for split",
                )
            self._require_evidence_minimum(case)
            primary = self._get_patient(case.primary_patient_id, case.clinic_id)
            target = self._get_patient(case.target_patient_id, case.clinic_id)
            before_primary = primary.identity_state
            before_target = target.identity_state
            mapping = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == case.clinic_id,
                    PatientIdentityMap.from_patient_id == case.primary_patient_id,
                )
                .first()
            )
            if mapping and mapping.to_patient_id != case.target_patient_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Split target does not match current identity mapping",
                )
            if mapping:
                existing_revocation = (
                    self.db.query(IdentityMapRevocation)
                    .filter(
                        IdentityMapRevocation.clinic_id == case.clinic_id,
                        IdentityMapRevocation.map_id == mapping.id,
                    )
                    .first()
                )
                if not existing_revocation:
                    revocation = IdentityMapRevocation(
                        clinic_id=case.clinic_id,
                        map_id=mapping.id,
                        case_id=case.id,
                        revoked_by=current_user.id,
                        revoked_at=datetime.now(timezone.utc),
                        reason=case.reason,
                    )
                    self.db.add(revocation)
            primary.identity_state = IdentityState.SPLIT
            if target.identity_state == IdentityState.MERGED:
                target.identity_state = IdentityState.VERIFIED
            case.status = IdentityCaseStatus.APPLIED
            self.db.commit()
            self._emit_identity_event(
                event_type="IDENTITY_SPLIT",
                case=case,
                current_user=current_user,
                extra={"map_id": str(mapping.id)} if mapping else None,
                before_after={
                    "primary_before": before_primary.value,
                    "primary_after": IdentityState.SPLIT.value,
                    "target_before": before_target.value,
                    "target_after": target.identity_state.value,
                },
            )
            return case

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported case type",
        )

    def rollback_case(self, *, case_id: UUID, payload, current_user) -> IdentityCase:
        case = self._get_case(case_id, current_user.clinic_id)
        if current_user.role not in {UserRole.ADMIN, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Identity rollback access denied",
            )
        if case.status != IdentityCaseStatus.APPLIED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case not applied",
            )
        mapping = (
            self.db.query(PatientIdentityMap)
            .filter(
                PatientIdentityMap.clinic_id == case.clinic_id,
                PatientIdentityMap.from_patient_id == case.primary_patient_id,
            )
            .first()
        )
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No identity mapping found for rollback",
            )
        patient = self._get_patient(case.primary_patient_id, case.clinic_id)
        before_state = patient.identity_state
        restore_state = IdentityState.PROVISIONAL if patient.created_reason else IdentityState.VERIFIED
        patient.identity_state = restore_state
        revocation = IdentityMapRevocation(
            clinic_id=case.clinic_id,
            map_id=mapping.id,
            case_id=case.id,
            revoked_by=current_user.id,
            revoked_at=datetime.now(timezone.utc),
            reason=payload.reason,
        )
        self.db.add(revocation)
        case.status = IdentityCaseStatus.ROLLED_BACK
        self.db.commit()
        self._emit_identity_event(
            event_type="IDENTITY_ROLLED_BACK",
            case=case,
            current_user=current_user,
            extra={"map_id": str(mapping.id)},
            before_after={
                "primary_before": before_state.value,
                "primary_after": restore_state.value,
            },
        )
        return case

    def resolve_canonical_patient_id(self, *, patient_id: UUID, clinic_id: UUID) -> UUID:
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

    def _emit_identity_event(self, *, event_type: str, case: IdentityCase, current_user, extra: dict | None = None, before_after: dict | None = None):
        evidence_ids = [
            str(ev.id)
            for ev in self.db.query(IdentityEvidence)
            .filter(
                IdentityEvidence.case_id == case.id,
                IdentityEvidence.clinic_id == case.clinic_id,
            )
            .all()
        ]
        approval_ids = [
            str(ap.id)
            for ap in self.db.query(IdentityApproval)
            .filter(
                IdentityApproval.case_id == case.id,
                IdentityApproval.clinic_id == case.clinic_id,
            )
            .all()
        ]
        payload = {
            "clinic_id": str(case.clinic_id),
            "case_id": str(case.id),
            "primary_patient_id": str(case.primary_patient_id),
            "target_patient_id": str(case.target_patient_id) if case.target_patient_id else None,
            "actor_id": str(current_user.id),
            "actor_role": current_user.role,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence_ids": evidence_ids,
            "approval_ids": approval_ids,
        }
        if extra:
            payload.update(extra)
        if before_after:
            payload.update(before_after)
        self.event_service.emit(
            event_type=event_type,
            actor_id=current_user.id,
            actor_role=current_user.role,
            clinic_id=case.clinic_id,
            patient_id=case.primary_patient_id,
            emitter="identity",
            payload=payload,
        )

    def _get_case(self, case_id: UUID, clinic_id: UUID) -> IdentityCase:
        case = (
            self.db.query(IdentityCase)
            .filter(
                IdentityCase.id == case_id,
                IdentityCase.clinic_id == clinic_id,
            )
            .first()
        )
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Identity case not found",
            )
        return case

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )
        return patient

    def _ensure_patient_in_clinic(self, patient_id: UUID, clinic_id: UUID) -> None:
        self._get_patient(patient_id, clinic_id)

    def _map_approval_role(self, role: str) -> IdentityApprovalRole | None:
        if role == UserRole.ADMIN:
            return IdentityApprovalRole.ADMIN
        if role == UserRole.CLINIC_ADMIN:
            return IdentityApprovalRole.CLINIC_ADMIN
        return None

    def _get_approvals(self, case: IdentityCase) -> list[IdentityApproval]:
        return (
            self.db.query(IdentityApproval)
            .filter(
                IdentityApproval.case_id == case.id,
                IdentityApproval.clinic_id == case.clinic_id,
            )
            .all()
        )

    def _require_dual_approval(self, approvals: list[IdentityApproval]) -> None:
        roles = {approval.approver_role for approval in approvals if approval.decision == IdentityApprovalDecision.APPROVE}
        if not {IdentityApprovalRole.ADMIN, IdentityApprovalRole.CLINIC_ADMIN}.issubset(roles):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dual approval required",
            )

    def _require_single_approval(self, approvals: list[IdentityApproval]) -> None:
        roles = {approval.approver_role for approval in approvals if approval.decision == IdentityApprovalDecision.APPROVE}
        if IdentityApprovalRole.CLINIC_ADMIN not in roles:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verification approval required",
            )

    def _has_required_approvals(self, case: IdentityCase) -> bool:
        approvals = self._get_approvals(case)
        if case.case_type == IdentityCaseType.VERIFY:
            try:
                self._require_single_approval(approvals)
                return True
            except HTTPException:
                return False
        if case.case_type in {IdentityCaseType.MERGE, IdentityCaseType.SPLIT}:
            try:
                self._require_dual_approval(approvals)
                return True
            except HTTPException:
                return False
        return False

    def _require_evidence_minimum(self, case: IdentityCase) -> None:
        evidence_count = (
            self.db.query(IdentityEvidence)
            .filter(
                IdentityEvidence.case_id == case.id,
                IdentityEvidence.clinic_id == case.clinic_id,
            )
            .count()
        )
        if case.case_type == IdentityCaseType.VERIFY and evidence_count < 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verification requires at least one evidence item",
            )
        if case.case_type in {IdentityCaseType.MERGE, IdentityCaseType.SPLIT} and evidence_count < 2:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Merge/split requires at least two evidence items",
            )

    def _ensure_no_identity_cycle(self, from_patient_id: UUID, to_patient_id: UUID, clinic_id: UUID) -> None:
        canonical = self.resolve_canonical_patient_id(
            patient_id=to_patient_id,
            clinic_id=clinic_id,
        )
        if canonical == from_patient_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Identity mapping cycle detected",
            )
