# app/api/v1/visit.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID


from app.core.idempotency import idempotent, hash_request
from app.models.idempotency import IdempotencyKey

from app.core.idempotency import idempotent
from app.core.rbac import require_visit_access
from app.schemas.visit import (
    VisitResponse,
    VisitTransitionRequest,
    VisitIntakeFlagRequest,
    VisitReassignRequest,
)
from app.schemas.triage import (
    TriageAssessmentResponse,
    TriageDraftRequest,
    TriageDraftResponse,
    TriageFinalizeRequest,
    TriageFinalizeResponse,
    TriageSignRequest,
    TriageSupersedeRequest,
)
from app.services.visit.service import VisitService
from app.services.triage_service import TriageService
from app.services.pharmacy_service import PharmacyService
from app.services.access_log_service import AccessLogService
from app.core.dependencies import get_db
from app.core.auth import get_current_user
from app.shared.enums import (
    AdmissionStatus,
    MRNStatus,
    PurposeOfUse,
    VisitStatus,
    VisitTriageState,
)

from app.models.visit import Visit
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.visit_intake_flag import VisitIntakeFlag
from app.models.admission import Admission
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.consultation import Consultation
from app.schemas.visit import AllowedTransitionsResponse
from app.schemas.visit import VisitTimelineResponse
from app.schemas.service_line import ServiceLineTreeNode
from app.services.service_line_service import ServiceLineService


router = APIRouter(prefix="/visits", tags=["Visits"])



from app.schemas.visit import VisitCreateRequest, VisitCreateResponse

from datetime import datetime
from app.core.rbac import require_reception
from app.core.rbac import require_triage_staff
from app.core.rbac import require_doctor
from app.core.rbac import require_clinic_admin
from app.shared.enums import UserRole
import uuid

from datetime import date, datetime, timezone
from typing import Optional, List
from app.schemas.visit import VisitResponse
from app.core.rbac import require_reception




@router.post(
    "/start",
    response_model=VisitCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_visit(
    payload: VisitCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    """
    START VISIT — This endpoint represents the moment clinical care begins.

    Semantics:
    - Initiated ONLY by Reception
    - Creates a Visit
    - Assigns doctor
    - Sets started_at (legal timestamp)
    - Patient enters clinical workflow
    """

    service = VisitService(db)
    visit = service.start_visit(payload, current_user)
    _attach_patient_name(db, visit)
    return visit


@router.post(
    "/{visit_id}/reassign-owner",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def reassign_owner(
    visit_id: UUID,
    payload: VisitReassignRequest,
    db=Depends(get_db),
    current_user=Depends(require_visit_access),
):
    service = VisitService(db)
    visit = service.reassign_owner(
        visit_id=visit_id,
        new_owner_id=payload.assigned_doctor_id,
        new_service_line=payload.service_line,
        user=current_user,
        expected_version=payload.expected_version,
        reason=payload.reason,
    )
    _attach_patient_name(db, visit)
    return VisitResponse.model_validate(visit, from_attributes=True).model_dump(
        mode="json"
    )


@router.get(
    "/active",
    response_model=VisitResponse | None,
    status_code=status.HTTP_200_OK,
)
def get_active_visit(
    patient_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    """
    Return the active visit for a patient (if any) within the clinic.
    Used to prevent duplicate visits and enable "Continue Visit" UX.
    """
    AccessLogService(db).log_chart_read(
        actor=current_user,
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
        purpose_of_use=purpose_of_use,
        justification=justification,
        resource="ACTIVE_VISIT_CHECK",
    )
    service = VisitService(db)
    visit = service.get_active_visit_for_patient(
        clinic_id=current_user.clinic_id,
        patient_id=patient_id,
    )
    if visit:
        _attach_patient_name(db, visit)
    return visit


# Transition a visit to a new status
@router.post(
    "/{visit_id}/transition",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def transition_visit(
    visit_id: UUID,
    payload: VisitTransitionRequest,
    dep=Depends(idempotent("VISIT_TRANSITION")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep

    # 🔁 Replay short-circuit
    if record:
        return record.response_body

    service = VisitService(db)

    try:
        visit = service.transition_visit(
            visit_id=visit_id,
            to_status=payload.to_status,
            user=current_user,
            expected_version=payload.expected_version,
            mode=payload.mode,
            override_reason_code=payload.override_reason_code,
            override_reason_text=payload.override_reason_text,
            idempotency_key=key,
        )

        # 🔒 Clinic boundary
        if visit.clinic_id != current_user.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-clinic access denied",
            )

        # ✅ JSON-safe serialization (FIX)
        _attach_patient_name(db, visit)
        response_payload = VisitResponse.model_validate(
            visit,
            from_attributes=True,
        ).model_dump(mode="json")

        # ✅ Persist idempotency atomically
        db.add(
            IdempotencyKey(
                id=uuid.uuid4(),
                key=key,
                user_id=current_user.id,
                endpoint="VISIT_TRANSITION",
                request_hash=hash_request(payload.model_dump(mode="json")),
                response_body=response_payload,
            )
        )
        db.commit()

        # ✅ ALWAYS return serialized payload
        return response_payload

    except PermissionError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{visit_id}/triage/draft",
    response_model=TriageDraftResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_triage_draft(
    visit_id: UUID,
    payload: TriageDraftRequest,
    dep=Depends(idempotent("VISIT_TRIAGE_DRAFT")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep
    if record:
        return record.response_body

    triage_service = TriageService(db)
    triage, visit = triage_service.upsert_draft_assessment(
        visit_id=visit_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=key,
    )

    response_payload = TriageDraftResponse(
        triage_assessment=TriageAssessmentResponse.model_validate(
            triage,
            from_attributes=True,
        ),
        visit_id=visit.id,
        visit_status=visit.status,
        visit_version=visit.version,
    ).model_dump(mode="json")

    db.add(
        IdempotencyKey(
            id=uuid.uuid4(),
            key=key,
            user_id=current_user.id,
            endpoint="VISIT_TRIAGE_DRAFT",
            request_hash=hash_request(payload.model_dump(mode="json")),
            response_body=response_payload,
        )
    )
    db.commit()
    return response_payload


@router.post(
    "/{visit_id}/triage/sign",
    response_model=TriageFinalizeResponse,
    status_code=status.HTTP_200_OK,
)
def sign_triage_assessment(
    visit_id: UUID,
    payload: TriageSignRequest,
    dep=Depends(idempotent("VISIT_TRIAGE_SIGN")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep
    if record:
        return record.response_body

    triage_service = TriageService(db)
    triage, visit = triage_service.sign_assessment(
        visit_id=visit_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=key,
    )

    response_payload = TriageFinalizeResponse(
        triage_assessment=TriageAssessmentResponse.model_validate(
            triage,
            from_attributes=True,
        ),
        visit_id=visit.id,
        visit_status=visit.status,
        visit_version=visit.version,
    ).model_dump(mode="json")

    db.add(
        IdempotencyKey(
            id=uuid.uuid4(),
            key=key,
            user_id=current_user.id,
            endpoint="VISIT_TRIAGE_SIGN",
            request_hash=hash_request(payload.model_dump(mode="json")),
            response_body=response_payload,
        )
    )
    db.commit()
    return response_payload


@router.post(
    "/{visit_id}/triage/finalize",
    response_model=TriageFinalizeResponse,
    status_code=status.HTTP_200_OK,
)
def finalize_triage(
    visit_id: UUID,
    payload: TriageFinalizeRequest,
    dep=Depends(idempotent("VISIT_TRIAGE_FINALIZE")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep
    if record:
        return record.response_body

    triage_service = TriageService(db)
    triage, visit = triage_service.finalize_assessment(
        visit_id=visit_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=key,
    )

    response_payload = TriageFinalizeResponse(
        triage_assessment=TriageAssessmentResponse.model_validate(
            triage,
            from_attributes=True,
        ),
        visit_id=visit.id,
        visit_status=visit.status,
        visit_version=visit.version,
    ).model_dump(mode="json")

    db.add(
        IdempotencyKey(
            id=uuid.uuid4(),
            key=key,
            user_id=current_user.id,
            endpoint="VISIT_TRIAGE_FINALIZE",
            request_hash=hash_request(payload.model_dump(mode="json")),
            response_body=response_payload,
        )
    )
    db.commit()
    return response_payload


@router.post(
    "/{visit_id}/triage/supersede",
    response_model=TriageFinalizeResponse,
    status_code=status.HTTP_200_OK,
)
def supersede_triage(
    visit_id: UUID,
    payload: TriageSupersedeRequest,
    dep=Depends(idempotent("VISIT_TRIAGE_SUPERSEDE")),
    current_user=Depends(require_visit_access),
):
    record, key, db = dep
    if record:
        return record.response_body

    triage_service = TriageService(db)
    triage, visit = triage_service.supersede_assessment(
        visit_id=visit_id,
        payload=payload,
        current_user=current_user,
        idempotency_key=key,
    )

    response_payload = TriageFinalizeResponse(
        triage_assessment=TriageAssessmentResponse.model_validate(
            triage,
            from_attributes=True,
        ),
        visit_id=visit.id,
        visit_status=visit.status,
        visit_version=visit.version,
    ).model_dump(mode="json")

    db.add(
        IdempotencyKey(
            id=uuid.uuid4(),
            key=key,
            user_id=current_user.id,
            endpoint="VISIT_TRIAGE_SUPERSEDE",
            request_hash=hash_request(payload.model_dump(mode="json")),
            response_body=response_payload,
        )
    )
    db.commit()
    return response_payload


@router.get(
    "/{visit_id}/triage",
    response_model=TriageAssessmentResponse | None,
    status_code=status.HTTP_200_OK,
)
def get_active_triage(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_visit_access),
):
    triage = TriageService(db).get_active_assessment(
        visit_id=visit_id,
        current_user=current_user,
    )
    if not triage:
        return None
    return TriageAssessmentResponse.model_validate(
        triage,
        from_attributes=True,
    )


@router.post(
    "/{visit_id}/auto-complete",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
)
def recheck_auto_complete(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    service = PharmacyService(db)
    updated = service.recheck_auto_complete_visit(visit_id)
    if updated:
        _attach_patient_name(db, updated)
    return updated




# Get allowed transitions for a visit
@router.get(
    "/{visit_id}/allowed-transitions",
    response_model=AllowedTransitionsResponse,
)
def get_allowed_transitions(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )
    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    service = VisitService(db)
    allowed = service.get_allowed_transitions(visit, current_user)

    return {"allowed": allowed}


# Get visit timeline
@router.get(
    "/{visit_id}/timeline",
    response_model=VisitTimelineResponse,
)
def get_visit_timeline(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    service = VisitService(db)
    timeline = service.get_visit_timeline(visit_id)

    return {
        "visit_id": visit_id,
        "timeline": timeline,
    }


# Get reception queue
@router.get("/queue", response_model=list[VisitResponse])
def get_queue(
    status: Optional[VisitStatus] = None,
    department_id: UUID | None = None,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    """
    Reception queue for current clinic.
    Optional filter by status.
    MVP: returns all visits for clinic (optionally by status).
    """
    service = VisitService(db)
    effective_department_id = _resolve_department_filter(
        current_user=current_user,
        requested_department_id=department_id,
    )
    visits = service.get_queue_for_clinic(
        clinic_id=current_user.clinic_id,
        status=status,
        department_id=effective_department_id,
    )
    _attach_patient_names(db, visits)
    return visits


@router.get("/triage/queue", response_model=list[VisitResponse])
def get_triage_queue(
    triage_state: VisitTriageState | None = Query(default=VisitTriageState.PENDING),
    limit: int = Query(default=150, ge=1, le=500),
    db=Depends(get_db),
    current_user=Depends(require_triage_staff),
):
    """
    Clinical triage queue for triage-capable staff.
    Default scope is PENDING triage_state (patients awaiting triage assessment).
    """
    visits = TriageService(db).list_triage_queue(
        current_user=current_user,
        triage_state=triage_state,
        limit=limit,
    )
    _attach_patient_names(db, visits)
    return visits


@router.get(
    "/service-lines",
    response_model=list[ServiceLineTreeNode],
    status_code=status.HTTP_200_OK,
)
def list_reception_service_lines(
    include_inactive: bool = False,
    include_global_roots: bool = True,
    department_id: UUID | None = None,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    effective_department_id = _resolve_department_filter(
        current_user=current_user,
        requested_department_id=department_id,
    )
    nodes = ServiceLineService(db).list_tree(
        clinic_id=current_user.clinic_id,
        include_inactive=include_inactive,
        department_id=effective_department_id,
        include_global_roots=include_global_roots,
    )
    return [ServiceLineTreeNode.model_validate(node) for node in nodes]

# app/api/v1/visit.py
# Doctor visit queue
@router.get("/doctor-queue", response_model=list[VisitResponse])
def get_doctor_queue(
    status: Optional[VisitStatus] = None,
    department_id: UUID | None = None,
    db=Depends(get_db),
    current_user=Depends(require_doctor),
):
    """
    Doctor queue for current clinic.
    Optional filter by status.
    Returns visits assigned to current doctor only.
    """
    service = VisitService(db)
    effective_department_id = _resolve_department_filter(
        current_user=current_user,
        requested_department_id=department_id,
    )
    visits = service.get_queue_for_doctor(
        clinic_id=current_user.clinic_id,
        doctor_id=current_user.id,
        status=status,
        department_id=effective_department_id,
    )
    _attach_patient_names(db, visits)
    _attach_consultation_status(db, visits)
    return visits


@router.get("/recent", response_model=list[VisitResponse])
def get_recent_visits(
    limit: int = 10,
    department_id: UUID | None = None,
    db=Depends(get_db),
    current_user=Depends(require_reception),
):
    effective_department_id = _resolve_department_filter(
        current_user=current_user,
        requested_department_id=department_id,
    )
    visits = VisitService(db).get_queue_for_clinic(
        clinic_id=current_user.clinic_id,
        status=None,
        department_id=effective_department_id,
    )
    visits = sorted(visits, key=lambda v: v.updated_at, reverse=True)[:limit]
    _attach_patient_names(db, visits)
    return visits


# Get visit details
@router.get(
    "/{visit_id}",
    response_model=VisitResponse,
)
def get_visit(
    visit_id: UUID,
    purpose_of_use: PurposeOfUse = Query(...),
    justification: str = Query(..., min_length=2),
    break_glass: bool = Query(False),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    if break_glass:
        AccessLogService(db).log_break_glass(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="VISIT_DETAIL",
        )
    else:
        AccessLogService(db).log_chart_read(
            actor=current_user,
            clinic_id=current_user.clinic_id,
            patient_id=visit.patient_id,
            purpose_of_use=purpose_of_use,
            justification=justification,
            resource="VISIT_DETAIL",
        )
    _attach_patient_name(db, visit)
    return visit


@router.post(
    "/{visit_id}/intake-flag",
    response_model=VisitResponse,
)
def set_intake_flag(
    visit_id: UUID,
    payload: VisitIntakeFlagRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    visit = (
        db.query(Visit)
        .filter(Visit.id == visit_id)
        .first()
    )

    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found",
        )

    if visit.clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-clinic access denied",
        )

    if payload.flagged:
        if current_user.role != UserRole.RECEPTION:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reception access required to flag emergency",
            )
    else:
        if current_user.role not in {UserRole.DOCTOR, UserRole.CLINIC_ADMIN}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinician access required to clear emergency flag",
            )

    flag = VisitIntakeFlag(
        id=uuid.uuid4(),
        clinic_id=visit.clinic_id,
        visit_id=visit.id,
        flagged=payload.flagged,
        reason=payload.reason,
        set_by=current_user.id,
        set_at=datetime.now(timezone.utc),
    )
    db.add(flag)
    db.commit()

    _attach_patient_name(db, visit)
    return visit
def _resolve_canonical_patient_id(db, *, clinic_id: UUID, patient_id: UUID) -> UUID:
    visited = set()
    current = patient_id
    for _ in range(10):
        if current in visited:
            return patient_id
        visited.add(current)
        mapping = (
            db.query(PatientIdentityMap)
            .filter(
                PatientIdentityMap.clinic_id == clinic_id,
                PatientIdentityMap.from_patient_id == current,
            )
            .first()
        )
        if not mapping:
            return current
        revoked = (
            db.query(IdentityMapRevocation)
            .filter(
                IdentityMapRevocation.clinic_id == clinic_id,
                IdentityMapRevocation.map_id == mapping.id,
            )
            .first()
        )
        if revoked:
            return current
        current = mapping.to_patient_id
    return patient_id


def _resolve_department_filter(*, current_user, requested_department_id: UUID | None) -> UUID | None:
    allowed_department_ids = getattr(current_user, "allowed_department_ids", None) or []
    current_department_id = getattr(current_user, "current_department_id", None)

    if requested_department_id is None:
        return current_department_id

    if allowed_department_ids and requested_department_id not in allowed_department_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department access denied",
        )
    return requested_department_id


def _attach_patient_name(db, visit: Visit) -> None:
    patient = (
        db.query(Patient)
        .filter(Patient.id == visit.patient_id)
        .first()
    )
    visit.patient_name = patient.full_name if patient else None
    canonical_id = _resolve_canonical_patient_id(
        db,
        clinic_id=visit.clinic_id,
        patient_id=visit.patient_id,
    )
    active_mrn = (
        db.query(PatientMRN.mrn)
        .filter(
            PatientMRN.patient_id == canonical_id,
            PatientMRN.clinic_id == visit.clinic_id,
            PatientMRN.status == MRNStatus.ACTIVE,
        )
        .first()
    )
    visit.patient_mrn = active_mrn[0] if active_mrn else None
    has_active_admission = (
        db.query(Admission)
        .filter(
            Admission.patient_id == visit.patient_id,
            Admission.clinic_id == visit.clinic_id,
            Admission.status == AdmissionStatus.ACTIVE,
        )
        .first()
    )
    visit.has_active_admission = has_active_admission is not None
    latest_flag = (
        db.query(VisitIntakeFlag)
        .filter(
            VisitIntakeFlag.visit_id == visit.id,
            VisitIntakeFlag.clinic_id == visit.clinic_id,
        )
        .order_by(VisitIntakeFlag.set_at.desc(), VisitIntakeFlag.id.desc())
        .first()
    )
    if latest_flag:
        visit.intake_emergency_flag = latest_flag.flagged
        visit.intake_emergency_reason = latest_flag.reason
        visit.intake_emergency_set_at = latest_flag.set_at
    else:
        visit.intake_emergency_flag = None
        visit.intake_emergency_reason = None
        visit.intake_emergency_set_at = None


def _attach_patient_names(db, visits: list[Visit]) -> None:
    if not visits:
        return
    clinic_id = visits[0].clinic_id
    patient_ids = {visit.patient_id for visit in visits}
    visit_ids = {visit.id for visit in visits}
    patients = (
        db.query(Patient)
        .filter(Patient.id.in_(patient_ids))
        .all()
    )
    patient_map = {patient.id: patient.full_name for patient in patients}
    canonical_map = {
        patient_id: _resolve_canonical_patient_id(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        for patient_id in patient_ids
    }
    canonical_ids = set(canonical_map.values())
    mrns = (
        db.query(PatientMRN.patient_id, PatientMRN.mrn)
        .filter(
            PatientMRN.patient_id.in_(canonical_ids),
            PatientMRN.clinic_id == clinic_id,
            PatientMRN.status == MRNStatus.ACTIVE,
        )
        .all()
    )
    mrn_map = {patient_id: mrn for patient_id, mrn in mrns}
    active_admission_links = (
        db.query(Admission.patient_id)
        .filter(
            Admission.patient_id.in_(patient_ids),
            Admission.clinic_id == clinic_id,
            Admission.status == AdmissionStatus.ACTIVE,
        )
        .all()
    )
    active_admission_set = {row[0] for row in active_admission_links}
    flags = (
        db.query(VisitIntakeFlag)
        .filter(
            VisitIntakeFlag.visit_id.in_(visit_ids),
            VisitIntakeFlag.clinic_id == clinic_id,
        )
        .order_by(
            VisitIntakeFlag.visit_id.asc(),
            VisitIntakeFlag.set_at.desc(),
            VisitIntakeFlag.id.desc(),
        )
        .all()
    )
    flag_map = {}
    for flag in flags:
        if flag.visit_id not in flag_map:
            flag_map[flag.visit_id] = flag
    for visit in visits:
        visit.patient_name = patient_map.get(visit.patient_id)
        canonical_id = canonical_map.get(visit.patient_id, visit.patient_id)
        visit.patient_mrn = mrn_map.get(canonical_id)
        visit.has_active_admission = visit.patient_id in active_admission_set
        latest_flag = flag_map.get(visit.id)
        if latest_flag:
            visit.intake_emergency_flag = latest_flag.flagged
            visit.intake_emergency_reason = latest_flag.reason
            visit.intake_emergency_set_at = latest_flag.set_at
        else:
            visit.intake_emergency_flag = None
            visit.intake_emergency_reason = None
            visit.intake_emergency_set_at = None


def _attach_consultation_status(db, visits: list[Visit]) -> None:
    if not visits:
        return
    visit_ids = [visit.id for visit in visits]
    consultations = (
        db.query(Consultation.visit_id, Consultation.completed_at)
        .filter(Consultation.visit_id.in_(visit_ids))
        .all()
    )
    status_map = {
        visit_id: "completed" if completed_at else "in_progress"
        for visit_id, completed_at in consultations
    }
    for visit in visits:
        visit.consultation_status = status_map.get(visit.id, "none")
