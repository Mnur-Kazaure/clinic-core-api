# app/api/v1/maternity.py
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db
from app.core.rbac import require_midwife
from app.models.visit import Visit
from app.schemas.maternity import (
    MaternityDeliveryUpsert,
    MaternityDeliveryResponse,
    PostnatalNoteCreate,
    PostnatalNoteResponse,
    FamilyPlanningEventCreate,
    FamilyPlanningEventResponse,
)
from app.services.maternity_service import MaternityService
from app.services.visit.service import VisitService
from app.api.v1.visit import _attach_patient_names
from app.services.access_log_service import AccessLogService
from app.shared.enums import PurposeOfUse, VisitStatus, VisitServiceLine


router = APIRouter(prefix="/maternity", tags=["maternity"])


@router.get("/queue")
def get_maternity_queue(
    status: VisitStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    visits = VisitService(db).get_queue_for_owner_by_service_line(
        clinic_id=current_user.clinic_id,
        owner_id=current_user.id,
        service_line=VisitServiceLine.MATERNITY,
        status=status,
    )
    _attach_patient_names(db, visits)
    return visits


@router.get(
    "/visits/{visit_id}/delivery",
    response_model=MaternityDeliveryResponse | None,
)
def get_delivery(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    service = MaternityService(db)
    record = service.get_delivery(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
    )
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id, Visit.clinic_id == current_user.clinic_id)
        .first()
    )
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=visit.patient_id if visit else None,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="MATERNITY",
        extra_payload={"visit_id": str(visit_id)},
    )
    return record


@router.post(
    "/visits/{visit_id}/delivery",
    response_model=MaternityDeliveryResponse,
)
def upsert_delivery(
    visit_id: UUID,
    payload: MaternityDeliveryUpsert,
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    return MaternityService(db).upsert_delivery(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/visits/{visit_id}/postnatal-notes",
    response_model=list[PostnatalNoteResponse],
)
def list_postnatal_notes(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    service = MaternityService(db)
    notes = service.list_postnatal_notes(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
    )
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id, Visit.clinic_id == current_user.clinic_id)
        .first()
    )
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=visit.patient_id if visit else None,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="MATERNITY",
        extra_payload={"visit_id": str(visit_id)},
    )
    return notes


@router.post(
    "/visits/{visit_id}/postnatal-notes",
    response_model=PostnatalNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_postnatal_note(
    visit_id: UUID,
    payload: PostnatalNoteCreate,
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    return MaternityService(db).add_postnatal_note(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/visits/{visit_id}/family-planning",
    response_model=list[FamilyPlanningEventResponse],
)
def list_family_planning_events(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    service = MaternityService(db)
    events = service.list_family_planning_events(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
    )
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id, Visit.clinic_id == current_user.clinic_id)
        .first()
    )
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=visit.patient_id if visit else None,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="MATERNITY",
        extra_payload={"visit_id": str(visit_id)},
    )
    return events


@router.post(
    "/visits/{visit_id}/family-planning",
    response_model=FamilyPlanningEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_family_planning_event(
    visit_id: UUID,
    payload: FamilyPlanningEventCreate,
    db=Depends(get_db),
    current_user=Depends(require_midwife),
):
    return MaternityService(db).add_family_planning_event(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
        payload=payload,
    )
