# app/api/v1/priority.py
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_db
from app.core.guards.priority_guards import require_priority_role
from app.schemas.clinical_priority import (
    ClinicalPriorityCreateRequest,
    ClinicalPriorityResponse,
)
from app.services.clinical_priority_service import ClinicalPriorityService


router = APIRouter(prefix="/priority", tags=["priority"])


@router.post(
    "/visits/{visit_id}",
    response_model=ClinicalPriorityResponse,
)
def set_visit_priority(
    visit_id: UUID,
    payload: ClinicalPriorityCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_priority_role),
):
    service = ClinicalPriorityService(db)
    priority_event = service.set_priority(
        visit_id=visit_id,
        level=payload.level,
        source=payload.source,
        reason=payload.reason,
        current_user=current_user,
    )
    return priority_event
