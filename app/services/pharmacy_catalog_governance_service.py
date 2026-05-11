from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.pharmacy_catalog_item import PharmacyCatalogItem
from app.models.pharmacy_inventory_item import PharmacyInventoryItem
from app.models.pharmacy_pricing_config import PharmacyPricingConfig
from app.models.user import User
from app.schemas.pharmacy_catalog import (
    PharmacyActiveCatalogItemResponse,
    PharmacyCatalogGovernanceDetailResponse,
    PharmacyCatalogRegistryRowResponse,
    PharmacyPricingConfigResponse,
)
from app.services.event_service import EventService
from app.shared.enums import (
    PharmacyCatalogLifecycleStatus,
    PharmacyPricingStatus,
    UserRole,
)


class PharmacyCatalogGovernanceService:
    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip()

    @classmethod
    def _normalize_lower(cls, value: str | None) -> str:
        return cls._normalize(value).lower()

    @classmethod
    def _display_name(cls, item: PharmacyCatalogItem) -> str:
        parts = [cls._normalize(item.generic_name)]
        if cls._normalize(item.strength):
            parts.append(cls._normalize(item.strength))
        if cls._normalize(item.dosage_form):
            parts.append(cls._normalize(item.dosage_form))
        return " ".join(part for part in parts if part)

    def _resolve_currency(self, *, clinic_id: UUID) -> str:
        return (
            self.db.query(Clinic.billing_currency)
            .filter(Clinic.id == clinic_id)
            .scalar()
            or "NGN"
        )

    def _generate_catalog_code(self) -> str:
        return f"PHARM-{uuid4().hex[:8].upper()}"

    def _get_catalog_item(self, *, clinic_id: UUID, item_id: UUID) -> PharmacyCatalogItem:
        item = (
            self.db.query(PharmacyCatalogItem)
            .filter(
                PharmacyCatalogItem.id == item_id,
                PharmacyCatalogItem.clinic_id == clinic_id,
            )
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pharmacy catalog item not found",
            )
        return item

    def _get_pricing_config(
        self, *, clinic_id: UUID, catalog_item_id: UUID
    ) -> PharmacyPricingConfig | None:
        return (
            self.db.query(PharmacyPricingConfig)
            .filter(
                PharmacyPricingConfig.clinic_id == clinic_id,
                PharmacyPricingConfig.catalog_item_id == catalog_item_id,
            )
            .first()
        )

    def _get_user_name_map(self, *, user_ids: set[UUID]) -> dict[UUID, str | None]:
        if not user_ids:
            return {}
        rows = self.db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all()
        return {row.id: row.full_name for row in rows}

    def _validate_duplicate(
        self,
        *,
        clinic_id: UUID,
        generic_name: str,
        strength: str | None,
        dosage_form: str,
        exclude_id: UUID | None = None,
    ) -> None:
        query = self.db.query(PharmacyCatalogItem.id).filter(
            PharmacyCatalogItem.clinic_id == clinic_id,
            func.lower(PharmacyCatalogItem.generic_name) == self._normalize_lower(generic_name),
            func.lower(func.coalesce(PharmacyCatalogItem.strength, "")) == self._normalize_lower(strength),
            func.lower(PharmacyCatalogItem.dosage_form) == self._normalize_lower(dosage_form),
        )
        if exclude_id is not None:
            query = query.filter(PharmacyCatalogItem.id != exclude_id)
        if query.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A pharmacy catalog item with the same generic name, strength, and dosage form already exists"
                ),
            )

    def _serialize_pricing(
        self,
        pricing: PharmacyPricingConfig | None,
        *,
        user_name_map: dict[UUID, str | None],
    ) -> PharmacyPricingConfigResponse | None:
        if pricing is None:
            return None
        return PharmacyPricingConfigResponse(
            id=pricing.id,
            catalog_item_id=pricing.catalog_item_id,
            charge_code=pricing.charge_code,
            unit_price_minor=int(pricing.unit_price_minor),
            currency=pricing.currency,
            effective_date=pricing.effective_date,
            status=PharmacyPricingStatus(pricing.status),
            active=bool(pricing.active),
            configured_by=pricing.configured_by,
            configured_by_name=user_name_map.get(pricing.configured_by),
            configured_at=pricing.configured_at,
            activated_by=pricing.activated_by,
            activated_by_name=user_name_map.get(pricing.activated_by) if pricing.activated_by else None,
            activated_at=pricing.activated_at,
            deactivated_by=pricing.deactivated_by,
            deactivated_by_name=user_name_map.get(pricing.deactivated_by) if pricing.deactivated_by else None,
            deactivated_at=pricing.deactivated_at,
        )

    def _serialize_item(
        self,
        item: PharmacyCatalogItem,
        *,
        pricing: PharmacyPricingConfig | None,
        user_name_map: dict[UUID, str | None],
    ) -> PharmacyCatalogRegistryRowResponse:
        return PharmacyCatalogRegistryRowResponse(
            id=item.id,
            catalog_code=item.catalog_code,
            generic_name=item.generic_name,
            brand_name=item.brand_name,
            strength=item.strength,
            dosage_form=item.dosage_form,
            dispense_unit=item.dispense_unit,
            classification=item.classification,
            tracking_mode=item.tracking_mode,
            requires_expiry=bool(item.requires_expiry),
            lifecycle_status=PharmacyCatalogLifecycleStatus(item.lifecycle_status),
            billing_status=PharmacyPricingStatus(item.billing_status),
            active=bool(item.active),
            justification=item.justification,
            requested_by=item.requested_by,
            requested_by_name=user_name_map.get(item.requested_by),
            submitted_by=item.submitted_by,
            submitted_by_name=user_name_map.get(item.submitted_by) if item.submitted_by else None,
            submitted_at=item.submitted_at,
            cmd_reviewed_by=item.cmd_reviewed_by,
            cmd_reviewed_by_name=user_name_map.get(item.cmd_reviewed_by) if item.cmd_reviewed_by else None,
            cmd_reviewed_at=item.cmd_reviewed_at,
            cmd_review_note=item.cmd_review_note,
            priced_by=item.priced_by,
            priced_by_name=user_name_map.get(item.priced_by) if item.priced_by else None,
            priced_at=item.priced_at,
            activated_by=item.activated_by,
            activated_by_name=user_name_map.get(item.activated_by) if item.activated_by else None,
            activated_at=item.activated_at,
            deactivated_by=item.deactivated_by,
            deactivated_by_name=user_name_map.get(item.deactivated_by) if item.deactivated_by else None,
            deactivated_at=item.deactivated_at,
            current_price_minor=int(pricing.unit_price_minor) if pricing else None,
            current_currency=pricing.currency if pricing else None,
            charge_code=pricing.charge_code if pricing else None,
            effective_date=pricing.effective_date if pricing else None,
        )

    def _serialize_rows(self, items: list[PharmacyCatalogItem]) -> list[PharmacyCatalogRegistryRowResponse]:
        pricing_rows = (
            self.db.query(PharmacyPricingConfig)
            .filter(PharmacyPricingConfig.catalog_item_id.in_([item.id for item in items]))
            .all()
            if items
            else []
        )
        pricing_by_item_id = {row.catalog_item_id: row for row in pricing_rows}
        user_ids: set[UUID] = set()
        for item in items:
            user_ids.add(item.requested_by)
            if item.submitted_by:
                user_ids.add(item.submitted_by)
            if item.cmd_reviewed_by:
                user_ids.add(item.cmd_reviewed_by)
            if item.priced_by:
                user_ids.add(item.priced_by)
            if item.activated_by:
                user_ids.add(item.activated_by)
            if item.deactivated_by:
                user_ids.add(item.deactivated_by)
        for pricing in pricing_rows:
            user_ids.add(pricing.configured_by)
            if pricing.activated_by:
                user_ids.add(pricing.activated_by)
            if pricing.deactivated_by:
                user_ids.add(pricing.deactivated_by)
        user_name_map = self._get_user_name_map(user_ids=user_ids)
        return [
            self._serialize_item(item, pricing=pricing_by_item_id.get(item.id), user_name_map=user_name_map)
            for item in items
        ]

    def list_catalog_items(
        self,
        *,
        clinic_id: UUID,
        requested_by: UUID | None = None,
        lifecycle_status: PharmacyCatalogLifecycleStatus | None = None,
        billing_status: PharmacyPricingStatus | None = None,
        include_inactive: bool = True,
    ) -> list[PharmacyCatalogRegistryRowResponse]:
        query = self.db.query(PharmacyCatalogItem).filter(PharmacyCatalogItem.clinic_id == clinic_id)
        if requested_by is not None:
            query = query.filter(PharmacyCatalogItem.requested_by == requested_by)
        if lifecycle_status is not None:
            query = query.filter(PharmacyCatalogItem.lifecycle_status == lifecycle_status.value)
        if billing_status is not None:
            query = query.filter(PharmacyCatalogItem.billing_status == billing_status.value)
        if not include_inactive:
            query = query.filter(PharmacyCatalogItem.active.is_(True))
        items = query.order_by(PharmacyCatalogItem.created_at.desc()).all()
        return self._serialize_rows(items)

    def create_catalog_request(self, *, clinic_id: UUID, actor: User, payload) -> PharmacyCatalogRegistryRowResponse:
        self._validate_duplicate(
            clinic_id=clinic_id,
            generic_name=payload.generic_name,
            strength=payload.strength,
            dosage_form=payload.dosage_form,
        )
        now = datetime.now(timezone.utc)
        lifecycle_status = (
            PharmacyCatalogLifecycleStatus.AWAITING_CMD_APPROVAL
            if payload.submit_now
            else PharmacyCatalogLifecycleStatus.DRAFT
        )
        item = PharmacyCatalogItem(
            id=uuid4(),
            clinic_id=clinic_id,
            catalog_code=self._generate_catalog_code(),
            generic_name=self._normalize(payload.generic_name),
            brand_name=self._normalize(payload.brand_name) or None,
            strength=self._normalize(payload.strength) or None,
            dosage_form=self._normalize(payload.dosage_form),
            dispense_unit=self._normalize(payload.dispense_unit),
            classification=payload.classification.value,
            tracking_mode=payload.tracking_mode.value,
            requires_expiry=bool(payload.requires_expiry),
            lifecycle_status=lifecycle_status.value,
            billing_status=PharmacyPricingStatus.NOT_CONFIGURED.value,
            active=False,
            justification=self._normalize(payload.justification),
            requested_by=actor.id,
            submitted_by=actor.id if payload.submit_now else None,
            submitted_at=now if payload.submit_now else None,
        )
        self.db.add(item)
        if payload.submit_now:
            self.event_service.build_event(
                event_type="PHARMACY_CATALOG_REQUEST_SUBMITTED",
                actor_id=actor.id,
                actor_role=getattr(actor.role, "value", actor.role),
                clinic_id=clinic_id,
                emitter="pharmacy",
                payload={
                    "catalog_item_id": str(item.id),
                    "catalog_code": item.catalog_code,
                    "generic_name": item.generic_name,
                    "dosage_form": item.dosage_form,
                    "strength": item.strength,
                },
            )
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_rows([item])[0]

    def submit_catalog_request(self, *, clinic_id: UUID, actor: User, item_id: UUID) -> PharmacyCatalogRegistryRowResponse:
        item = self._get_catalog_item(clinic_id=clinic_id, item_id=item_id)
        if item.requested_by != actor.id and str(actor.role) != UserRole.PHARMACY_HOD.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Pharmacy HOD can submit this request",
            )
        if item.lifecycle_status not in {
            PharmacyCatalogLifecycleStatus.DRAFT.value,
            PharmacyCatalogLifecycleStatus.SUBMITTED.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft catalog requests can be submitted",
            )
        now = datetime.now(timezone.utc)
        item.lifecycle_status = PharmacyCatalogLifecycleStatus.AWAITING_CMD_APPROVAL.value
        item.submitted_by = actor.id
        item.submitted_at = now
        self.db.add(item)
        self.event_service.build_event(
            event_type="PHARMACY_CATALOG_REQUEST_SUBMITTED",
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "catalog_item_id": str(item.id),
                "catalog_code": item.catalog_code,
                "generic_name": item.generic_name,
                "dosage_form": item.dosage_form,
                "strength": item.strength,
            },
        )
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_rows([item])[0]

    def review_catalog_request(self, *, clinic_id: UUID, actor: User, item_id: UUID, payload) -> PharmacyCatalogRegistryRowResponse:
        item = self._get_catalog_item(clinic_id=clinic_id, item_id=item_id)
        if item.lifecycle_status != PharmacyCatalogLifecycleStatus.AWAITING_CMD_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only awaiting-CMD-approval catalog requests can be reviewed",
            )
        now = datetime.now(timezone.utc)
        item.cmd_reviewed_by = actor.id
        item.cmd_reviewed_at = now
        item.cmd_review_note = self._normalize(payload.note) or None
        if payload.decision == "REJECT":
            item.lifecycle_status = PharmacyCatalogLifecycleStatus.REJECTED.value
            event_type = "PHARMACY_CATALOG_CMD_REJECTED"
        else:
            item.lifecycle_status = PharmacyCatalogLifecycleStatus.PRICING_PENDING.value
            event_type = "PHARMACY_CATALOG_CMD_APPROVED"
        self.db.add(item)
        self.event_service.build_event(
            event_type=event_type,
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "catalog_item_id": str(item.id),
                "catalog_code": item.catalog_code,
                "decision": payload.decision,
                "note": item.cmd_review_note,
            },
        )
        self.db.commit()
        self.db.refresh(item)
        return self._serialize_rows([item])[0]

    def _sync_charge_catalog(
        self,
        *,
        clinic_id: UUID,
        item: PharmacyCatalogItem,
        pricing: PharmacyPricingConfig,
    ) -> ChargeCatalog:
        charge = (
            self.db.query(ChargeCatalog)
            .filter(
                ChargeCatalog.clinic_id == clinic_id,
                ChargeCatalog.code == pricing.charge_code,
            )
            .first()
        )
        if charge is None:
            charge = ChargeCatalog(
                clinic_id=clinic_id,
                code=pricing.charge_code,
                name=self._display_name(item),
                category=f"PHARMACY_{item.classification}",
                default_amount_minor=int(pricing.unit_price_minor),
                currency=pricing.currency,
                active=bool(pricing.active),
            )
        else:
            charge.name = self._display_name(item)
            charge.category = f"PHARMACY_{item.classification}"
            charge.default_amount_minor = int(pricing.unit_price_minor)
            charge.currency = pricing.currency
            charge.active = bool(pricing.active)
        self.db.add(charge)
        self.db.flush()
        return charge

    def _sync_inventory_registration(
        self,
        *,
        clinic_id: UUID,
        item: PharmacyCatalogItem,
        pricing: PharmacyPricingConfig,
        actor: User,
    ) -> PharmacyInventoryItem:
        inventory_item = (
            self.db.query(PharmacyInventoryItem)
            .filter(
                PharmacyInventoryItem.clinic_id == clinic_id,
                PharmacyInventoryItem.catalog_item_id == item.id,
            )
            .first()
        )
        if inventory_item is None:
            inventory_item = (
                self.db.query(PharmacyInventoryItem)
                .filter(
                    PharmacyInventoryItem.clinic_id == clinic_id,
                    func.lower(PharmacyInventoryItem.generic_name) == self._normalize_lower(item.generic_name),
                    func.lower(func.coalesce(PharmacyInventoryItem.strength, "")) == self._normalize_lower(item.strength),
                    func.lower(PharmacyInventoryItem.dosage_form) == self._normalize_lower(item.dosage_form),
                    func.lower(PharmacyInventoryItem.unit_of_measure) == self._normalize_lower(item.dispense_unit),
                )
                .first()
            )
        now = datetime.now(timezone.utc)
        if inventory_item is None:
            inventory_item = PharmacyInventoryItem(
                id=uuid4(),
                clinic_id=clinic_id,
                catalog_item_id=item.id,
                generic_name=item.generic_name,
                brand_name=item.brand_name,
                dosage_form=item.dosage_form,
                strength=item.strength,
                unit_of_measure=item.dispense_unit,
                classification=item.classification,
                tracking_mode=item.tracking_mode,
                requires_expiry=bool(item.requires_expiry),
                selling_price_minor=int(pricing.unit_price_minor),
                currency=pricing.currency,
                stock_quantity=0,
                low_stock_threshold=10,
                lifecycle_status="ACTIVE" if item.active else "INACTIVE",
                created_by=actor.id,
                updated_by=actor.id,
                last_restocked_at=None,
            )
        else:
            inventory_item.catalog_item_id = item.id
            inventory_item.generic_name = item.generic_name
            inventory_item.brand_name = item.brand_name
            inventory_item.dosage_form = item.dosage_form
            inventory_item.strength = item.strength
            inventory_item.unit_of_measure = item.dispense_unit
            inventory_item.classification = item.classification
            inventory_item.tracking_mode = item.tracking_mode
            inventory_item.requires_expiry = bool(item.requires_expiry)
            inventory_item.selling_price_minor = int(pricing.unit_price_minor)
            inventory_item.currency = pricing.currency
            inventory_item.lifecycle_status = "ACTIVE" if item.active else "INACTIVE"
            inventory_item.updated_by = actor.id
            if item.active and inventory_item.last_restocked_at is None:
                inventory_item.last_restocked_at = now
        self.db.add(inventory_item)
        self.db.flush()
        return inventory_item

    def configure_pricing(
        self,
        *,
        clinic_id: UUID,
        actor: User,
        item_id: UUID,
        payload,
    ) -> PharmacyCatalogGovernanceDetailResponse:
        item = self._get_catalog_item(clinic_id=clinic_id, item_id=item_id)
        if item.lifecycle_status == PharmacyCatalogLifecycleStatus.REJECTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Rejected catalog requests cannot be priced",
            )
        if item.lifecycle_status in {
            PharmacyCatalogLifecycleStatus.DRAFT.value,
            PharmacyCatalogLifecycleStatus.SUBMITTED.value,
            PharmacyCatalogLifecycleStatus.AWAITING_CMD_APPROVAL.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Catalog item must complete CMD approval before pricing",
            )
        now = datetime.now(timezone.utc)
        if payload.activate and payload.effective_date > now.date():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Future-dated pricing cannot be activated yet",
            )

        pricing = self._get_pricing_config(clinic_id=clinic_id, catalog_item_id=item.id)
        if pricing is None:
            pricing = PharmacyPricingConfig(
                id=uuid4(),
                clinic_id=clinic_id,
                catalog_item_id=item.id,
                charge_code=self._normalize(payload.charge_code).upper(),
                unit_price_minor=int(payload.unit_price_minor),
                currency=self._normalize(payload.currency).upper() or self._resolve_currency(clinic_id=clinic_id),
                effective_date=payload.effective_date,
                status=PharmacyPricingStatus.PRICED.value,
                active=False,
                configured_by=actor.id,
                configured_at=now,
            )
        else:
            pricing.charge_code = self._normalize(payload.charge_code).upper()
            pricing.unit_price_minor = int(payload.unit_price_minor)
            pricing.currency = self._normalize(payload.currency).upper() or pricing.currency
            pricing.effective_date = payload.effective_date
            pricing.configured_by = actor.id
            pricing.configured_at = now

        item.priced_by = actor.id
        item.priced_at = now

        if payload.activate:
            pricing.status = PharmacyPricingStatus.ACTIVE.value
            pricing.active = True
            pricing.activated_by = actor.id
            pricing.activated_at = now
            pricing.deactivated_by = None
            pricing.deactivated_at = None
            item.billing_status = PharmacyPricingStatus.ACTIVE.value
            item.lifecycle_status = PharmacyCatalogLifecycleStatus.ACTIVE.value
            item.active = True
            item.activated_by = actor.id
            item.activated_at = now
            item.deactivated_by = None
            item.deactivated_at = None
        else:
            if item.active:
                pricing.status = PharmacyPricingStatus.INACTIVE.value
                pricing.active = False
                pricing.deactivated_by = actor.id
                pricing.deactivated_at = now
                item.billing_status = PharmacyPricingStatus.INACTIVE.value
                item.lifecycle_status = PharmacyCatalogLifecycleStatus.DEACTIVATED.value
                item.active = False
                item.deactivated_by = actor.id
                item.deactivated_at = now
                event_type = "PHARMACY_CATALOG_DEACTIVATED"
            else:
                pricing.status = PharmacyPricingStatus.PRICED.value
                pricing.active = False
                item.billing_status = PharmacyPricingStatus.PRICED.value
                item.lifecycle_status = PharmacyCatalogLifecycleStatus.PRICED.value
                item.active = False
                event_type = None
            self.db.add(pricing)
            self.db.add(item)
            charge = self._sync_charge_catalog(clinic_id=clinic_id, item=item, pricing=pricing)
            if charge is not None:
                charge.active = False
                self.db.add(charge)
            inventory_item = (
                self.db.query(PharmacyInventoryItem)
                .filter(
                    PharmacyInventoryItem.clinic_id == clinic_id,
                    PharmacyInventoryItem.catalog_item_id == item.id,
                )
                .first()
            )
            if inventory_item is not None:
                inventory_item.lifecycle_status = "INACTIVE"
                inventory_item.selling_price_minor = int(pricing.unit_price_minor)
                inventory_item.currency = pricing.currency
                inventory_item.updated_by = actor.id
                self.db.add(inventory_item)
            if event_type is not None:
                self.event_service.build_event(
                    event_type=event_type,
                    actor_id=actor.id,
                    actor_role=getattr(actor.role, "value", actor.role),
                    clinic_id=clinic_id,
                    emitter="pharmacy",
                    payload={
                        "catalog_item_id": str(item.id),
                        "catalog_code": item.catalog_code,
                    },
                )
            self.db.commit()
            self.db.refresh(item)
            self.db.refresh(pricing)
            return PharmacyCatalogGovernanceDetailResponse(
                item=self._serialize_rows([item])[0],
                pricing=self._serialize_pricing(pricing, user_name_map=self._get_user_name_map(user_ids={actor.id})),
            )

        self.db.add(pricing)
        self.db.add(item)
        charge = self._sync_charge_catalog(clinic_id=clinic_id, item=item, pricing=pricing)
        inventory_item = self._sync_inventory_registration(
            clinic_id=clinic_id,
            item=item,
            pricing=pricing,
            actor=actor,
        )
        charge.active = True
        self.db.add(charge)
        self.db.add(inventory_item)
        self.event_service.build_event(
            event_type="PHARMACY_CATALOG_PRICED",
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "catalog_item_id": str(item.id),
                "catalog_code": item.catalog_code,
                "charge_code": pricing.charge_code,
                "unit_price_minor": int(pricing.unit_price_minor),
                "currency": pricing.currency,
                "effective_date": pricing.effective_date.isoformat(),
            },
        )
        self.event_service.build_event(
            event_type="PHARMACY_CATALOG_ACTIVATED",
            actor_id=actor.id,
            actor_role=getattr(actor.role, "value", actor.role),
            clinic_id=clinic_id,
            emitter="pharmacy",
            payload={
                "catalog_item_id": str(item.id),
                "catalog_code": item.catalog_code,
                "charge_code": pricing.charge_code,
            },
        )
        self.db.commit()
        self.db.refresh(item)
        self.db.refresh(pricing)
        user_ids = {actor.id}
        return PharmacyCatalogGovernanceDetailResponse(
            item=self._serialize_rows([item])[0],
            pricing=self._serialize_pricing(pricing, user_name_map=self._get_user_name_map(user_ids=user_ids)),
        )

    def list_active_catalog_items(self, *, clinic_id: UUID) -> list[PharmacyActiveCatalogItemResponse]:
        today = datetime.now(timezone.utc).date()
        rows = (
            self.db.query(PharmacyCatalogItem, PharmacyPricingConfig)
            .join(
                PharmacyPricingConfig,
                PharmacyPricingConfig.catalog_item_id == PharmacyCatalogItem.id,
            )
            .filter(
                PharmacyCatalogItem.clinic_id == clinic_id,
                PharmacyCatalogItem.active.is_(True),
                PharmacyCatalogItem.lifecycle_status == PharmacyCatalogLifecycleStatus.ACTIVE.value,
                PharmacyPricingConfig.active.is_(True),
                PharmacyPricingConfig.status == PharmacyPricingStatus.ACTIVE.value,
                PharmacyPricingConfig.effective_date <= today,
            )
            .order_by(PharmacyCatalogItem.generic_name.asc(), PharmacyCatalogItem.strength.asc())
            .all()
        )
        return [
            PharmacyActiveCatalogItemResponse(
                id=item.id,
                catalog_code=item.catalog_code,
                generic_name=item.generic_name,
                brand_name=item.brand_name,
                strength=item.strength,
                dosage_form=item.dosage_form,
                dispense_unit=item.dispense_unit,
                classification=item.classification,
                tracking_mode=item.tracking_mode,
                requires_expiry=bool(item.requires_expiry),
                charge_code=pricing.charge_code,
                unit_price_minor=int(pricing.unit_price_minor),
                currency=pricing.currency,
                display_name=self._display_name(item),
            )
            for item, pricing in rows
        ]

    def resolve_operational_item(
        self,
        *,
        clinic_id: UUID,
        catalog_item_id: UUID | None,
        drug_name: str | None,
    ) -> tuple[PharmacyCatalogItem, PharmacyPricingConfig, ChargeCatalog | None]:
        today = datetime.now(timezone.utc).date()
        query = (
            self.db.query(PharmacyCatalogItem, PharmacyPricingConfig, ChargeCatalog)
            .join(
                PharmacyPricingConfig,
                PharmacyPricingConfig.catalog_item_id == PharmacyCatalogItem.id,
            )
            .outerjoin(
                ChargeCatalog,
                (ChargeCatalog.clinic_id == PharmacyCatalogItem.clinic_id)
                & (ChargeCatalog.code == PharmacyPricingConfig.charge_code),
            )
            .filter(
                PharmacyCatalogItem.clinic_id == clinic_id,
                PharmacyCatalogItem.active.is_(True),
                PharmacyCatalogItem.lifecycle_status == PharmacyCatalogLifecycleStatus.ACTIVE.value,
                PharmacyPricingConfig.active.is_(True),
                PharmacyPricingConfig.status == PharmacyPricingStatus.ACTIVE.value,
                PharmacyPricingConfig.effective_date <= today,
            )
        )
        row = None
        if catalog_item_id is not None:
            row = query.filter(PharmacyCatalogItem.id == catalog_item_id).first()
        elif self._normalize(drug_name):
            row = query.filter(
                func.lower(PharmacyCatalogItem.generic_name) == self._normalize_lower(drug_name)
            ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"No approved pharmacy pricing is configured for '{drug_name or 'the selected item'}'. "
                    "Complete catalog approval and pricing activation before issuing this prescription."
                ),
            )
        item, pricing, charge = row
        return item, pricing, charge
