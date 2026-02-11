# app/api/v1/pmr.py
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db
from app.core.guards.pmr_guards import require_pmr_read_role, require_mrn_issue_role
from app.schemas.pmr import PMRResponse, MRNIssueResponse
from app.services.pmr_service import PMRService
from app.services.mrn_service import MRNService
from app.shared.enums import PurposeOfUse


router = APIRouter(prefix="/pmr", tags=["pmr"])


@router.get(
    "/patients/{patient_id}",
    response_model=PMRResponse,
)
def get_patient_pmr(
    patient_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    detail_level: str | None = Query(None),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(require_pmr_read_role),
):
    service = PMRService(db)
    return service.get_pmr(
        patient_id=patient_id,
        clinic_id=current_user.clinic_id,
        actor=current_user,
        purpose_of_use=purpose_of_use,
        justification=justification,
        limit=limit,
        cursor=cursor,
        detail_level=detail_level,
        break_glass=break_glass,
    )


@router.post(
    "/patients/{patient_id}/mrn",
    response_model=MRNIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_patient_mrn(
    patient_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_mrn_issue_role),
):
    mrn = MRNService(db).issue_mrn_for_patient(
        patient_id=patient_id,
        clinic_id=current_user.clinic_id,
        actor=current_user,
    )
    return {"mrn": mrn}
