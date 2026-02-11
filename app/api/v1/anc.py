# app/api/v1/anc.py
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import get_db
from app.core.rbac import require_chew, require_visit_access
from app.models.visit import Visit
from app.models.patient import Patient
from app.schemas.anc import (
    PregnancyEpisodeCreate,
    PregnancyEpisodeResponse,
    PreviousPregnancyCreate,
    PreviousPregnancyResponse,
    ANCEncounterUpsert,
    ANCEncounterResponse,
)
from app.services.anc_service import ANCService
from app.services.visit.service import VisitService
from app.api.v1.visit import _attach_patient_names
from app.services.access_log_service import AccessLogService
from app.shared.enums import PurposeOfUse, VisitStatus, VisitServiceLine


router = APIRouter(prefix="/anc", tags=["anc"])


@router.get("/queue")
def get_anc_queue(
    status: VisitStatus | None = None,
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    visits = VisitService(db).get_queue_for_owner_by_service_line(
        clinic_id=current_user.clinic_id,
        owner_id=current_user.id,
        service_line=VisitServiceLine.ANC,
        status=status,
    )
    _attach_patient_names(db, visits)
    return visits


@router.post(
    "/patients/{patient_id}/episodes",
    response_model=PregnancyEpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_episode(
    patient_id: UUID,
    payload: PregnancyEpisodeCreate,
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    service = ANCService(db)
    return service.create_episode(
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
        actor_id=current_user.id,
        close_existing=payload.close_existing,
        payload=payload,
    )


@router.get("/episodes/active", response_model=PregnancyEpisodeResponse | None)
def get_active_episode(
    patient_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    patient = (
        db.query(Patient)
        .filter(Patient.id == patient_id, Patient.clinic_id == current_user.clinic_id)
        .first()
    )
    if patient is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Patient not found")
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="ANC",
        extra_payload={"patient_id_requested": str(patient_id)},
    )
    return ANCService(db).get_active_episode(
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
    )


@router.get("/episodes/{episode_id}", response_model=PregnancyEpisodeResponse)
def get_episode(
    episode_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    episode = ANCService(db).get_episode(
        clinic_id=current_user.clinic_id,
        episode_id=episode_id,
    )
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=episode.patient_id,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="ANC",
        extra_payload={"episode_id": str(episode_id)},
    )
    return episode


@router.post(
    "/episodes/{episode_id}/previous-pregnancies",
    response_model=PreviousPregnancyResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_previous_pregnancy(
    episode_id: UUID,
    payload: PreviousPregnancyCreate,
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    return ANCService(db).add_previous_pregnancy(
        clinic_id=current_user.clinic_id,
        episode_id=episode_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/episodes/{episode_id}/previous-pregnancies",
    response_model=list[PreviousPregnancyResponse],
)
def list_previous_pregnancies(
    episode_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    service = ANCService(db)
    episode = service.get_episode(
        clinic_id=current_user.clinic_id,
        episode_id=episode_id,
    )
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=episode.patient_id,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="ANC",
        extra_payload={"episode_id": str(episode_id)},
    )
    return service.list_previous_pregnancies(
        clinic_id=current_user.clinic_id,
        episode_id=episode_id,
    )


@router.get(
    "/visits/{visit_id}/encounter",
    response_model=ANCEncounterResponse | None,
)
def get_encounter(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    service = ANCService(db)
    encounter = service.get_encounter(
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
        resource="ANC",
        extra_payload={"visit_id": str(visit_id)},
    )
    return encounter


@router.post(
    "/visits/{visit_id}/encounter",
    response_model=ANCEncounterResponse,
)
def upsert_encounter(
    visit_id: UUID,
    payload: ANCEncounterUpsert,
    db=Depends(get_db),
    current_user=Depends(require_chew),
):
    return ANCService(db).upsert_encounter(
        clinic_id=current_user.clinic_id,
        visit_id=visit_id,
        actor_id=current_user.id,
        payload=payload,
    )


@router.get("/episodes/{episode_id}/export.pdf")
def export_episode_pdf(
    episode_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    include_previous_pregnancies: bool = Query(True),
    include_encounters: bool = Query(True),
    include_blank_rows: int = Query(0, ge=0, le=20),
    format: Literal["A4"] = Query("A4"),
    orientation: Literal["PORTRAIT"] = Query("PORTRAIT"),
    db=Depends(get_db),
    current_user=Depends(require_visit_access),
):
    # Format/orientation are locked for v1.0; these params intentionally remain for stable API shape.
    _ = format
    _ = orientation

    pdf_bytes, filename = ANCService(db).export_episode_pdf(
        clinic_id=current_user.clinic_id,
        episode_id=episode_id,
        actor=current_user,
        purpose_of_use=purpose_of_use,
        justification=justification,
        include_previous_pregnancies=include_previous_pregnancies,
        include_encounters=include_encounters,
        include_blank_rows=include_blank_rows,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
