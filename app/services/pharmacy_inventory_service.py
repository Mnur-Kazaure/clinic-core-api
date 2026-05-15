from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.clinic import Clinic
from app.models.dispensation import Dispensation
from app.models.pharmacy_access_setting import PharmacyAccessSetting
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_stock_movement import PharmacyStockMovement
from app.models.prescription import Prescription
from app.models.user import User
from app.shared.enums import UserRole


class PharmacyInventoryService:
    READABLE_FILTERS = {
        "ALL",
        "ACTIVE",
        "INACTIVE",
        "AVAILABLE",
        "LOW_STOCK",
        "OUT_OF_STOCK",
    }

    def __init__(self, db: Session):
        self.db = db

    def _resolve_currency(self, *, clinic_id: UUID) -> str:
        return (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

    @staticmethod
    def _as_role_value(role) -> str:
        return getattr(role, "value", str(role))

    def _get_or_create_access_setting(self, *, clinic_id: UUID) -> PharmacyAccessSetting:
        setting = (
            self.db.query(PharmacyAccessSetting)
            .filter(PharmacyAccessSetting.clinic_id == clinic_id)
            .first()
        )
        if setting is not None:
            return setting

        setting = PharmacyAccessSetting(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            inventory_mode="EDITABLE",
            changed_by=None,
            changed_at=datetime.now(timezone.utc),
        )
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def _assert_inventory_write_access(self, *, clinic_id: UUID, actor) -> None:
        role = self._as_role_value(actor.role)
        if role != UserRole.PHARMACY_STORE_OFFICER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only pharmacy store officers can modify store inventory",
            )

        setting = self._get_or_create_access_setting(clinic_id=clinic_id)
        if setting.inventory_mode != "EDITABLE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inventory edit mode is disabled by Pharmacy HOD",
            )

    def _resolve_stock_filter(self, value: str | None) -> str:
        resolved = (value or "ALL").strip().upper()
        if resolved not in self.READABLE_FILTERS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported stock filter '{value}'",
            )
        return resolved

    def _resolve_report_window(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[date, date, datetime, datetime]:
        today = datetime.now(timezone.utc).date()
        effective_start = start_date or end_date or today
        effective_end = end_date or start_date or today

        if effective_start > effective_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="start_date cannot be later than end_date",
            )

        start_at = datetime.combine(effective_start, time.min, tzinfo=timezone.utc)
        end_at = datetime.combine(
            effective_end + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        return effective_start, effective_end, start_at, end_at

    def _movement_to_dict(self, movement: PharmacyStockMovement, actor_name: str | None = None) -> dict:
        return {
            "id": movement.id,
            "clinic_id": movement.clinic_id,
            "inventory_item_id": movement.inventory_item_id,
            "actor_id": movement.actor_id,
            "actor_name": actor_name,
            "movement_type": movement.movement_type,
            "quantity_delta": int(movement.quantity_delta),
            "stock_before": int(movement.stock_before),
            "stock_after": int(movement.stock_after),
            "note": movement.note,
            "reference_type": movement.reference_type,
            "reference_id": movement.reference_id,
            "occurred_at": movement.occurred_at,
        }

    def get_access_mode(self, *, clinic_id: UUID) -> dict:
        setting = self._get_or_create_access_setting(clinic_id=clinic_id)
        actor_name = None
        if setting.changed_by is not None:
            actor_name = (
                self.db.query(User.full_name)
                .filter(User.id == setting.changed_by)
                .scalar()
            )
        return {
            "inventory_mode": setting.inventory_mode,
            "changed_by": setting.changed_by,
            "changed_by_name": actor_name,
            "changed_at": setting.changed_at,
        }

    def update_access_mode(self, *, clinic_id: UUID, inventory_mode: str, actor) -> dict:
        resolved_mode = inventory_mode.strip().upper()
        if resolved_mode not in {"EDITABLE", "READ_ONLY"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="inventory_mode must be EDITABLE or READ_ONLY",
            )

        setting = self._get_or_create_access_setting(clinic_id=clinic_id)
        setting.inventory_mode = resolved_mode
        setting.changed_by = actor.id
        setting.changed_at = datetime.now(timezone.utc)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return self.get_access_mode(clinic_id=clinic_id)

    def list_inventory(
        self,
        *,
        clinic_id: UUID,
        search: str | None = None,
        stock_filter: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        resolved_filter = self._resolve_stock_filter(stock_filter)
        page = max(1, page)
        limit = max(1, min(limit, 100))

        query = self.db.query(PharmacyInventoryItem).filter(
            PharmacyInventoryItem.clinic_id == clinic_id
        )

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(PharmacyInventoryItem.generic_name).like(term),
                    func.lower(
                        func.coalesce(PharmacyInventoryItem.brand_name, "")
                    ).like(term),
                )
            )

        if resolved_filter == "ACTIVE":
            query = query.filter(PharmacyInventoryItem.lifecycle_status == "ACTIVE")
        elif resolved_filter == "INACTIVE":
            query = query.filter(PharmacyInventoryItem.lifecycle_status == "INACTIVE")
        elif resolved_filter == "AVAILABLE":
            query = query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity > PharmacyInventoryItem.low_stock_threshold,
            )
        elif resolved_filter == "LOW_STOCK":
            query = query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity > 0,
                PharmacyInventoryItem.stock_quantity <= PharmacyInventoryItem.low_stock_threshold,
            )
        elif resolved_filter == "OUT_OF_STOCK":
            query = query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity == 0,
            )

        total = int(query.with_entities(func.count(PharmacyInventoryItem.id)).scalar() or 0)
        rows = (
            query.order_by(
                PharmacyInventoryItem.generic_name.asc(),
                PharmacyInventoryItem.updated_at.desc(),
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return {
            "data": rows,
            "total": total,
            "page": page,
            "limit": limit,
        }

    def get_inventory_item(self, *, clinic_id: UUID, item_id: UUID) -> PharmacyInventoryItem:
        item = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.id == item_id,
                PharmacyInventoryItem.clinic_id == clinic_id,
            )
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )
        return item

    def create_inventory_item(self, *, clinic_id: UUID, payload, actor) -> PharmacyInventoryItem:
        self._assert_inventory_write_access(clinic_id=clinic_id, actor=actor)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Store inventory master creation is disabled. Activate the item through "
                "Pharmacy HOD request, CMD approval, and Accounts pricing first."
            ),
        )

    def update_inventory_item(
        self,
        *,
        clinic_id: UUID,
        item_id: UUID,
        payload,
        actor,
    ) -> PharmacyInventoryItem:
        self._assert_inventory_write_access(clinic_id=clinic_id, actor=actor)
        item = self.get_inventory_item(clinic_id=clinic_id, item_id=item_id)

        previous_status = item.lifecycle_status
        movement_note = payload.note.strip() if payload.note else None

        if payload.low_stock_threshold is not None:
            item.low_stock_threshold = int(payload.low_stock_threshold)
        if payload.lifecycle_status is not None:
            item.lifecycle_status = payload.lifecycle_status.strip().upper()

        item.updated_by = actor.id
        self.db.add(item)
        self.db.flush()

        now = datetime.now(timezone.utc)
        if item.lifecycle_status != previous_status:
            movement_type = "ACTIVATED" if item.lifecycle_status == "ACTIVE" else "INACTIVATED"
            self.db.add(
                PharmacyStockMovement(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    inventory_item_id=item.id,
                    actor_id=actor.id,
                    movement_type=movement_type,
                    quantity_delta=0,
                    stock_before=item.stock_quantity,
                    stock_after=item.stock_quantity,
                    note=movement_note,
                    reference_type="INVENTORY_UPDATE",
                    reference_id=item.id,
                    occurred_at=now,
                )
            )

        self.db.commit()
        self.db.refresh(item)
        return item

    def restock_inventory_item(
        self,
        *,
        clinic_id: UUID,
        item_id: UUID,
        quantity: int,
        note: str | None,
        actor,
    ) -> PharmacyInventoryItem:
        self._assert_inventory_write_access(clinic_id=clinic_id, actor=actor)

        item = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.id == item_id,
                PharmacyInventoryItem.clinic_id == clinic_id,
            )
            .with_for_update()
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found",
            )

        stock_before = int(item.stock_quantity)
        stock_after = stock_before + int(quantity)
        now = datetime.now(timezone.utc)

        item.stock_quantity = stock_after
        item.last_restocked_at = now
        item.updated_by = actor.id
        self.db.add(item)
        self.db.add(
            PharmacyStockMovement(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                inventory_item_id=item.id,
                actor_id=actor.id,
                movement_type="RESTOCK",
                quantity_delta=int(quantity),
                stock_before=stock_before,
                stock_after=stock_after,
                note=note.strip() if note else None,
                reference_type="RESTOCK",
                reference_id=item.id,
                occurred_at=now,
            )
        )

        self.db.commit()
        self.db.refresh(item)
        return item

    def list_item_movements(
        self,
        *,
        clinic_id: UUID,
        item_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        self.get_inventory_item(clinic_id=clinic_id, item_id=item_id)
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        query = (
            self.db.query(PharmacyStockMovement, User.full_name.label("actor_name"))
            .join(User, User.id == PharmacyStockMovement.actor_id)
            .filter(
                PharmacyStockMovement.clinic_id == clinic_id,
                PharmacyStockMovement.inventory_item_id == item_id,
            )
        )
        total = int(
            query.with_entities(func.count(PharmacyStockMovement.id)).order_by(None).scalar()
            or 0
        )
        rows = (
            query.order_by(PharmacyStockMovement.occurred_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        data = [self._movement_to_dict(movement, actor_name) for movement, actor_name in rows]
        return {
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_reports_summary(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        resolved_start, resolved_end, start_at, end_at = self._resolve_report_window(
            start_date=start_date,
            end_date=end_date,
        )

        movement_query = self.db.query(PharmacyStockMovement).filter(
            PharmacyStockMovement.clinic_id == clinic_id,
            PharmacyStockMovement.occurred_at >= start_at,
            PharmacyStockMovement.occurred_at < end_at,
        )

        total_movements = int(
            movement_query.with_entities(func.count(PharmacyStockMovement.id)).scalar()
            or 0
        )

        restock_units = int(
            movement_query.filter(PharmacyStockMovement.movement_type == "RESTOCK")
            .with_entities(func.coalesce(func.sum(PharmacyStockMovement.quantity_delta), 0))
            .scalar()
            or 0
        )

        dispensed_units = int(
            movement_query.filter(PharmacyStockMovement.movement_type == "DISPENSE")
            .with_entities(
                func.coalesce(func.sum(func.abs(PharmacyStockMovement.quantity_delta)), 0)
            )
            .scalar()
            or 0
        )

        price_updates = int(
            movement_query.filter(PharmacyStockMovement.movement_type == "PRICE_UPDATE")
            .with_entities(func.count(PharmacyStockMovement.id))
            .scalar()
            or 0
        )

        lifecycle_changes = int(
            movement_query.filter(
                PharmacyStockMovement.movement_type.in_(["ACTIVATED", "INACTIVATED"])
            )
            .with_entities(func.count(PharmacyStockMovement.id))
            .scalar()
            or 0
        )

        base_inventory_query = self.db.query(PharmacyInventoryItem).filter(
            PharmacyInventoryItem.clinic_id == clinic_id
        )

        low_stock_items = int(
            base_inventory_query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity > 0,
                PharmacyInventoryItem.stock_quantity
                <= PharmacyInventoryItem.low_stock_threshold,
            )
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        out_of_stock_items = int(
            base_inventory_query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity == 0,
            )
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        inventory_value_minor = int(
            base_inventory_query.filter(PharmacyInventoryItem.lifecycle_status == "ACTIVE")
            .with_entities(
                func.coalesce(
                    func.sum(
                        PharmacyInventoryItem.stock_quantity
                        * PharmacyInventoryItem.selling_price_minor
                    ),
                    0,
                )
            )
            .scalar()
            or 0
        )

        recent_rows = (
            self.db.query(PharmacyStockMovement, User.full_name.label("actor_name"))
            .join(User, User.id == PharmacyStockMovement.actor_id)
            .filter(
                PharmacyStockMovement.clinic_id == clinic_id,
                PharmacyStockMovement.occurred_at >= start_at,
                PharmacyStockMovement.occurred_at < end_at,
            )
            .order_by(PharmacyStockMovement.occurred_at.desc())
            .limit(10)
            .all()
        )
        recent_movements = [
            self._movement_to_dict(movement, actor_name)
            for movement, actor_name in recent_rows
        ]

        return {
            "start_date": resolved_start,
            "end_date": resolved_end,
            "total_movements": total_movements,
            "restock_units": restock_units,
            "dispensed_units": dispensed_units,
            "price_updates": price_updates,
            "lifecycle_changes": lifecycle_changes,
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "inventory_value_minor": inventory_value_minor,
            "currency": self._resolve_currency(clinic_id=clinic_id),
            "recent_movements": recent_movements,
        }

    def list_report_movements(
        self,
        *,
        clinic_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        movement_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        resolved_start, resolved_end, start_at, end_at = self._resolve_report_window(
            start_date=start_date,
            end_date=end_date,
        )
        resolved_type = (movement_type or "ALL").strip().upper()
        allowed_types = {
            "ALL",
            "RESTOCK",
            "DISPENSE",
            "ADJUSTMENT",
            "PRICE_UPDATE",
            "ACTIVATED",
            "INACTIVATED",
        }
        if resolved_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unsupported movement_type '{movement_type}'",
            )

        page = max(1, page)
        limit = max(1, min(limit, 100))

        query = (
            self.db.query(
                PharmacyStockMovement,
                User.full_name.label("actor_name"),
                PharmacyInventoryItem.generic_name.label("generic_name"),
                PharmacyInventoryItem.brand_name.label("brand_name"),
            )
            .join(User, User.id == PharmacyStockMovement.actor_id)
            .join(
                PharmacyInventoryItem,
                and_(
                    PharmacyInventoryItem.id
                    == PharmacyStockMovement.inventory_item_id,
                    PharmacyInventoryItem.clinic_id
                    == PharmacyStockMovement.clinic_id,
                ),
            )
            .filter(
                PharmacyStockMovement.clinic_id == clinic_id,
                PharmacyStockMovement.occurred_at >= start_at,
                PharmacyStockMovement.occurred_at < end_at,
            )
        )

        if resolved_type != "ALL":
            query = query.filter(PharmacyStockMovement.movement_type == resolved_type)

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(PharmacyInventoryItem.generic_name).like(term),
                    func.lower(
                        func.coalesce(PharmacyInventoryItem.brand_name, "")
                    ).like(term),
                    func.lower(func.coalesce(User.full_name, "")).like(term),
                )
            )

        total = int(
            query.with_entities(func.count(PharmacyStockMovement.id))
            .order_by(None)
            .scalar()
            or 0
        )
        rows = (
            query.order_by(PharmacyStockMovement.occurred_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        data: list[dict] = []
        for movement, actor_name, generic_name, brand_name in rows:
            item_name = (
                f"{generic_name} ({brand_name})"
                if brand_name
                else generic_name
            )
            data.append(
                {
                    "id": movement.id,
                    "occurred_at": movement.occurred_at,
                    "movement_type": movement.movement_type,
                    "quantity_delta": int(movement.quantity_delta),
                    "stock_before": int(movement.stock_before),
                    "stock_after": int(movement.stock_after),
                    "note": movement.note,
                    "actor_name": actor_name,
                    "item_name": item_name,
                }
            )

        return {
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
            "start_date": resolved_start,
            "end_date": resolved_end,
        }

    def get_inventory_overview(self, *, clinic_id: UUID) -> dict:
        base_query = self.db.query(PharmacyInventoryItem).filter(
            PharmacyInventoryItem.clinic_id == clinic_id
        )

        total_drugs = int(
            base_query.filter(PharmacyInventoryItem.lifecycle_status == "ACTIVE")
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        low_stock = int(
            base_query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity > 0,
                PharmacyInventoryItem.stock_quantity <= PharmacyInventoryItem.low_stock_threshold,
            )
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        out_of_stock = int(
            base_query.filter(
                PharmacyInventoryItem.lifecycle_status == "ACTIVE",
                PharmacyInventoryItem.stock_quantity == 0,
            )
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        inactive = int(
            base_query.filter(PharmacyInventoryItem.lifecycle_status == "INACTIVE")
            .with_entities(func.count(PharmacyInventoryItem.id))
            .scalar()
            or 0
        )
        available = max(total_drugs - low_stock - out_of_stock, 0)

        inventory_value_minor = int(
            base_query.filter(PharmacyInventoryItem.lifecycle_status == "ACTIVE")
            .with_entities(
                func.coalesce(
                    func.sum(
                        PharmacyInventoryItem.stock_quantity
                        * PharmacyInventoryItem.selling_price_minor
                    ),
                    0,
                )
            )
            .scalar()
            or 0
        )

        now_date = datetime.now(timezone.utc).date()
        day_start = datetime.combine(now_date, time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        todays_dispenses = int(
            self.db.query(func.count(Dispensation.id))
            .filter(
                Dispensation.clinic_id == clinic_id,
                Dispensation.created_at >= day_start,
                Dispensation.created_at < day_end,
            )
            .scalar()
            or 0
        )

        top_dispensed_rows = (
            self.db.query(
                Prescription.drug_name.label("drug_name"),
                func.count(Dispensation.id).label("dispensed_count"),
            )
            .join(
                Dispensation,
                and_(
                    Dispensation.prescription_id == Prescription.id,
                    Dispensation.clinic_id == clinic_id,
                ),
            )
            .filter(
                Prescription.clinic_id == clinic_id,
                Dispensation.created_at >= day_start,
                Dispensation.created_at < day_end,
            )
            .group_by(Prescription.drug_name)
            .order_by(func.count(Dispensation.id).desc(), Prescription.drug_name.asc())
            .limit(5)
            .all()
        )
        top_dispensed_drugs = [
            {
                "drug_name": row.drug_name,
                "dispensed_count": int(row.dispensed_count or 0),
            }
            for row in top_dispensed_rows
        ]

        recent_movement_rows = (
            self.db.query(PharmacyStockMovement, User.full_name.label("actor_name"))
            .join(User, User.id == PharmacyStockMovement.actor_id)
            .filter(PharmacyStockMovement.clinic_id == clinic_id)
            .order_by(PharmacyStockMovement.occurred_at.desc())
            .limit(10)
            .all()
        )
        recent_movements = [
            self._movement_to_dict(movement, actor_name)
            for movement, actor_name in recent_movement_rows
        ]

        alerts: list[str] = []
        if out_of_stock > 0:
            alerts.append(f"{out_of_stock} drugs are out of stock.")
        if low_stock > 0:
            alerts.append(f"{low_stock} drugs are below low-stock threshold.")
        if not alerts:
            alerts.append("No critical stock alerts.")

        return {
            "total_drugs": total_drugs,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "todays_dispenses": todays_dispenses,
            "inventory_value_minor": inventory_value_minor,
            "currency": self._resolve_currency(clinic_id=clinic_id),
            "alerts": alerts,
            "inventory_health": {
                "available": available,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
                "inactive": inactive,
            },
            "recent_movements": recent_movements,
            "top_dispensed_drugs": top_dispensed_drugs,
            "access_mode": self.get_access_mode(clinic_id=clinic_id),
        }
