from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1._sse import build_snapshot_stream
from app.core.database import SessionLocal
from app.core.dependencies import get_db
from app.core.guards.pharmacy_role_guards import require_pharmacy_hod_dashboard_user
from app.schemas.pharmacy_inventory import (
    PharmacyInventoryOverviewResponse,
    PharmacyReportsSummaryResponse,
)
from app.schemas.pharmacy_hod import (
    PharmacyHodDashboardResponse,
    PharmacyHodStaffAssignmentUpdateRequest,
    PharmacyHodStaffSummaryResponse,
)
from app.schemas.pharmacy_catalog import (
    PharmacyCatalogRegistryRowResponse,
    PharmacyCatalogRequestCreateRequest,
)
from app.schemas.pharmacy_supply import (
    PharmacyIssueVoucherResponse,
    PharmacyRefillRequestResponse,
)
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.pharmacy_inventory_service import PharmacyInventoryService
from app.services.pharmacy_hod_dashboard_service import PharmacyHodDashboardService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.shared.enums import PharmacyRefillRequestStatus

router = APIRouter(prefix="/pharmacy-hod", tags=["Pharmacy HOD"])


@router.get(
    "/dashboard",
    response_model=PharmacyHodDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_pharmacy_hod_dashboard(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyHodDashboardService(db).get_dashboard(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dashboard-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_pharmacy_hod_dashboard(
    request: Request,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    def load_snapshot():
        with SessionLocal() as stream_db:
            return PharmacyHodDashboardService(stream_db).get_dashboard(
                clinic_id=current_user.clinic_id,
                start_date=start_date,
                end_date=end_date,
            )

    def signature_for(snapshot):
        with SessionLocal() as stream_db:
            return PharmacyHodDashboardService(stream_db).snapshot_signature(snapshot)

    return build_snapshot_stream(
        request=request,
        event_name="pharmacy_hod_dashboard_snapshot",
        load_snapshot=load_snapshot,
        signature_for=signature_for,
        payload_for=lambda snapshot: snapshot.model_dump(mode="json"),
        event_id_for=lambda snapshot: snapshot.generated_at.isoformat(),
    )


@router.put(
    "/staff/{staff_id}/assignment",
    response_model=PharmacyHodStaffSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def update_pharmacy_hod_staff_assignment(
    staff_id: UUID,
    payload: PharmacyHodStaffAssignmentUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyHodDashboardService(db).update_staff_assignment(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        staff_id=staff_id,
        payload=payload,
    )


@router.get(
    "/overview",
    response_model=PharmacyInventoryOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_pharmacy_hod_overview(
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyInventoryService(db).get_inventory_overview(
        clinic_id=current_user.clinic_id
    )


@router.get(
    "/reports/summary",
    response_model=PharmacyReportsSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def get_pharmacy_hod_reports_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyInventoryService(db).get_reports_summary(
        clinic_id=current_user.clinic_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/refill-requests",
    response_model=list[PharmacyRefillRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_hod_refill_requests(
    status_filter: PharmacyRefillRequestStatus | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacySupplyService(db).list_hod_refill_requests(
        clinic_id=current_user.clinic_id,
        status_filter=status_filter,
    )


@router.get(
    "/refill-requests/{request_id}",
    response_model=PharmacyRefillRequestResponse,
    status_code=status.HTTP_200_OK,
)
def get_hod_refill_request(
    request_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacySupplyService(db).get_refill_request(
        clinic_id=current_user.clinic_id,
        request_id=request_id,
    )


@router.get(
    "/issue-vouchers",
    response_model=list[PharmacyIssueVoucherResponse],
    status_code=status.HTTP_200_OK,
)
def list_hod_issue_vouchers(
    store_unit_id: UUID = Query(...),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacySupplyService(db).list_store_issue_vouchers(
        clinic_id=current_user.clinic_id,
        store_unit_id=store_unit_id,
    )


@router.get(
    "/catalog-requests",
    response_model=list[PharmacyCatalogRegistryRowResponse],
    status_code=status.HTTP_200_OK,
)
def list_hod_catalog_requests(
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyCatalogGovernanceService(db).list_catalog_items(
        clinic_id=current_user.clinic_id,
    )


@router.post(
    "/catalog-requests",
    response_model=PharmacyCatalogRegistryRowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hod_catalog_request(
    payload: PharmacyCatalogRequestCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_hod_dashboard_user),
):
    return PharmacyCatalogGovernanceService(db).create_catalog_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )
