# app/core/guards/lab_guards.py
from fastapi import Depends, HTTPException, Query, status
from uuid import UUID

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.billing_item import BillingItem
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_specimen import LabSpecimen
from app.models.service_line import ServiceLine
from app.models.visit import Visit
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_unit_access_service import LabUnitAccessService
from app.shared.enums import (
    BillingItemStatus,
    LAB_OPERATION_ROLES,
    LabRequestStatus,
    UserRole,
    VisitStatus,
)


def _role_value(raw_role) -> str:
    return raw_role.value if hasattr(raw_role, "value") else str(raw_role)


def require_lab_access(
    visit_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if _role_value(current_user.role) not in {role.value for role in LAB_OPERATION_ROLES}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lab staff may access lab operations",
        )

    visit = db.query(Visit).filter(Visit.id == visit_id).first()
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

    if visit.status != VisitStatus.LAB_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lab access denied. Visit is in state {visit.status}",
        )

    lab_request = (
        db.query(LabRequest)
        .filter(LabRequest.visit_id == visit.id)
        .first()
    )
    if not lab_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No lab request exists for this visit",
        )

    if lab_request.status == LabRequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lab request already completed",
        )

    return visit


def require_lab_manager_user(user=Depends(get_current_user)):
    if _role_value(user.role) != UserRole.LAB_MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab manager access required",
        )
    return user


def require_lab_selected_unit(
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> ServiceLine:
    if _role_value(current_user.role) not in {role.value for role in LAB_OPERATION_ROLES}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access required",
        )
    return LabUnitAccessService(db).resolve_selected_unit(
        clinic_id=current_user.clinic_id,
        user=current_user,
        selected_unit_id=unit_id,
    )


def _require_lab_request_access_base(
    lab_request_id: UUID,
    *,
    db,
    current_user,
    selected_unit: ServiceLine,
    enforce_visit_status: bool,
) -> LabRequest:
    if _role_value(current_user.role) not in {role.value for role in LAB_OPERATION_ROLES}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access required",
        )

    lab_request = (
        db.query(LabRequest)
        .filter(LabRequest.id == lab_request_id)
        .first()
    )
    if not lab_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab request not found",
        )

    visit = (
        db.query(Visit)
        .filter(Visit.id == lab_request.visit_id)
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

    if enforce_visit_status and visit.status != VisitStatus.LAB_REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lab access denied. Visit is in state {visit.status}",
        )

    if lab_request.billing_item_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access denied until payment is verified",
        )

    billing_item = (
        db.query(BillingItem.status)
        .filter(BillingItem.id == lab_request.billing_item_id)
        .first()
    )
    if billing_item is None or billing_item.status != BillingItemStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access denied until payment is verified",
        )

    lab_request, _ = LabFoundationService(db).reconcile_request_configuration(
        lab_request=lab_request,
        auto_commit=True,
    )
    if lab_request.target_unit_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lab request is not yet routed to a configured lab unit",
        )
    if lab_request.target_unit_id != selected_unit.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected lab unit does not match this lab request",
        )

    return lab_request


def require_lab_request_access_for_result(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
) -> LabRequest:
    lab_request = _require_lab_request_access_base(
        lab_request_id=lab_request_id,
        db=db,
        current_user=current_user,
        selected_unit=selected_unit,
        enforce_visit_status=True,
    )

    if lab_request.status == LabRequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lab request already completed",
        )

    return lab_request


def require_lab_request_access_for_complete(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
) -> LabRequest:
    return _require_lab_request_access_base(
        lab_request_id=lab_request_id,
        db=db,
        current_user=current_user,
        selected_unit=selected_unit,
        enforce_visit_status=True,
    )


def require_lab_request_access_for_read(
    lab_request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
    selected_unit: ServiceLine = Depends(require_lab_selected_unit),
) -> LabRequest:
    return _require_lab_request_access_base(
        lab_request_id=lab_request_id,
        db=db,
        current_user=current_user,
        selected_unit=selected_unit,
        enforce_visit_status=False,
    )


def require_lab_result_access(
    result_id: UUID,
    db=Depends(get_db),
    selected_unit=Depends(require_lab_selected_unit),
) -> LabResult:
    result = db.query(LabResult).filter(LabResult.id == result_id).first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab result not found",
        )

    request_id = result.request_item_id or result.lab_request_id
    lab_request = db.query(LabRequest).filter(LabRequest.id == request_id).first()
    if lab_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab request not found for result",
        )
    if lab_request.target_unit_id != selected_unit.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected lab unit does not match this lab result",
        )
    return result


def require_lab_specimen_access(
    specimen_id: UUID,
    db=Depends(get_db),
    selected_unit=Depends(require_lab_selected_unit),
) -> LabSpecimen:
    specimen = db.query(LabSpecimen).filter(LabSpecimen.id == specimen_id).first()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specimen not found",
        )
    if specimen.target_unit_id != selected_unit.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Selected lab unit does not match this specimen",
        )
    return specimen


def require_lab_user(user=Depends(get_current_user)):
    if _role_value(user.role) not in {role.value for role in LAB_OPERATION_ROLES}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lab access required",
        )
    return user
