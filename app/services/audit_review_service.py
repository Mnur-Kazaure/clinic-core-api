# app/services/audit_review_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit_review_case import AuditReviewCase
from app.models.audit_review_item import AuditReviewItem
from app.models.audit_review_case_history import AuditReviewCaseHistory
from app.models.access_log import AccessLog
from app.models.event_log import EventLog
from app.shared.enums import AuditCaseStatus, AuditItemType


class AuditReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_case(self, *, payload, current_user) -> AuditReviewCase:
        case = AuditReviewCase(
            clinic_id=current_user.clinic_id,
            status=AuditCaseStatus.OPEN,
            severity=payload.severity,
            reason=payload.reason,
            created_by=current_user.id,
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def add_item(self, *, case_id: UUID, payload, current_user) -> AuditReviewItem:
        case = self._get_case(case_id, current_user.clinic_id)
        if case.status == AuditCaseStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot add items to closed case",
            )

        if payload.item_type == AuditItemType.ACCESS_LOG:
            if not payload.access_log_id or payload.event_log_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Access log item requires access_log_id only",
                )
            self._ensure_access_log(payload.access_log_id, current_user.clinic_id)
        else:
            if not payload.event_log_id or payload.access_log_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Event log item requires event_log_id only",
                )
            self._ensure_event_log(payload.event_log_id, current_user.clinic_id)

        item = AuditReviewItem(
            clinic_id=current_user.clinic_id,
            case_id=case.id,
            item_type=payload.item_type,
            access_log_id=payload.access_log_id,
            event_log_id=payload.event_log_id,
            added_by=current_user.id,
            added_at=datetime.now(timezone.utc),
            notes=payload.notes,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def start_review(self, *, case_id: UUID, payload, current_user) -> AuditReviewCase:
        case = self._get_case(case_id, current_user.clinic_id)
        if case.status != AuditCaseStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case is not open",
            )
        previous = case.status
        case.status = AuditCaseStatus.IN_REVIEW
        case.reviewed_by = current_user.id
        history = AuditReviewCaseHistory(
            clinic_id=current_user.clinic_id,
            case_id=case.id,
            from_status=previous,
            to_status=case.status,
            changed_by=current_user.id,
            changed_at=datetime.now(timezone.utc),
            change_reason=payload.reason,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(case)
        return case

    def close_case(self, *, case_id: UUID, payload, current_user) -> AuditReviewCase:
        case = self._get_case(case_id, current_user.clinic_id)
        if case.status != AuditCaseStatus.IN_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case is not in review",
            )
        previous = case.status
        case.status = AuditCaseStatus.CLOSED
        case.closed_by = current_user.id
        case.closed_at = datetime.now(timezone.utc)
        case.outcome = payload.outcome
        history = AuditReviewCaseHistory(
            clinic_id=current_user.clinic_id,
            case_id=case.id,
            from_status=previous,
            to_status=case.status,
            changed_by=current_user.id,
            changed_at=datetime.now(timezone.utc),
            change_reason=payload.reason,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(case)
        return case

    def _get_case(self, case_id: UUID, clinic_id: UUID) -> AuditReviewCase:
        case = (
            self.db.query(AuditReviewCase)
            .filter(
                AuditReviewCase.id == case_id,
                AuditReviewCase.clinic_id == clinic_id,
            )
            .first()
        )
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit review case not found",
            )
        return case

    def _ensure_access_log(self, log_id: UUID, clinic_id: UUID) -> None:
        log = (
            self.db.query(AccessLog)
            .filter(
                AccessLog.id == log_id,
                AccessLog.clinic_id == clinic_id,
            )
            .first()
        )
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access log not found",
            )

    def _ensure_event_log(self, log_id: UUID, clinic_id: UUID) -> None:
        log = (
            self.db.query(EventLog)
            .filter(
                EventLog.id == log_id,
                EventLog.clinic_id == clinic_id,
            )
            .first()
        )
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event log not found",
            )
