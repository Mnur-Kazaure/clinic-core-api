# app/services/billing_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import IntegrityError

from app.models.billing_ledger_entry import BillingLedgerEntry
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.identity_map_revocation import IdentityMapRevocation
from app.models.patient_identity_map import PatientIdentityMap
from app.models.patient import Patient
from app.models.visit import Visit
from app.shared.enums import BillingEntryType, BillingReasonCode


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def create_charge_for_visit(
        self,
        *,
        visit_id: UUID,
        code: str | None,
        amount_minor: int | None,
        description: str,
        reason_code: BillingReasonCode,
        actor,
    ) -> BillingLedgerEntry:
        visit = (
            self.db.query(Visit)
            .filter(Visit.id == visit_id)
            .first()
        )
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        if visit.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")

        clinic = self._get_clinic(actor.clinic_id)
        currency = clinic.billing_currency
        resolved_patient_id = self._resolve_canonical_patient_id(
            patient_id=visit.patient_id,
            clinic_id=visit.clinic_id,
        )

        if code:
            catalog = (
                self.db.query(ChargeCatalog)
                .filter(
                    ChargeCatalog.clinic_id == actor.clinic_id,
                    ChargeCatalog.code == code,
                    ChargeCatalog.active.is_(True),
                )
                .first()
            )
            if not catalog:
                raise HTTPException(status_code=404, detail="Charge code not found")
            if catalog.currency != currency:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Charge currency mismatch",
                )
            if amount_minor is None:
                amount_minor = catalog.default_amount_minor
        if amount_minor is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="amount_minor is required when no charge code is provided",
            )
        if amount_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Charge amount must be positive",
            )

        entry = BillingLedgerEntry(
            clinic_id=visit.clinic_id,
            patient_id=resolved_patient_id,
            visit_id=visit.id,
            admission_id=None,
            entry_type=BillingEntryType.CHARGE,
            amount_minor=amount_minor,
            currency=currency,
            description=description,
            reason_code=reason_code,
            external_ref=None,
            related_entry_id=None,
            actor_id=actor.id,
            actor_role=actor.role,
            occurred_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def create_payment_for_patient(
        self,
        *,
        patient_id: UUID,
        amount_minor: int,
        description: str,
        reason_code: BillingReasonCode,
        external_ref: str | None,
        actor,
    ) -> BillingLedgerEntry:
        patient = self._get_patient(patient_id, actor.clinic_id)
        clinic = self._get_clinic(actor.clinic_id)
        resolved_patient_id = self._resolve_canonical_patient_id(
            patient_id=patient.id,
            clinic_id=patient.clinic_id,
        )
        if amount_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Payment amount must be positive",
            )
        entry = BillingLedgerEntry(
            clinic_id=patient.clinic_id,
            patient_id=resolved_patient_id,
            visit_id=None,
            admission_id=None,
            entry_type=BillingEntryType.PAYMENT,
            amount_minor=-abs(amount_minor),
            currency=clinic.billing_currency,
            description=description,
            reason_code=reason_code,
            external_ref=external_ref,
            related_entry_id=None,
            actor_id=actor.id,
            actor_role=actor.role,
            occurred_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Payment violates uniqueness or constraint",
            )
        self.db.refresh(entry)
        return entry

    def reverse_entry(
        self,
        *,
        entry_id: UUID,
        justification: str,
        reason_code: BillingReasonCode,
        actor,
    ) -> BillingLedgerEntry:
        entry = (
            self.db.query(BillingLedgerEntry)
            .filter(BillingLedgerEntry.id == entry_id)
            .first()
        )
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        if entry.clinic_id != actor.clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        if entry.entry_type == BillingEntryType.REVERSAL:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot reverse a reversal entry",
            )
        if len(justification.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Justification must be at least 10 characters",
            )

        reversal_amount = -entry.amount_minor
        reversal = BillingLedgerEntry(
            clinic_id=entry.clinic_id,
            patient_id=entry.patient_id,
            visit_id=entry.visit_id,
            admission_id=entry.admission_id,
            entry_type=BillingEntryType.REVERSAL,
            amount_minor=reversal_amount,
            currency=entry.currency,
            description=justification,
            reason_code=reason_code,
            external_ref=None,
            related_entry_id=entry.id,
            actor_id=actor.id,
            actor_role=actor.role,
            occurred_at=datetime.now(timezone.utc),
        )
        self.db.add(reversal)
        self.db.commit()
        self.db.refresh(reversal)
        return reversal

    def get_ledger_for_patient(self, *, patient_id: UUID, clinic_id: UUID) -> list[BillingLedgerEntry]:
        self._get_patient(patient_id, clinic_id)
        canonical_id = self._resolve_canonical_patient_id(
            patient_id=patient_id,
            clinic_id=clinic_id,
        )
        patient_ids = self._resolve_identity_closure(
            canonical_id=canonical_id,
            clinic_id=clinic_id,
        )
        return (
            self.db.query(BillingLedgerEntry)
            .filter(
                BillingLedgerEntry.clinic_id == clinic_id,
                BillingLedgerEntry.patient_id.in_(patient_ids),
            )
            .order_by(BillingLedgerEntry.occurred_at.desc())
            .all()
        )

    def _get_patient(self, patient_id: UUID, clinic_id: UUID) -> Patient:
        patient = (
            self.db.query(Patient)
            .filter(Patient.id == patient_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if patient.clinic_id != clinic_id:
            raise HTTPException(status_code=403, detail="Cross-clinic access denied")
        return patient

    def _get_clinic(self, clinic_id: UUID) -> Clinic:
        clinic = (
            self.db.query(Clinic)
            .filter(Clinic.id == clinic_id)
            .first()
        )
        if not clinic:
            raise HTTPException(status_code=404, detail="Clinic not found")
        return clinic

    def _resolve_canonical_patient_id(self, *, patient_id: UUID, clinic_id: UUID) -> UUID:
        visited = set()
        current = patient_id
        for _ in range(10):
            if current in visited:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Identity mapping cycle detected",
                )
            visited.add(current)
            mapping = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.from_patient_id == current,
                )
                .first()
            )
            if not mapping:
                return current
            revoked = (
                self.db.query(IdentityMapRevocation)
                .filter(
                    IdentityMapRevocation.clinic_id == clinic_id,
                    IdentityMapRevocation.map_id == mapping.id,
                )
                .first()
            )
            if revoked:
                return current
            current = mapping.to_patient_id
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identity resolution exceeded hop limit",
        )

    def _resolve_identity_closure(self, *, canonical_id: UUID, clinic_id: UUID) -> list[UUID]:
        seen = {canonical_id}
        queue = [canonical_id]
        while queue:
            target = queue.pop()
            mappings = (
                self.db.query(PatientIdentityMap)
                .filter(
                    PatientIdentityMap.clinic_id == clinic_id,
                    PatientIdentityMap.to_patient_id == target,
                )
                .all()
            )
            for mapping in mappings:
                revoked = (
                    self.db.query(IdentityMapRevocation)
                    .filter(
                        IdentityMapRevocation.clinic_id == clinic_id,
                        IdentityMapRevocation.map_id == mapping.id,
                    )
                    .first()
                )
                if revoked:
                    continue
                if mapping.from_patient_id not in seen:
                    seen.add(mapping.from_patient_id)
                    queue.append(mapping.from_patient_id)
        return list(seen)
