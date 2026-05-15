from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lab_result import LabResult
from app.models.lab_test_config import LabTestConfig
from app.models.user import User
from app.shared.enums import (
    LabSpecimenRejectionReasonCode,
    LabVerificationPolicy,
    UserRole,
)


LAB_TECH_EQUIVALENT_ROLES = frozenset({UserRole.LAB, UserRole.LAB_TECH})
LAB_SPECIMEN_HANDLING_ROLES = frozenset(
    {
        UserRole.LAB,
        UserRole.LAB_TECH,
        UserRole.LAB_SCIENTIST,
        UserRole.LAB_SUPERVISOR,
    }
)
LAB_RESULT_ENTRY_ROLES = LAB_SPECIMEN_HANDLING_ROLES
LAB_QC_ENTRY_ROLES = frozenset({UserRole.LAB_SCIENTIST, UserRole.LAB_SUPERVISOR})
LAB_TECH_REJECTION_REASONS = frozenset(
    {
        LabSpecimenRejectionReasonCode.WRONG_LABEL,
        LabSpecimenRejectionReasonCode.BROKEN_CONTAINER,
        LabSpecimenRejectionReasonCode.MISSING_SAMPLE,
    }
)


@dataclass(frozen=True)
class LabActorContext:
    user: User
    role: UserRole


class LabRoleAccessService:
    def __init__(self, db: Session):
        self.db = db

    def get_actor(self, *, actor_id: UUID) -> LabActorContext:
        user = self.db.query(User).filter(User.id == actor_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab actor not found",
            )
        try:
            role = UserRole(user.role)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab authority denied for this account",
            ) from exc
        return LabActorContext(user=user, role=role)

    def assert_can_handle_specimen(self, *, actor: LabActorContext) -> None:
        if actor.role not in LAB_SPECIMEN_HANDLING_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role cannot handle laboratory specimens",
            )

    def assert_can_enter_result(self, *, actor: LabActorContext) -> None:
        if actor.role not in LAB_RESULT_ENTRY_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role cannot enter laboratory results",
            )

    def assert_can_verify_result(
        self,
        *,
        actor: LabActorContext,
        result: LabResult,
        config: LabTestConfig | None,
        has_critical: bool,
    ) -> None:
        if actor.role == UserRole.LAB_MANAGER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lab manager accounts are oversight-only",
            )
        if actor.role in LAB_TECH_EQUIVALENT_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Technician-level roles cannot verify lab results",
            )
        if result.entered_by == actor.user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Result verification requires separation of duties",
            )
        if has_critical and actor.role != UserRole.LAB_SUPERVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Critical lab results require supervisor verification",
            )
        if actor.role == UserRole.LAB_SCIENTIST:
            if config is None or not config.allows_scientist_verification:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Scientist verification is not enabled for this test",
                )
            if config.scientist_verification_restricted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Scientist verification is restricted for this test",
                )

    def assert_can_release_result(self, *, actor: LabActorContext) -> None:
        if actor.role != UserRole.LAB_SUPERVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only laboratory supervisors can release lab results",
            )

    def assert_can_amend_result(self, *, actor: LabActorContext) -> None:
        if actor.role != UserRole.LAB_SUPERVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only laboratory supervisors can amend released results",
            )

    def assert_can_enter_qc(self, *, actor: LabActorContext) -> None:
        if actor.role not in LAB_QC_ENTRY_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only scientists or supervisors can enter QC data",
            )

    def assert_can_override_qc(self, *, actor: LabActorContext) -> None:
        if actor.role != UserRole.LAB_SUPERVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only laboratory supervisors can override QC release blocks",
            )

    def assert_can_reject_specimen(
        self,
        *,
        actor: LabActorContext,
        reason_code: LabSpecimenRejectionReasonCode,
    ) -> None:
        self.assert_can_handle_specimen(actor=actor)
        if actor.role in LAB_TECH_EQUIVALENT_ROLES and reason_code not in LAB_TECH_REJECTION_REASONS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Technician-level roles may only reject specimens for wrong label, "
                    "broken container, or missing sample"
                ),
            )

    def requires_verification(
        self,
        *,
        verification_policy: LabVerificationPolicy,
        has_abnormal: bool,
        has_critical: bool,
    ) -> bool:
        if verification_policy == LabVerificationPolicy.NONE:
            return False
        if verification_policy == LabVerificationPolicy.OPTIONAL:
            return False
        if verification_policy == LabVerificationPolicy.REQUIRED_BEFORE_RELEASE:
            return True
        if verification_policy == LabVerificationPolicy.REQUIRED_IF_ABNORMAL:
            return has_abnormal
        if verification_policy == LabVerificationPolicy.REQUIRED_IF_CRITICAL:
            return has_critical
        return False
