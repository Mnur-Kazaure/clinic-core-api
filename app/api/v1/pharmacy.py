from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status, HTTPException, Query, Request
from uuid import UUID

from app.api.v1._sse import build_snapshot_stream
from app.core.database import SessionLocal
from app.core.guards.pharmacy_guards import (
    require_pharmacy_access,
    require_pharmacy_inventory_user,
    require_pharmacy_user,
)
from app.core.guards.pharmacy_role_guards import (
    require_pharmacy_inventory_write_user,
)
from app.core.guards.pharmacy_prescription_guards import require_pharmacy_for_dispense
from app.services.pharmacy_inventory_service import PharmacyInventoryService
from app.services.pharmacy_dispensing_dashboard_service import (
    PharmacyDispensingDashboardService,
)
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy_inventory import (
    PharmacyAccessModeResponse,
    PharmacyInventoryCreateRequest,
    PharmacyInventoryItemResponse,
    PharmacyInventoryListResponse,
    PharmacyInventoryOverviewResponse,
    PharmacyInventoryUpdateRequest,
    PharmacyRestockRequest,
    PharmacyStockMovementListResponse,
)
from app.schemas.pharmacy import (
    DispensingReassignmentCreate,
    DispensingReassignmentResponse,
    DispenseCreate,
    DispenseResponse,
    ExternalFulfillCreate,
    PrescriptionFulfillmentResponse,
)
from app.schemas.pharmacy_supply import (
    PharmacyIssueVoucherAcknowledgeRequest,
    PharmacyIssueVoucherResponse,
    PharmacyRefillRequestCreateRequest,
    PharmacyRefillRequestResponse,
    PharmacyReturnRequestCreateRequest,
    PharmacyReturnRequestResponse,
)
from app.schemas.pharmacy_workspace import PharmacyDispensingDashboardResponse
from app.schemas.prescription import PrescriptionResponse
from app.core.dependencies import get_db
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.billing_item import BillingItem
from app.models.cashier_pay_point import CashierPayPoint
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.patient_mrn import PatientMRN
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.dispensation import Dispensation
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.pharmacy_unit_access_service import PharmacyUnitAccessService
from app.services.pharmacy_supply_service import PharmacySupplyService
from app.shared.enums import (
    ClinicalPriorityLevel,
    PharmacyRefillRequestStatus,
    PharmacyPrescriptionWorkflowStatus,
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    MRNStatus,
    VisitStatus,
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])

# -----------------------------
# Helpers
# -----------------------------

def _resolve_canonical_patient_id(
    db,
    *,
    clinic_id: UUID,
    patient_id: UUID,
) -> UUID:
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


def _attach_patient_info(
    db,
    *,
    clinic_id: UUID,
    prescriptions: list[Prescription],
) -> None:
    if not prescriptions:
        return
    visit_ids = {prescription.visit_id for prescription in prescriptions}
    visits = db.query(Visit).filter(Visit.id.in_(visit_ids)).all()
    visit_map = {visit.id: visit for visit in visits}
    patient_ids = {visit.patient_id for visit in visits}
    patients = db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
    patient_name_map = {patient.id: patient.full_name for patient in patients}
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
    prescriber_ids = {prescription.prescribed_by for prescription in prescriptions}
    dispenser_ids = {
        prescription.dispensed_by
        for prescription in prescriptions
        if prescription.dispensed_by
    }
    user_ids = prescriber_ids | dispenser_ids
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {user.id: user for user in users}

    for prescription in prescriptions:
        visit = visit_map.get(prescription.visit_id)
        if not visit:
            prescription.patient_id = None
            prescription.patient_name = None
            prescription.patient_mrn = None
            prescription.prescribed_by_name = None
            prescription.prescribed_by_role = None
            prescription.dispensed_by_name = None
            prescription.dispensed_by_role = None
            continue
        prescription.patient_id = visit.patient_id
        prescription.patient_name = patient_name_map.get(visit.patient_id)
        canonical_id = canonical_map.get(visit.patient_id, visit.patient_id)
        prescription.patient_mrn = mrn_map.get(canonical_id)
        prescriber = user_map.get(prescription.prescribed_by)
        prescription.prescribed_by_name = (
            prescriber.full_name if prescriber else None
        )
        prescription.prescribed_by_role = (
            prescriber.role if prescriber else None
        )
        dispenser = (
            user_map.get(prescription.dispensed_by)
            if prescription.dispensed_by
            else None
        )
        prescription.dispensed_by_name = (
            dispenser.full_name if dispenser else None
        )
        prescription.dispensed_by_role = (
            dispenser.role if dispenser else None
        )


