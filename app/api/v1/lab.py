# app/api/v1/lab.py
from fastapi import APIRouter, Depends, status
from uuid import UUID

from app.core.lab_guards import require_lab_access
from app.services.lab_service import LabService
from app.schemas.lab import LabResultCreate, LabResultResponse
from app.core.dependencies import get_db

router = APIRouter(prefix="/lab", tags=["Lab"])


@router.post(
    "/{visit_id}/results",
    response_model=LabResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_lab_result(
    visit_id: UUID,
    payload: LabResultCreate,
    visit=Depends(require_lab_access),  # 🔒 Guard enforced here
    db=Depends(get_db),
):
    service = LabService(db)

    result = service.record_result(
        visit=visit,
        payload=payload,
    )

    return result