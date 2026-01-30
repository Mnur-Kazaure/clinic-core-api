# app/api/v1/identity.py
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_db
from app.core.guards.identity_guards import (
    require_provisional_role,
    require_identity_approval_role,
    require_identity_case_role,
)
from app.schemas.identity import (
    ProvisionalPatientRequest,
    IdentityCaseCreateRequest,
    IdentityCaseResponse,
    IdentityEvidenceCreateRequest,
    IdentityApprovalRequest,
    IdentityRollbackRequest,
)
from app.services.identity_service import IdentityService


router = APIRouter(prefix="/identity", tags=["identity"])


@router.post("/provisional")
def create_provisional_patient(
    payload: ProvisionalPatientRequest,
    db=Depends(get_db),
    current_user=Depends(require_provisional_role),
):
    service = IdentityService(db)
    return service.create_provisional_patient(
        payload=payload,
        current_user=current_user,
    )


@router.post("/cases", response_model=IdentityCaseResponse)
def create_identity_case(
    payload: IdentityCaseCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_identity_case_role),
):
    service = IdentityService(db)
    return service.create_case(
        payload=payload,
        current_user=current_user,
    )


@router.post("/cases/{case_id}/evidence")
def add_identity_evidence(
    case_id: UUID,
    payload: IdentityEvidenceCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_identity_case_role),
):
    service = IdentityService(db)
    return service.add_evidence(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/cases/{case_id}/approve")
def approve_identity_case(
    case_id: UUID,
    payload: IdentityApprovalRequest,
    db=Depends(get_db),
    current_user=Depends(require_identity_approval_role),
):
    service = IdentityService(db)
    return service.approve_case(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/cases/{case_id}/apply")
def apply_identity_case(
    case_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_identity_case_role),
):
    service = IdentityService(db)
    return service.apply_case(
        case_id=case_id,
        current_user=current_user,
    )


@router.post("/cases/{case_id}/rollback")
def rollback_identity_case(
    case_id: UUID,
    payload: IdentityRollbackRequest,
    db=Depends(get_db),
    current_user=Depends(require_identity_case_role),
):
    service = IdentityService(db)
    return service.rollback_case(
        case_id=case_id,
        payload=payload,
        current_user=current_user,
    )