def _attach_pharmacy_context(
    db,
    *,
    prescriptions: list[Prescription],
) -> None:
    if not prescriptions:
        return

    billing_item_ids = {
        prescription.billing_item_id
        for prescription in prescriptions
        if prescription.billing_item_id is not None
    }
    unit_ids = {
        prescription.assigned_dispensing_unit_id
        for prescription in prescriptions
        if prescription.assigned_dispensing_unit_id is not None
    }
    pay_point_ids = {
        prescription.assigned_cashier_pay_point_id
        for prescription in prescriptions
        if prescription.assigned_cashier_pay_point_id is not None
    }

    billing_items = (
        db.query(BillingItem)
        .filter(BillingItem.id.in_(billing_item_ids))
        .all()
        if billing_item_ids
        else []
    )
    units = (
        db.query(ServiceLine)
        .filter(ServiceLine.id.in_(unit_ids))
        .all()
        if unit_ids
        else []
    )
    pay_points = (
        db.query(CashierPayPoint)
        .filter(CashierPayPoint.id.in_(pay_point_ids))
        .all()
        if pay_point_ids
        else []
    )

    billing_map = {item.id: item for item in billing_items}
    unit_map = {unit.id: unit for unit in units}
    pay_point_map = {row.id: row for row in pay_points}

    for prescription in prescriptions:
        billing_item = (
            billing_map.get(prescription.billing_item_id)
            if prescription.billing_item_id
            else None
        )
        unit = (
            unit_map.get(prescription.assigned_dispensing_unit_id)
            if prescription.assigned_dispensing_unit_id
            else None
        )
        pay_point = (
            pay_point_map.get(prescription.assigned_cashier_pay_point_id)
            if prescription.assigned_cashier_pay_point_id
            else None
        )
        prescription.billing_status = billing_item.status.value if billing_item else None
        prescription.payment_cleared = bool(
            billing_item and billing_item.status.value == "PAID"
        )
        prescription.assigned_dispensing_unit_name = unit.name if unit else None
        prescription.assigned_cashier_pay_point_name = pay_point.name if pay_point else None


@router.get(
    "/inventory/overview",
    response_model=PharmacyInventoryOverviewResponse,
    status_code=status.HTTP_200_OK,
)
def get_inventory_overview(
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_user),
):
    return PharmacyInventoryService(db).get_inventory_overview(
        clinic_id=current_user.clinic_id
    )


@router.get(
    "/inventory",
    response_model=PharmacyInventoryListResponse,
    status_code=status.HTTP_200_OK,
)
def list_inventory(
    search: str | None = Query(default=None),
    stock_filter: str | None = Query(default="ALL"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_user),
):
    return PharmacyInventoryService(db).list_inventory(
        clinic_id=current_user.clinic_id,
        search=search,
        stock_filter=stock_filter,
        page=page,
        limit=limit,
    )


@router.post(
    "/inventory",
    response_model=PharmacyInventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_item(
    payload: PharmacyInventoryCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacyInventoryService(db).create_inventory_item(
        clinic_id=current_user.clinic_id,
        payload=payload,
        actor=current_user,
    )


@router.get(
    "/inventory/{item_id}",
    response_model=PharmacyInventoryItemResponse,
    status_code=status.HTTP_200_OK,
)
def get_inventory_item(
    item_id: UUID,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_user),
):
    return PharmacyInventoryService(db).get_inventory_item(
        clinic_id=current_user.clinic_id,
        item_id=item_id,
    )


@router.put(
    "/inventory/{item_id}",
    response_model=PharmacyInventoryItemResponse,
    status_code=status.HTTP_200_OK,
)
def update_inventory_item(
    item_id: UUID,
    payload: PharmacyInventoryUpdateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacyInventoryService(db).update_inventory_item(
        clinic_id=current_user.clinic_id,
        item_id=item_id,
        payload=payload,
        actor=current_user,
    )


@router.post(
    "/inventory/{item_id}/restock",
    response_model=PharmacyInventoryItemResponse,
    status_code=status.HTTP_200_OK,
)
def restock_inventory_item(
    item_id: UUID,
    payload: PharmacyRestockRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_write_user),
):
    return PharmacyInventoryService(db).restock_inventory_item(
        clinic_id=current_user.clinic_id,
        item_id=item_id,
        quantity=payload.quantity,
        note=payload.note,
        actor=current_user,
    )


@router.get(
    "/inventory/{item_id}/movements",
    response_model=PharmacyStockMovementListResponse,
    status_code=status.HTTP_200_OK,
)
def list_inventory_movements(
    item_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_user),
):
    return PharmacyInventoryService(db).list_item_movements(
        clinic_id=current_user.clinic_id,
        item_id=item_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/inventory/access-mode",
    response_model=PharmacyAccessModeResponse,
    status_code=status.HTTP_200_OK,
)
def get_inventory_access_mode(
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_inventory_user),
):
    return PharmacyInventoryService(db).get_access_mode(
        clinic_id=current_user.clinic_id
    )


@router.get(
    "/dashboard",
    response_model=PharmacyDispensingDashboardResponse,
    status_code=status.HTTP_200_OK,
)
def get_dispensing_dashboard(
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacyDispensingDashboardService(db).get_dashboard(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        selected_unit_id=unit_id,
    )


@router.get(
    "/dashboard-stream",
    status_code=status.HTTP_200_OK,
)
async def stream_dispensing_dashboard(
    request: Request,
    unit_id: UUID | None = Query(default=None),
    current_user=Depends(require_pharmacy_user),
):
    def load_snapshot():
        with SessionLocal() as stream_db:
            stream_user = stream_db.query(User).filter(User.id == current_user.id).first()
            return PharmacyDispensingDashboardService(stream_db).get_dashboard(
                clinic_id=current_user.clinic_id,
                actor=stream_user,
                selected_unit_id=unit_id,
            )

    def signature_for(snapshot):
        with SessionLocal() as stream_db:
            return PharmacyDispensingDashboardService(stream_db).snapshot_signature(snapshot)

    return build_snapshot_stream(
        request=request,
        event_name="pharmacy_dashboard_snapshot",
        load_snapshot=load_snapshot,
        signature_for=signature_for,
        payload_for=lambda snapshot: snapshot.model_dump(mode="json"),
        event_id_for=lambda snapshot: snapshot.generated_at.isoformat(),
    )


# GET /pharmacy/prescriptions?status=ISSUED
@router.get(
    "/prescriptions",
    response_model=list[PrescriptionResponse],
    status_code=status.HTTP_200_OK,
)
def list_prescriptions(
    status: PrescriptionStatus | None = None,
    workflow_status: PharmacyPrescriptionWorkflowStatus | None = None,
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    selected_unit = PharmacyUnitAccessService(db).resolve_selected_unit(
        clinic_id=current_user.clinic_id,
        user=current_user,
        selected_unit_id=unit_id,
    )
    q = (
        db.query(Prescription)
        .join(Visit, Prescription.visit_id == Visit.id)
        .filter(
            Visit.clinic_id == current_user.clinic_id,
            Prescription.assigned_dispensing_unit_id == selected_unit.id,
        )
    )

    if status is not None:
        q = q.filter(Prescription.status == status)
    if workflow_status is not None:
        q = q.filter(Prescription.workflow_status == workflow_status)
    q = q.filter(Visit.status != VisitStatus.CANCELLED)

    prescriptions = q.order_by(Prescription.issued_at.desc()).all()
    _attach_patient_info(
        db,
        clinic_id=current_user.clinic_id,
        prescriptions=prescriptions,
    )
    _attach_pharmacy_context(db, prescriptions=prescriptions)
    return prescriptions


@router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
def get_prescription(
    prescription_id: UUID,
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    prescription = (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id)
        .first()
    )

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )

    visit = (
        db.query(Visit)
        .filter(Visit.id == prescription.visit_id)
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

    selected_unit = PharmacyUnitAccessService(db).resolve_selected_unit(
        clinic_id=current_user.clinic_id,
        user=current_user,
        selected_unit_id=unit_id,
    )
    if (
        prescription.assigned_dispensing_unit_id is not None
        and prescription.assigned_dispensing_unit_id != selected_unit.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Prescription is outside your assigned dispensing unit",
        )
    _attach_patient_info(
        db,
        clinic_id=current_user.clinic_id,
        prescriptions=[prescription],
    )
    _attach_pharmacy_context(db, prescriptions=[prescription])
    source_line = (
        db.query(ServiceLine)
        .filter(ServiceLine.id == visit.service_line_id)
        .first()
        if visit.service_line_id is not None
        else None
    )
    prescription.source_department_name = (
        source_line.name if source_line is not None else visit.service_line.value
    )
    if (
        prescription.exception_authorization_type
        == getattr(
            type(prescription.exception_authorization_type),
            "EMERGENCY_OVERRIDE",
            None,
        )
    ):
        prescription.priority = "EMERGENCY"
    elif visit.triage_acuity == ClinicalPriorityLevel.CRITICAL:
        prescription.priority = "EMERGENCY"
    elif visit.triage_acuity == ClinicalPriorityLevel.URGENT:
        prescription.priority = "URGENT"
    else:
        prescription.priority = "ROUTINE"
    issued_at = (
        prescription.issued_at
        if getattr(prescription.issued_at, "tzinfo", None) is not None
        else prescription.issued_at.replace(tzinfo=timezone.utc)
    )
    prescription.aging_minutes = int(
        max(0, (datetime.now(timezone.utc) - issued_at).total_seconds() // 60)
    )
    detail_context = PharmacyDispensingDashboardService(db).get_prescription_detail_context(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        selected_unit_id=selected_unit.id,
        prescription=prescription,
    )
    prescription.available_stock_lots = detail_context["available_stock_lots"]
    prescription.local_stock_available_quantity = detail_context[
        "local_stock_available_quantity"
    ]
    prescription.local_stock_status = detail_context["local_stock_status"]
    prescription.local_stock_source = detail_context["local_stock_source"]
    prescription.reassignment_options = detail_context["reassignment_targets"]
    return prescription


# api/pharmacy/visits/{visit_id}/dispense (This endpoint triger auto-complation)
@router.post(
    "/{visit_id}/dispense",
    response_model=DispenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def dispense_medication(
    visit_id: UUID,
    payload: DispenseCreate,
    visit=Depends(require_pharmacy_access),  # 🔒 Guard enforced here
    db=Depends(get_db),
):
    service = PharmacyService(db)

    dispense = service.dispense(
        visit=visit,
        payload=payload,
    )

    return dispense


# POST /pharmacy/prescriptions/{prescription_id}/dispense
@router.post(
    "/prescriptions/{prescription_id}/dispense",
    response_model=DispenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def dispense_prescription(
    prescription_id: UUID,
    payload: DispenseCreate,
    prescription=Depends(require_pharmacy_for_dispense),
    db=Depends(get_db),
):
    service = PharmacyService(db)
    dispense = service.dispense_prescription(prescription, payload)
    return dispense


@router.post(
    "/prescriptions/{prescription_id}/fulfill-external",
    response_model=PrescriptionFulfillmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def fulfill_prescription_external(
    prescription_id: UUID,
    payload: ExternalFulfillCreate,
    prescription=Depends(require_pharmacy_for_dispense),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    """
    Mark a prescription as fulfilled outside the clinic (e.g., out of stock).
    This writes an append-only fulfillment event and participates in visit auto-completion.
    """
    service = PharmacyService(db)
    event = service.mark_dispensed_external(
        prescription,
        actor_id=current_user.id,
        note=payload.note,
    )
    return event


@router.post(
    "/prescriptions/{prescription_id}/reassign",
    response_model=DispensingReassignmentResponse,
    status_code=status.HTTP_200_OK,
)
def reassign_prescription(
    prescription_id: UUID,
    payload: DispensingReassignmentCreate,
    prescription=Depends(require_pharmacy_for_dispense),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacyService(db).reassign_prescription(
        prescription=prescription,
        actor=current_user,
        target_unit_id=payload.target_unit_id,
        reason=payload.reason,
        note=payload.note,
    )


@router.get(
    "/refill-requests",
    response_model=list[PharmacyRefillRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_unit_refill_requests(
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).list_unit_refill_requests(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        selected_unit_id=unit_id,
    )


@router.post(
    "/refill-requests",
    response_model=PharmacyRefillRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_refill_request(
    payload: PharmacyRefillRequestCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).create_refill_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.get(
    "/issue-vouchers",
    response_model=list[PharmacyIssueVoucherResponse],
    status_code=status.HTTP_200_OK,
)
def list_unit_issue_vouchers(
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).list_unit_issue_vouchers(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        selected_unit_id=unit_id,
    )


@router.get(
    "/issue-vouchers/{voucher_id}",
    response_model=PharmacyIssueVoucherResponse,
    status_code=status.HTTP_200_OK,
)
def get_unit_issue_voucher(
    voucher_id: UUID,
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    voucher = PharmacySupplyService(db).get_issue_voucher(
        clinic_id=current_user.clinic_id,
        voucher_id=voucher_id,
    )
    selected_unit = PharmacyUnitAccessService(db).resolve_selected_unit(
        clinic_id=current_user.clinic_id,
        user=current_user,
        selected_unit_id=unit_id,
    )
    if voucher["receiving_unit_id"] != selected_unit.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Issue voucher is outside your receiving unit scope",
        )
    return voucher


@router.get(
    "/return-requests",
    response_model=list[PharmacyReturnRequestResponse],
    status_code=status.HTTP_200_OK,
)
def list_unit_return_requests(
    unit_id: UUID | None = Query(default=None),
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).list_unit_return_requests(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        selected_unit_id=unit_id,
    )


@router.post(
    "/return-requests",
    response_model=PharmacyReturnRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_return_request(
    payload: PharmacyReturnRequestCreateRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).create_return_request(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        payload=payload,
    )


@router.post(
    "/issue-vouchers/{voucher_id}/acknowledge",
    response_model=PharmacyIssueVoucherResponse,
    status_code=status.HTTP_200_OK,
)
def acknowledge_issue_voucher(
    voucher_id: UUID,
    payload: PharmacyIssueVoucherAcknowledgeRequest,
    db=Depends(get_db),
    current_user=Depends(require_pharmacy_user),
):
    return PharmacySupplyService(db).acknowledge_issue_voucher(
        clinic_id=current_user.clinic_id,
        actor=current_user,
        voucher_id=voucher_id,
        payload=payload,
    )
