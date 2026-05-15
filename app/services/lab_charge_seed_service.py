from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic


@dataclass(frozen=True)
class LabChargeSeed:
    name: str
    category: str
    default_amount_minor: int


DEFAULT_LAB_CHARGE_CATALOG: tuple[LabChargeSeed, ...] = (
    LabChargeSeed("Hemoglobin Estimation (Hb)", "Hematology & Blood", 150000),
    LabChargeSeed("Packed Cell Volume (PCV)", "Hematology & Blood", 120000),
    LabChargeSeed("Sickling Test", "Hematology & Blood", 100000),
    LabChargeSeed("Blood Grouping", "Hematology & Blood", 120000),
    LabChargeSeed("Urinalysis", "Urine & Stool", 100000),
    LabChargeSeed("Urine Microscopy", "Urine & Stool", 120000),
    LabChargeSeed("Stool Microscopy", "Urine & Stool", 120000),
    LabChargeSeed("Pregnancy Test (Urine hCG)", "Screening & Metabolic", 100000),
    LabChargeSeed("Blood Glucose (Random)", "Screening & Metabolic", 100000),
    LabChargeSeed("Blood Glucose (Fasting)", "Screening & Metabolic", 100000),
    LabChargeSeed("VDRL", "Infectious Disease", 120000),
    LabChargeSeed("Hepatitis B Surface Antigen (HBsAg)", "Infectious Disease", 200000),
    LabChargeSeed("Hepatitis C Antibody (HCV)", "Infectious Disease", 200000),
    LabChargeSeed("HIV Test", "Infectious Disease", 150000),
    LabChargeSeed("Sputum AFB", "Infectious Disease", 200000),
    LabChargeSeed("Malaria Parasite Microscopy (MPS)", "Infectious Disease", 100000),
    LabChargeSeed("Malaria Rapid Diagnostic Test (mRDT)", "Infectious Disease", 120000),
    LabChargeSeed("Widal Test", "Infectious Disease", 120000),
    LabChargeSeed("H. pylori Test", "Infectious Disease", 200000),
    LabChargeSeed(
        "Blood Donor Screening (Weight, Height, BP, Hb/PCV)",
        "Blood Transfusion Services",
        200000,
    ),
    LabChargeSeed(
        "Donor Blood Screening (HIV, HBsAg, HCV, VDRL)",
        "Blood Transfusion Services",
        350000,
    ),
    LabChargeSeed("Blood Bag and Giving Set", "Blood Transfusion Services", 250000),
)


def _normalize_code_fragment(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def build_lab_charge_code(name: str) -> str:
    return f"LAB_{_normalize_code_fragment(name)}"


class LabChargeSeedService:
    def __init__(self, db):
        self.db = db

    def seed_default_lab_charges(self, *, clinic_id: UUID) -> None:
        clinic = (
            self.db.query(Clinic)
            .filter(Clinic.id == clinic_id)
            .first()
        )
        if clinic is None:
            return

        for row in DEFAULT_LAB_CHARGE_CATALOG:
            code = build_lab_charge_code(row.name)
            existing = (
                self.db.query(ChargeCatalog)
                .filter(
                    ChargeCatalog.clinic_id == clinic_id,
                    ChargeCatalog.code == code,
                )
                .first()
            )
            if existing:
                existing.name = row.name
                existing.category = row.category
                existing.default_amount_minor = row.default_amount_minor
                existing.currency = clinic.billing_currency
                existing.active = True
                self.db.add(existing)
                continue

            self.db.add(
                ChargeCatalog(
                    clinic_id=clinic_id,
                    code=code,
                    name=row.name,
                    category=row.category,
                    default_amount_minor=row.default_amount_minor,
                    currency=clinic.billing_currency,
                    active=True,
                )
            )
