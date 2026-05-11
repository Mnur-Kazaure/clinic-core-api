from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import get_db
from app.core.guards.pharmacy_role_guards import require_cmd_dashboard_user
from app.schemas.pharmacy_catalog import (
    PharmacyCatalogRegistryRowResponse,
    PharmacyCatalogRequestReviewRequest,
)
from app.schemas.pharmacy_supply import (
    PharmacyRefillRequestResponse,
    PharmacyRefillRequestReviewRequest,
)
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.shared.enums import PharmacyRefillRequestStatus

router = APIRouter(prefix="/pharmacy-cmd", tags=["Pharmacy CMD"])


@router.get(
    "/refill-requests",
    response_model=list[PharmacyRefillRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_cmd_refill_requests(
    status_filter: PharmacyRefillRequestStatus | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_cmd_dashboard_user),
):
    return PharmacySupplyService(db).list_cmd_refill_requests(
        clinic_id=current_user.clinic_id,
        status_filter=status_filter,
    )


@router.get(
    "/refill-requests/{request_id}",
    response_model=PharmacyRefillRequestResponse,
    status_code=status.HTTP_200_OK,
)
def get_cmd_refill_request(
    request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_cmd_dashboard_user),
):
    return PharmacySupplyService(db).get_refill_request(
        clinic_id=current_user.clinic_id,
        request_id=request_id,
    )


@router.post(
    "/refill-requests/{request_id}/review",
    response_model=PharmacyRefillRequestResponse,
    status_code=status.HTTP_200_OK,
)
def review_cmd_refill_request(
    request_id: UUID,
    payload: PharmacyRefillRequestReviewRequest,
    db=Depends(get_db),
    current_user=Depends(require_cmd_dashboard_user),
):
    return PharmacySupplyService(db).review_refill_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        request_id=request_id,
        payload=payload,
    )


@router.get(
    "/catalog-requests",
    response_model=list[PharmacyCatalogRegistryRowResponse],
    status_code=status.HTTP_200_OK,
)
def list_cmd_catalog_requests(
    db=Depends(get_db),
    current_user=Depends(require_cmd_dashboard_user),
):
    return PharmacyCatalogGovernanceService(db).list_catalog_items(
        clinic_id=current_user.clinic_id,
    )


@router.post(
    "/catalog-requests/{item_id}/review",
    response_model=PharmacyCatalogRegistryRowResponse,
    status_code=status.HTTP_200_OK,
)
def review_cmd_catalog_request(
    item_id: UUID,
    payload: PharmacyCatalogRequestReviewRequest,
    db=Depends(get_db),
    current_user=Depends(require_cmd_dashboard_user),
):
    return PharmacyCatalogGovernanceService(db).review_catalog_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        item_id=item_id,
        payload=payload,
    )
