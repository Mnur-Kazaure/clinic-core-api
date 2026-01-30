# app/api/v1/audit_review.py
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_db
from app.core.guards.audit_review_guards import require_audit_review_role
from app.schemas.audit_review import (
    AuditReviewCaseCreateRequest,
    AuditReviewCaseStartRequest,
    AuditReviewCaseCloseRequest,
    AuditReviewItemCreateRequest,
    AuditReviewCaseResponse,
    AuditReviewItemResponse,
)
from app.services.audit_review_service import AuditReviewService


router = APIRouter(prefix="/audit-review", tags=["Audit Review"])


@router.post("/cases", response_model=AuditReviewCaseResponse, status_code=status.HTTP_201_CREATED)
def create_audit_case(
    payload: AuditReviewCaseCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_audit_review_role),
):
    service = AuditReviewService(db)
    return service.create_case(payload=payload, current_user=current_user)


@router.post("/cases/{case_id}/items", response_model=AuditReviewItemResponse)
def add_audit_item(
    case_id: UUID,
    payload: AuditReviewItemCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_audit_review_role),
):
    service = AuditReviewService(db)
    return service.add_item(case_id=case_id, payload=payload, current_user=current_user)


@router.post("/cases/{case_id}/start-review", response_model=AuditReviewCaseResponse)
def start_review(
    case_id: UUID,
    payload: AuditReviewCaseStartRequest,
    db=Depends(get_db),
    current_user=Depends(require_audit_review_role),
):
    service = AuditReviewService(db)
    return service.start_review(case_id=case_id, payload=payload, current_user=current_user)


@router.post("/cases/{case_id}/close", response_model=AuditReviewCaseResponse)
def close_review(
    case_id: UUID,
    payload: AuditReviewCaseCloseRequest,
    db=Depends(get_db),
    current_user=Depends(require_audit_review_role),
):
    service = AuditReviewService(db)
    return service.close_case(case_id=case_id, payload=payload, current_user=current_user)
