# app/services/mrn_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.clinic_mrn_sequence import ClinicMrnSequence
from app.models.patient_mrn import PatientMRN
from app.models.patient import Patient
from app.models.patient_identity_map import PatientIdentityMap
from app.models.identity_map_revocation import IdentityMapRevocation
from app.shared.enums import MRNStatus


class MRNService:
    def __init__(self, db: Session):
        self.db = db

    def issue_mrn_for_patient(
        self,
        *,
        patient_id: UUID,
        clinic_id: UUID,
        actor,
        commit: bool = True,
    ) -> PatientMRN:
        patient = self._get_patient(patient_id, clinic_id)
        canonical_id = self._resolve_canonical_patient_id(patient_id=patient.id, clinic_id=clinic_id)

        active = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == canonical_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .first()
        )
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active MRN already exists for patient",
            )

        attempts = 0
        while attempts < 3:
            attempts += 1
            try:
                with self.db.begin_nested():
                    sequence = (
                        self.db.query(ClinicMrnSequence)
                        .filter(ClinicMrnSequence.clinic_id == clinic_id)
                        .with_for_update()
                        .first()
                    )
                    if not sequence:
                        sequence = ClinicMrnSequence(
                            clinic_id=clinic_id,
                            prefix=None,
                            next_value=1,
                        )
                        self.db.add(sequence)
                        self.db.flush()

                    seq_value = sequence.next_value
                    sequence.next_value = seq_value + 1

                    mrn_body = f"{seq_value:07d}"
                    check_digit = self._luhn_check_digit(mrn_body)
                    if sequence.prefix:
                        mrn_value = f"{sequence.prefix}-{mrn_body}-{check_digit}"
                    else:
                        mrn_value = f"{mrn_body}-{check_digit}"

                    now = datetime.now(timezone.utc)
                    mrn = PatientMRN(
                        clinic_id=clinic_id,
                        patient_id=canonical_id,
                        mrn=mrn_value.upper(),
                        status=MRNStatus.ACTIVE,
                        issued_at=now,
                        issued_by=actor.id,
                        check_digit=check_digit,
                    )
                    self.db.add(mrn)
                    self.db.flush()
                if commit:
                    self.db.commit()
                    self.db.refresh(mrn)
                return mrn
            except IntegrityError:
                if commit:
                    self.db.rollback()
                if attempts >= 3:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Failed to issue MRN due to concurrent allocation",
                    )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to issue MRN due to concurrent allocation",
        )

    def retire_active_mrn(self, *, patient_id: UUID, clinic_id: UUID, reason: str, retired_at: datetime | None = None) -> None:
        mrn = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == patient_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .first()
        )
        if not mrn:
            return
        mrn.status = MRNStatus.RETIRED
        mrn.retired_at = retired_at or datetime.now(timezone.utc)
        mrn.retire_reason = reason

    def restore_retired_mrn(self, *, patient_id: UUID, clinic_id: UUID, reason: str | None = None) -> None:
        mrn = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == patient_id,
                PatientMRN.status == MRNStatus.RETIRED,
            )
            .order_by(PatientMRN.retired_at.desc().nullslast())
            .first()
        )
        if not mrn:
            return
        existing_active = (
            self.db.query(PatientMRN)
            .filter(
                PatientMRN.clinic_id == clinic_id,
                PatientMRN.patient_id == patient_id,
                PatientMRN.status == MRNStatus.ACTIVE,
            )
            .first()
        )
        if existing_active:
            return
        mrn.status = MRNStatus.ACTIVE
        mrn.retired_at = None
        if reason:
            mrn.retire_reason = reason

    def _get_patient(self, patient_id: UUID, clinic_id: UUID) -> Patient:
        patient = (
            self.db.query(Patient)
            .filter(
                Patient.id == patient_id,
                Patient.clinic_id == clinic_id,
            )
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

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

    def _luhn_check_digit(self, number: str) -> str:
        digits = [int(char) for char in number]
        checksum = 0
        parity = len(digits) % 2
        for idx, digit in enumerate(digits):
            if idx % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return str((10 - (checksum % 10)) % 10)
