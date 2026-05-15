from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1._sse import build_snapshot_stream
from app.core.database import SessionLocal
from app.core.dependencies import get_db
from app.core.guards.pharmacy_role_guards import (
    require_pharmacy_inventory_write_user,
    require_pharmacy_store_dashboard_user,
)
from app.schemas.pharmacy_store import (
    PharmacyStoreAdjustmentRequest,
    PharmacyStoreDashboardResponse,
    PharmacyStoreStockActionResponse,
    PharmacyStoreReceiveStockRequest,
)
from app.schemas.pharmacy_supply import (
    PharmacyIssueVoucherCreateRequest,
    PharmacyIssueVoucherDispatchRequest,
    PharmacyIssueVoucherResponse,
    PharmacyReturnRequestReceiveRequest,
    PharmacyReturnRequestResponse,
    PharmacyReturnRequestReviewRequest,
)
from app.services.pharmacy_store_dashboard_service import PharmacyStoreDashboardService
from app.services.pharmacy_supply_service import PharmacySupplyService

router = APIRouter(prefix="/pharmacy-store", tags=["Pharmacy Store"])


@router.get(
    "/dashboard",
    response_model=PharmacyStoreDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_store_dashboard(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_store_dashboard_user),
):
    return PharmacyStoreDashboardService(db).get_dashboard(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
        store_unit_id=store_unit_id,
    )


@router.get(
    "/dashboard-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_store_dashboard(
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    store_unit_id: UUID | None = Query(default=None),
    current_user=Depends(require_pharmacy_store_dashboard_user),
):
    def load_snapshot():
        with SessionLocal() as stream_db:
            return PharmacyStoreDashboardService(stream_db).get_dashboard(
                clinic_id=current_user.clinic_id,
                start_date=start_date,
                end_date=end_date,
                store_unit_id=store_unit_id,
            )

    def signature_for(snapshot):
        with SessionLocal() as stream_db:
            return PharmacyStoreDashboardService(stream_db).snapshot_signature(snapshot)

    return build_snapshot_stream(
        request=request,
        event_name="pharmacy_store_dashboard_snapshot",
        load_snapshot=load_snapshot,
        signature_for=signature_for,
        payload_for=lambda snapshot: snapshot.model_dump(mode="json"),
        event_id_for=lambda snapshot: snapshot.generated_at.isoformat(),
    )


@router.get(
    "/issue-vouchers",
    response_model=list[PharmacyIssueVoucherResponse],
    status_code=status.HTTP_200_OK,
)
def list_store_issue_vouchers(
    store_unit_id: UUID = Query(...),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_store_dashboard_user),
):
    return PharmacySupplyService(db).list_store_issue_vouchers(
        clinic_id=current_user.clinic_id,
        store_unit_id=store_unit_id,
    )


@router.get(
    "/issue-vouchers/{voucher_id}",
    response_model=PharmacyIssueVoucherResponse,
    status_code=status.HTTP_200_OK,
)
def get_store_issue_voucher(
    voucher_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_store_dashboard_user),
):
    return PharmacySupplyService(db).get_issue_voucher(
        clinic_id=current_user.clinic_id,
        voucher_id=voucher_id,
    )


@router.post(
    "/issue-vouchers",
    response_model=PharmacyIssueVoucherResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_store_issue_voucher(
    payload: PharmacyIssueVoucherCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacySupplyService(db).create_issue_voucher(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.post(
    "/issue-vouchers/{voucher_id}/dispatch",
    response_model=PharmacyIssueVoucherResponse,
    status_code=status.HTTP_200_OK,
)
def dispatch_store_issue_voucher(
    voucher_id: UUID,
    payload: PharmacyIssueVoucherDispatchRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacySupplyService(db).dispatch_issue_voucher(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        voucher_id=voucher_id,
        payload=payload,
    )


@router.post(
    "/return-requests/{return_request_id}/review",
    response_model=PharmacyReturnRequestResponse,
    status_code=status.HTTP_200_OK,
)
def review_store_return_request(
    return_request_id: UUID,
    payload: PharmacyReturnRequestReviewRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacySupplyService(db).review_return_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        return_request_id=return_request_id,
        payload=payload,
    )


@router.post(
    "/return-requests/{return_request_id}/receive",
    response_model=PharmacyReturnRequestResponse,
    status_code=status.HTTP_200_OK,
)
def receive_store_return_request(
    return_request_id: UUID,
    payload: PharmacyReturnRequestReceiveRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacySupplyService(db).receive_return_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        return_request_id=return_request_id,
        payload=payload,
    )


@router.post(
    "/receive-stock",
    response_model=PharmacyStoreStockActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def receive_store_stock(
    payload: PharmacyStoreReceiveStockRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacyStoreDashboardService(db).receive_stock(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.post(
    "/adjustments",
    response_model=PharmacyStoreStockActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_store_adjustment(
    payload: PharmacyStoreAdjustmentRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacyStoreDashboardService(db).adjust_stock(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )
