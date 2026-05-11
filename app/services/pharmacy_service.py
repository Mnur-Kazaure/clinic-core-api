# app/services/pharmacy_service.py
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app.models.billing_item import BillingItem
from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.clinic import Clinic
from app.models.dispensation import Dispensation
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.pharmacy_unit_profile import PharmacyUnitProfile
from app.models.pharmacy_unit_stock_lot import PharmacyUnitStockLot
from app.models.prescription import Prescription
from app.models.prescription_fulfillment_event import PrescriptionFulfillmentEvent
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.visit import Visit
from app.services.pharmacy_catalog_governance_service import (
    PharmacyCatalogGovernanceService,
)
from app.services.event_service import EventService
from app.services.pharmacy_routing_service import PharmacyRoutingService
from app.services.visit.service import VisitService
from app.shared.enums import (
    BillingEntryType,
    BillingItemStatus,
    BillingReasonCode,
    PharmacyExceptionAuthorizationType,
    PharmacyPrescriptionWorkflowStatus,
    PharmacyUnitCategory,
    PrescriptionFulfillmentType,
    PrescriptionStatus,
    VisitStatus,
)
from app.core.system_actor import SystemUser


class PharmacyService:
    def __init__(self, db):
        self.db = db

    def _resolve_inventory_item_for_prescription(
        self,
        prescription: Prescription,
        *,
        lock: bool = False,
    ):
        query = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == prescription.clinic_id,
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
            )
        )
        if prescription.pharmacy_catalog_item_id is not None:
            query = query.filter(
                PharmacyInventoryItem.catalog_item_id == prescription.pharmacy_catalog_item_id
            )
        else:
            drug_name = (prescription.drug_name or "").strip()
            if not drug_name:
                return None
            query = query.filter(
                func.lower(PharmacyInventoryItem.generic_name) == drug_name.lower(),
            )
        if lock:
            query = query.with_for_update()
        return query.first()

    def initialize_prescription_workflow(
        self,
        *,
        prescription: Prescription,
        actor,
        auto_commit: bool = True,
    ) -> BillingItem:
        if prescription.billing_item_id is not None:
            item = (
                self.db.query(BillingItem)
                .filter(BillingItem.id == prescription.billing_item_id)
                .first()
            )
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Prescription billing linkage is inconsistent",
                )
            return item

        visit = (
            self.db.query(Visit)
            .filter(Visit.id == prescription.visit_id)
            .first()
        )
        if visit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

        patient = (
            self.db.query(Patient)
            .filter(Patient.id == visit.patient_id)
            .first()
        )
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        catalog_item, pricing_config, charge_catalog = (
            PharmacyCatalogGovernanceService(self.db).resolve_operational_item(
                clinic_id=prescription.clinic_id,
                catalog_item_id=prescription.pharmacy_catalog_item_id,
                drug_name=prescription.drug_name,
            )
        )
        display_name = PharmacyCatalogGovernanceService._display_name(catalog_item)

        routing = PharmacyRoutingService(self.db).resolve_assignment(
            clinic_id=prescription.clinic_id,
            visit=visit,
            patient=patient,
            scheme_type=None,
        )

        billing_item = BillingItem(
            id=uuid.uuid4(),
            clinic_id=prescription.clinic_id,
            patient_id=visit.patient_id,
            visit_id=visit.id,
            cashier_pay_point_id=routing.cashier_pay_point.id,
            charge_catalog_id=charge_catalog.id if charge_catalog is not None else None,
            pharmacy_catalog_item_id=catalog_item.id,
            pharmacy_pricing_config_id=pricing_config.id,
            charge_code=pricing_config.charge_code,
            item_name=display_name,
            service_type="MEDICATION",
            quantity=int(prescription.quantity_prescribed),
            unit_price_minor=int(pricing_config.unit_price_minor),
            total_minor=int(prescription.quantity_prescribed) * int(pricing_config.unit_price_minor),
            amount_paid_minor=0,
            currency=pricing_config.currency,
            status=BillingItemStatus.PENDING,
            created_by=actor.id,
            payment_reference=None,
            paid_at=None,
        )
        self.db.add(billing_item)
        self.db.flush()

        prescription.billing_item_id = billing_item.id
        prescription.pharmacy_catalog_item_id = catalog_item.id
        prescription.drug_name = catalog_item.generic_name
        prescription.assigned_dispensing_unit_id = routing.dispensing_unit.id
        prescription.assigned_cashier_pay_point_id = routing.cashier_pay_point.id
        prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
        prescription.exception_authorization_type = PharmacyExceptionAuthorizationType.NONE
        self.db.add(prescription)

        self.db.add(
            BillingLedgerEntry(
                clinic_id=prescription.clinic_id,
                patient_id=visit.patient_id,
                visit_id=visit.id,
                admission_id=None,
                entry_type=BillingEntryType.CHARGE,
                amount_minor=int(billing_item.total_minor),
                currency=pricing_config.currency,
                description=f"Medication: {display_name}",
                reason_code=BillingReasonCode.MEDICATION,
                charge_code=pricing_config.charge_code,
                external_ref=None,
                related_entry_id=None,
                actor_id=actor.id,
                actor_role=actor.role,
                occurred_at=datetime.now(timezone.utc),
            )
        )

        if auto_commit:
            self.db.commit()
            self.db.refresh(billing_item)

        return billing_item

    def mark_prescriptions_paid(self, *, billing_item_ids: set[uuid.UUID]) -> None:
        if not billing_item_ids:
            return
        prescriptions = (
            self.db.query(Prescription)
            .filter(Prescription.billing_item_id.in_(billing_item_ids))
            .all()
        )
        for prescription in prescriptions:
            if prescription.workflow_status in {
                PharmacyPrescriptionWorkflowStatus.DISPENSED,
                PharmacyPrescriptionWorkflowStatus.CANCELLED,
                PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
            }:
                continue
            prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
            self.db.add(prescription)

    def authorize_exception(
        self,
        *,
        prescription: Prescription,
        authorization_type: PharmacyExceptionAuthorizationType,
        actor_id,
        auto_commit: bool = True,
    ) -> Prescription:
        prescription.exception_authorization_type = authorization_type
        prescription.exception_authorized_by = actor_id
        prescription.exception_authorized_at = datetime.now(timezone.utc)
        if prescription.workflow_status not in {
            PharmacyPrescriptionWorkflowStatus.DISPENSED,
            PharmacyPrescriptionWorkflowStatus.CANCELLED,
            PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
        }:
            prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
        self.db.add(prescription)
        if auto_commit:
            self.db.commit()
            self.db.refresh(prescription)
        return prescription

    def reassign_prescription(
        self,
        *,
        prescription: Prescription,
        actor,
        target_unit_id,
        reason: str,
        note: str | None = None,
        auto_commit: bool = True,
    ) -> dict:
        if prescription.status in {
            PrescriptionStatus.DISPENSED,
            PrescriptionStatus.CANCELLED,
            PrescriptionStatus.EXTERNALLY_FULFILLED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription is no longer available for reassignment",
            )
        if prescription.workflow_status == PharmacyPrescriptionWorkflowStatus.IN_DISPENSE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription cannot be reassigned while dispensing is in progress",
            )
        if prescription.assigned_dispensing_unit_id == target_unit_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription is already assigned to the selected dispensing unit",
            )

        target_row = (
            self.db.query(ServiceLine, PharmacyUnitProfile)
            .join(PharmacyUnitProfile, PharmacyUnitProfile.service_line_id == ServiceLine.id)
            .filter(
                ServiceLine.clinic_id == prescription.clinic_id,
                ServiceLine.id == target_unit_id,
                PharmacyUnitProfile.unit_category != PharmacyUnitCategory.STORE,
            )
            .first()
        )
        if target_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target dispensing unit was not found",
            )

        previous_unit_id = prescription.assigned_dispensing_unit_id
        self._synchronize_readiness(prescription)
        prescription.assigned_dispensing_unit_id = target_unit_id
        self.db.add(prescription)

        EventService(self.db).build_event(
            event_type="PHARMACY_REASSIGNED",
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=prescription.clinic_id,
            emitter="pharmacy",
            patient_id=prescription.patient_id if hasattr(prescription, "patient_id") else None,
            payload={
                "prescription_id": str(prescription.id),
                "previous_unit_id": str(previous_unit_id) if previous_unit_id else None,
                "target_unit_id": str(target_unit_id),
                "workflow_status": prescription.workflow_status.value,
                "reason": reason,
                "note": note,
            },
        )
        if auto_commit:
            self.db.commit()
            self.db.refresh(prescription)
        return {
            "prescription_id": prescription.id,
            "previous_unit_id": previous_unit_id,
            "target_unit_id": target_unit_id,
            "workflow_status": prescription.workflow_status.value,
            "reason": reason,
            "note": note,
        }

    def dispense(self, visit, payload):
        prescription = (
            self.db.query(Prescription)
            .filter(Prescription.visit_id == visit.id)
            .order_by(Prescription.created_at.asc())
            .first()
        )

        if not prescription:
            raise ValueError("No prescription found for visit")

        return self.dispense_prescription(prescription, payload)

    def _synchronize_readiness(self, prescription: Prescription) -> None:
        if prescription.workflow_status in {
            PharmacyPrescriptionWorkflowStatus.DISPENSED,
            PharmacyPrescriptionWorkflowStatus.CANCELLED,
            PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED,
        }:
            return
        paid = self._is_prescription_item_paid(prescription)
        authorized = (
            prescription.exception_authorization_type
            != PharmacyExceptionAuthorizationType.NONE
        )
        if paid or authorized:
            prescription.workflow_status = (
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED
                if prescription.quantity_dispensed_total > 0
                and prescription.quantity_remaining > 0
                else PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE
            )
        else:
            prescription.workflow_status = (
                PharmacyPrescriptionWorkflowStatus.AWAITING_PAYMENT_CLEARANCE
            )
        self.db.add(prescription)

    def _is_prescription_item_paid(self, prescription: Prescription) -> bool:
        if prescription.billing_item_id is None:
            return False
        item = (
            self.db.query(BillingItem.status)
            .filter(BillingItem.id == prescription.billing_item_id)
            .first()
        )
        return bool(item and item.status == BillingItemStatus.PAID)

    def _resolve_local_stock_lot(
        self,
        *,
        prescription: Prescription,
        inventory_item: PharmacyInventoryItem,
        selected_unit_id,
        stock_lot_id,
        requested_qty: int,
    ) -> PharmacyUnitStockLot | None:
        if selected_unit_id is None:
            return None

        query = (
            self.db.query(PharmacyUnitStockLot)
            .filter(
                PharmacyUnitStockLot.clinic_id == prescription.clinic_id,
                PharmacyUnitStockLot.service_line_id == selected_unit_id,
                PharmacyUnitStockLot.inventory_item_id == inventory_item.id,
                PharmacyUnitStockLot.quantity_on_hand >= requested_qty,
            )
        )

        today = datetime.now(timezone.utc).date()
        query = query.filter(
            (PharmacyUnitStockLot.expiry_date.is_(None))
            | (PharmacyUnitStockLot.expiry_date >= today)
        )

        if stock_lot_id is not None:
            query = query.filter(PharmacyUnitStockLot.id == stock_lot_id)
        else:
            query = query.order_by(
                PharmacyUnitStockLot.expiry_date.asc().nulls_last(),
                PharmacyUnitStockLot.created_at.asc(),
            )

        return query.with_for_update().first()

    def dispense_prescription(self, prescription, payload):
        self._synchronize_readiness(prescription)

        if prescription.workflow_status not in {
            PharmacyPrescriptionWorkflowStatus.READY_TO_DISPENSE,
            PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription is awaiting payment clearance or authorized exception",
            )

        inventory_item = self._resolve_inventory_item_for_prescription(
            prescription,
            lock=True,
        )
        if inventory_item is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mapped pharmacy inventory item was not found",
            )

        terminal_event = (
            self.db.query(PrescriptionFulfillmentEvent)
            .filter(
                PrescriptionFulfillmentEvent.prescription_id == prescription.id,
                PrescriptionFulfillmentEvent.clinic_id == prescription.clinic_id,
            )
            .first()
        )
        if terminal_event:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription already fulfilled",
            )

        requested_qty = int(payload.quantity)
        if requested_qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dispense quantity must be greater than zero",
            )
        if requested_qty > int(prescription.quantity_remaining or 0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Dispense quantity exceeds the remaining prescribed quantity",
            )

        selected_unit_id = getattr(payload, "unit_id", None) or prescription.assigned_dispensing_unit_id
        if (
            prescription.assigned_dispensing_unit_id is not None
            and selected_unit_id != prescription.assigned_dispensing_unit_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dispense must be performed from the assigned dispensing unit",
            )

        stock_lot = self._resolve_local_stock_lot(
            prescription=prescription,
            inventory_item=inventory_item,
            selected_unit_id=selected_unit_id,
            stock_lot_id=getattr(payload, "stock_lot_id", None),
            requested_qty=requested_qty,
        )

        movement_note = f"Dispensed for prescription {prescription.id}"
        occurred_at = datetime.now(timezone.utc)
        if stock_lot is not None:
            stock_before = int(stock_lot.quantity_on_hand)
            stock_after = stock_before - requested_qty
            stock_lot.quantity_on_hand = stock_after
            self.db.add(stock_lot)
            movement_note = (
                f"{movement_note} from unit lot {stock_lot.batch_number}"
            )
        else:
            # Transitional compatibility while units are being stocked explicitly.
            # The enterprise target is unit-stock-only dispensing, but legacy demo
            # data still uses clinic-wide inventory without unit lots.
            if inventory_item.stock_quantity < requested_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Insufficient stock in assigned dispensing unit",
                )
            stock_before = int(inventory_item.stock_quantity)
            stock_after = stock_before - requested_qty
            inventory_item.stock_quantity = stock_after
            inventory_item.updated_by = payload.pharmacist_id
            self.db.add(inventory_item)
            movement_note = f"{movement_note} (legacy clinic inventory fallback)"

        dispensation = Dispensation(
            id=uuid.uuid4(),
            prescription_id=prescription.id,
            clinic_id=prescription.clinic_id,
            pharmacist_id=payload.pharmacist_id,
            quantity=payload.quantity,
            stock_lot_id=stock_lot.id if stock_lot is not None else None,
            batch_number=stock_lot.batch_number if stock_lot is not None else None,
            expiry_date=stock_lot.expiry_date if stock_lot is not None else None,
            dispensing_unit_id=selected_unit_id,
            created_at=occurred_at,
        )

        prescription.quantity_dispensed_total = int(
            prescription.quantity_dispensed_total or 0
        ) + requested_qty
        prescription.quantity_remaining = max(
            int(prescription.quantity_prescribed or 0)
            - int(prescription.quantity_dispensed_total or 0),
            0,
        )
        prescription.dispensed_by = payload.pharmacist_id

        is_full_completion = prescription.quantity_remaining == 0
        fulfillment_event = None
        if is_full_completion:
            fulfillment_event = PrescriptionFulfillmentEvent(
                id=uuid.uuid4(),
                clinic_id=prescription.clinic_id,
                prescription_id=prescription.id,
                actor_id=payload.pharmacist_id,
                fulfillment_type=PrescriptionFulfillmentType.DISPENSED_IN_HOUSE,
                quantity=payload.quantity,
                occurred_at=occurred_at,
            )

        records = [dispensation]
        if fulfillment_event is not None:
            records.append(fulfillment_event)
        records.append(
            PharmacyStockMovement(
                id=uuid.uuid4(),
                clinic_id=prescription.clinic_id,
                inventory_item_id=inventory_item.id,
                service_line_id=selected_unit_id,
                actor_id=payload.pharmacist_id,
                movement_type="DISPENSE",
                quantity_delta=-int(payload.quantity),
                stock_before=stock_before,
                stock_after=stock_after,
                note=movement_note,
                reference_type="DISPENSATION",
                reference_id=dispensation.id,
                occurred_at=occurred_at,
            )
        )

        if is_full_completion:
            prescription.status = PrescriptionStatus.DISPENSED
            prescription.dispensed_at = occurred_at
            prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.DISPENSED
        else:
            prescription.status = PrescriptionStatus.ISSUED
            prescription.workflow_status = (
                PharmacyPrescriptionWorkflowStatus.PARTIALLY_DISPENSED
            )
        self.db.add(prescription)
        EventService(self.db).build_event(
            event_type=(
                "PHARMACY_FULLY_DISPENSED"
                if is_full_completion
                else "PHARMACY_PARTIAL_DISPENSED"
            ),
            actor_id=payload.pharmacist_id,
            actor_role="PHARMACY",
            clinic_id=prescription.clinic_id,
            emitter="pharmacy",
            patient_id=getattr(prescription, "patient_id", None),
            payload={
                "prescription_id": str(prescription.id),
                "visit_id": str(prescription.visit_id),
                "dispensing_unit_id": str(selected_unit_id)
                if selected_unit_id
                else None,
                "billing_item_id": str(prescription.billing_item_id)
                if prescription.billing_item_id
                else None,
                "drug_name": prescription.drug_name,
                "batch_number": dispensation.batch_number,
                "stock_lot_id": str(dispensation.stock_lot_id)
                if dispensation.stock_lot_id
                else None,
                "quantity_dispensed": requested_qty,
                "quantity_dispensed_total": prescription.quantity_dispensed_total,
                "quantity_remaining": prescription.quantity_remaining,
                "workflow_status": prescription.workflow_status.value,
            },
        )

        self.db.add_all(records)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription already fulfilled",
            ) from None
        self.db.refresh(dispensation)
        dispensation.quantity_dispensed_total = prescription.quantity_dispensed_total
        dispensation.quantity_remaining = prescription.quantity_remaining
        dispensation.workflow_status = prescription.workflow_status
        dispensation.dispensed_at = occurred_at

        if is_full_completion:
            self._try_auto_complete_visit(prescription.visit_id)

        return dispensation

    def mark_dispensed_external(self, prescription, *, actor_id, note: str | None = None):
        self._synchronize_readiness(prescription)
        existing_event = (
            self.db.query(PrescriptionFulfillmentEvent)
            .filter(
                PrescriptionFulfillmentEvent.prescription_id == prescription.id,
                PrescriptionFulfillmentEvent.clinic_id == prescription.clinic_id,
            )
            .first()
        )
        if existing_event:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription already fulfilled",
            )

        fulfillment_event = PrescriptionFulfillmentEvent(
            id=uuid.uuid4(),
            clinic_id=prescription.clinic_id,
            prescription_id=prescription.id,
            actor_id=actor_id,
            fulfillment_type=PrescriptionFulfillmentType.DISPENSED_EXTERNAL,
            quantity=None,
            note=note,
            occurred_at=datetime.now(timezone.utc),
        )

        self.db.add(fulfillment_event)
        prescription.quantity_remaining = 0
        prescription.status = PrescriptionStatus.EXTERNALLY_FULFILLED
        prescription.workflow_status = PharmacyPrescriptionWorkflowStatus.EXTERNALLY_FULFILLED
        prescription.externally_fulfilled_at = fulfillment_event.occurred_at
        self.db.add(prescription)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Prescription already fulfilled",
            ) from None
        self.db.refresh(fulfillment_event)

        self._try_auto_complete_visit(prescription.visit_id)

        return fulfillment_event

    # Public recheck for dashboard refresh
    def recheck_auto_complete_visit(self, visit_id):
        self._try_auto_complete_visit(visit_id)
        return (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )

    # 🔒 INTERNAL ONLY — no router access
    def _try_auto_complete_visit(self, visit_id):
        visit = (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )

        if not visit:
            return

        # Must be pharmacy stage
        if visit.status != VisitStatus.PHARMACY_PENDING:
            return

        unresolved = (
            self.db.query(Prescription.id)
            .filter(
                Prescription.visit_id == visit.id,
                Prescription.status.notin_(
                    [
                        PrescriptionStatus.DISPENSED,
                        PrescriptionStatus.CANCELLED,
                        PrescriptionStatus.EXTERNALLY_FULFILLED,
                    ]
                ),
            )
            .count()
        )

        if unresolved > 0:
            return

        # ✅ Auto-complete visit as SYSTEM
        VisitService(self.db).transition_visit(
            visit_id=visit.id,
            to_status=VisitStatus.COMPLETED,
            user=SystemUser,
        )
