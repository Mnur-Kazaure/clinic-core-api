from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.department import Department
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.service_line import ServiceLine
from app.shared.enums import (
    LabResultFieldType,
    LabResultTemplateType,
    LabVerificationPolicy,
    ServiceLineKind,
)


@dataclass(frozen=True)
class SeedTemplateField:
    field_code: str
    field_name: str
    field_type: LabResultFieldType
    display_order: int
    is_required: bool = False
    unit: str | None = None
    reference_range_text: str | None = None
    reference_min: float | None = None
    reference_max: float | None = None
    reference_unit: str | None = None
    options_json: list[str] | dict | None = None
    validation_rules_json: dict | list | None = None


@dataclass(frozen=True)
class SeedTemplate:
    code: str
    name: str
    result_type: LabResultTemplateType
    description: str
    fields: tuple[SeedTemplateField, ...]
    version: int = 1


@dataclass(frozen=True)
class SeedTest:
    test_code: str
    test_name: str
    unit_name: str
    specimen_type: str
    template_code: str
    price_minor: int
    turnaround_time_minutes: int
    verification_policy: LabVerificationPolicy
    billing_name: str
    display_order: int
    critical_rules_json: dict | None = None
    allows_scientist_verification: bool = False
    scientist_verification_restricted: bool = False
    is_enabled: bool = True


LAB_DEPARTMENT_NAME = "Medical Laboratory"
LAB_ROOT_SERVICE_LINE_NAME = "Medical Laboratory"


SYSTEM_REFERENCE_TEMPLATES: tuple[SeedTemplate, ...] = (
    SeedTemplate(
        code="TPL_HEM_FBC_PANEL",
        name="Full Blood Count Panel",
        result_type=LabResultTemplateType.PANEL,
        description="Structured hematology panel for full blood count reporting.",
        fields=(
            SeedTemplateField(
                field_code="haemoglobin",
                field_name="Haemoglobin",
                field_type=LabResultFieldType.NUMBER,
                display_order=1,
                is_required=True,
                unit="g/dL",
                reference_range_text="12-16 g/dL",
                reference_min=12,
                reference_max=16,
                reference_unit="g/dL",
            ),
            SeedTemplateField(
                field_code="pcv",
                field_name="PCV",
                field_type=LabResultFieldType.NUMBER,
                display_order=2,
                is_required=True,
                unit="%",
                reference_range_text="36-46%",
                reference_min=36,
                reference_max=46,
                reference_unit="%",
            ),
            SeedTemplateField(
                field_code="wbc",
                field_name="WBC",
                field_type=LabResultFieldType.NUMBER,
                display_order=3,
                is_required=True,
                unit="x10^9/L",
                reference_range_text="4-11 x10^9/L",
                reference_min=4,
                reference_max=11,
                reference_unit="x10^9/L",
            ),
            SeedTemplateField(
                field_code="platelets",
                field_name="Platelets",
                field_type=LabResultFieldType.NUMBER,
                display_order=4,
                is_required=True,
                unit="x10^9/L",
                reference_range_text="150-450 x10^9/L",
                reference_min=150,
                reference_max=450,
                reference_unit="x10^9/L",
            ),
            SeedTemplateField(
                field_code="neutrophils",
                field_name="Neutrophils",
                field_type=LabResultFieldType.NUMBER,
                display_order=5,
                is_required=False,
                unit="%",
                reference_range_text="40-75%",
                reference_min=40,
                reference_max=75,
                reference_unit="%",
            ),
            SeedTemplateField(
                field_code="lymphocytes",
                field_name="Lymphocytes",
                field_type=LabResultFieldType.NUMBER,
                display_order=6,
                is_required=False,
                unit="%",
                reference_range_text="20-45%",
                reference_min=20,
                reference_max=45,
                reference_unit="%",
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_HEM_PCV_NUMERIC",
        name="Packed Cell Volume",
        result_type=LabResultTemplateType.NUMERIC,
        description="Single numeric packed cell volume template.",
        fields=(
            SeedTemplateField(
                field_code="pcv",
                field_name="PCV",
                field_type=LabResultFieldType.NUMBER,
                display_order=1,
                is_required=True,
                unit="%",
                reference_range_text="36-46%",
                reference_min=36,
                reference_max=46,
                reference_unit="%",
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_HEM_MP_MIXED",
        name="Malaria Parasite",
        result_type=LabResultTemplateType.MIXED,
        description="Mixed malaria parasite result template with density scale and optional comment.",
        fields=(
            SeedTemplateField(
                field_code="result",
                field_name="Result",
                field_type=LabResultFieldType.SELECT,
                display_order=1,
                is_required=True,
                options_json=["Positive", "Negative"],
            ),
            SeedTemplateField(
                field_code="parasite_density",
                field_name="Parasite Density",
                field_type=LabResultFieldType.SELECT,
                display_order=2,
                is_required=False,
                options_json=["Scanty", "*", "++", "+++", "++++"],
            ),
            SeedTemplateField(
                field_code="parasite_count",
                field_name="Parasite Count",
                field_type=LabResultFieldType.NUMBER,
                display_order=3,
                is_required=False,
                unit="parasites/uL",
                reference_unit="parasites/uL",
            ),
            SeedTemplateField(
                field_code="comment",
                field_name="Comment",
                field_type=LabResultFieldType.TEXT,
                display_order=4,
                is_required=False,
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_HEM_BLOOD_GROUP",
        name="Blood Group",
        result_type=LabResultTemplateType.SELECT,
        description="ABO and rhesus grouping template.",
        fields=(
            SeedTemplateField(
                field_code="abo_group",
                field_name="ABO Group",
                field_type=LabResultFieldType.SELECT,
                display_order=1,
                is_required=True,
                options_json=["A", "B", "AB", "O"],
            ),
            SeedTemplateField(
                field_code="rhesus",
                field_name="Rhesus",
                field_type=LabResultFieldType.SELECT,
                display_order=2,
                is_required=True,
                options_json=["Positive", "Negative"],
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_CHEM_GLUCOSE_NUMERIC",
        name="Blood Glucose",
        result_type=LabResultTemplateType.NUMERIC,
        description="Single numeric glucose template for fasting and random blood sugar.",
        fields=(
            SeedTemplateField(
                field_code="glucose",
                field_name="Glucose",
                field_type=LabResultFieldType.NUMBER,
                display_order=1,
                is_required=True,
                unit="mg/dL",
                reference_range_text="70-99 mg/dL",
                reference_min=70,
                reference_max=99,
                reference_unit="mg/dL",
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_CHEM_UE_PANEL",
        name="Urea and Electrolytes",
        result_type=LabResultTemplateType.PANEL,
        description="Chemical pathology panel for urea and electrolytes.",
        fields=(
            SeedTemplateField(
                field_code="sodium",
                field_name="Sodium",
                field_type=LabResultFieldType.NUMBER,
                display_order=1,
                is_required=True,
                unit="mmol/L",
                reference_range_text="135-145 mmol/L",
                reference_min=135,
                reference_max=145,
                reference_unit="mmol/L",
            ),
            SeedTemplateField(
                field_code="potassium",
                field_name="Potassium",
                field_type=LabResultFieldType.NUMBER,
                display_order=2,
                is_required=True,
                unit="mmol/L",
                reference_range_text="3.5-5.0 mmol/L",
                reference_min=3.5,
                reference_max=5.0,
                reference_unit="mmol/L",
            ),
            SeedTemplateField(
                field_code="chloride",
                field_name="Chloride",
                field_type=LabResultFieldType.NUMBER,
                display_order=3,
                is_required=True,
                unit="mmol/L",
                reference_range_text="98-107 mmol/L",
                reference_min=98,
                reference_max=107,
                reference_unit="mmol/L",
            ),
            SeedTemplateField(
                field_code="urea",
                field_name="Urea",
                field_type=LabResultFieldType.NUMBER,
                display_order=4,
                is_required=True,
                unit="mmol/L",
                reference_range_text="2.5-7.1 mmol/L",
                reference_min=2.5,
                reference_max=7.1,
                reference_unit="mmol/L",
            ),
            SeedTemplateField(
                field_code="creatinine",
                field_name="Creatinine",
                field_type=LabResultFieldType.NUMBER,
                display_order=5,
                is_required=True,
                unit="umol/L",
                reference_range_text="62-106 umol/L",
                reference_min=62,
                reference_max=106,
                reference_unit="umol/L",
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_CHEM_LFT_PANEL",
        name="Liver Function Test",
        result_type=LabResultTemplateType.PANEL,
        description="Chemical pathology panel for liver function testing.",
        fields=(
            SeedTemplateField(
                field_code="alt",
                field_name="ALT",
                field_type=LabResultFieldType.NUMBER,
                display_order=1,
                is_required=True,
                unit="U/L",
                reference_range_text="7-56 U/L",
                reference_min=7,
                reference_max=56,
                reference_unit="U/L",
            ),
            SeedTemplateField(
                field_code="ast",
                field_name="AST",
                field_type=LabResultFieldType.NUMBER,
                display_order=2,
                is_required=True,
                unit="U/L",
                reference_range_text="10-40 U/L",
                reference_min=10,
                reference_max=40,
                reference_unit="U/L",
            ),
            SeedTemplateField(
                field_code="alp",
                field_name="ALP",
                field_type=LabResultFieldType.NUMBER,
                display_order=3,
                is_required=True,
                unit="U/L",
                reference_range_text="44-147 U/L",
                reference_min=44,
                reference_max=147,
                reference_unit="U/L",
            ),
            SeedTemplateField(
                field_code="bilirubin",
                field_name="Bilirubin",
                field_type=LabResultFieldType.NUMBER,
                display_order=4,
                is_required=True,
                unit="umol/L",
                reference_range_text="5-21 umol/L",
                reference_min=5,
                reference_max=21,
                reference_unit="umol/L",
            ),
            SeedTemplateField(
                field_code="albumin",
                field_name="Albumin",
                field_type=LabResultFieldType.NUMBER,
                display_order=5,
                is_required=True,
                unit="g/L",
                reference_range_text="35-50 g/L",
                reference_min=35,
                reference_max=50,
                reference_unit="g/L",
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_MICRO_UMCS_MIXED_STRUCTURED",
        name="Urine M/C/S",
        result_type=LabResultTemplateType.MIXED_STRUCTURED,
        description="Semi-structured urine microscopy, culture, and sensitivity template.",
        fields=(
            SeedTemplateField(
                field_code="appearance",
                field_name="Appearance",
                field_type=LabResultFieldType.TEXT,
                display_order=1,
                is_required=True,
            ),
            SeedTemplateField(
                field_code="microscopy",
                field_name="Microscopy",
                field_type=LabResultFieldType.TEXT,
                display_order=2,
                is_required=True,
            ),
            SeedTemplateField(
                field_code="culture_result",
                field_name="Culture Result",
                field_type=LabResultFieldType.SELECT,
                display_order=3,
                is_required=True,
                options_json=["No Growth", "Growth Detected"],
            ),
            SeedTemplateField(
                field_code="organism",
                field_name="Organism",
                field_type=LabResultFieldType.TEXT,
                display_order=4,
                is_required=False,
            ),
            SeedTemplateField(
                field_code="sensitivity_table",
                field_name="Sensitivity Table",
                field_type=LabResultFieldType.JSON,
                display_order=5,
                is_required=False,
                validation_rules_json={"schema": "sensitivity_matrix"},
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_MICRO_STOOL_MIXED",
        name="Stool Microscopy",
        result_type=LabResultTemplateType.MIXED,
        description="Semi-structured stool microscopy template.",
        fields=(
            SeedTemplateField(
                field_code="parasite",
                field_name="Parasite",
                field_type=LabResultFieldType.SELECT,
                display_order=1,
                is_required=False,
                options_json=["Absent", "Present"],
            ),
            SeedTemplateField(
                field_code="rbc",
                field_name="RBC",
                field_type=LabResultFieldType.SELECT,
                display_order=2,
                is_required=False,
                options_json=["Present", "Absent"],
            ),
            SeedTemplateField(
                field_code="wbc",
                field_name="WBC",
                field_type=LabResultFieldType.SELECT,
                display_order=3,
                is_required=False,
                options_json=["Present", "Absent"],
            ),
        ),
    ),
    SeedTemplate(
        code="TPL_HISTO_BIOPSY_NARRATIVE",
        name="Biopsy Report",
        result_type=LabResultTemplateType.NARRATIVE,
        description="Narrative histopathology biopsy reporting template.",
        fields=(
            SeedTemplateField(
                field_code="macroscopy",
                field_name="Macroscopy",
                field_type=LabResultFieldType.TEXT,
                display_order=1,
                is_required=True,
            ),
            SeedTemplateField(
                field_code="microscopy",
                field_name="Microscopy",
                field_type=LabResultFieldType.TEXT,
                display_order=2,
                is_required=True,
            ),
            SeedTemplateField(
                field_code="diagnosis",
                field_name="Diagnosis",
                field_type=LabResultFieldType.TEXT,
                display_order=3,
                is_required=True,
            ),
            SeedTemplateField(
                field_code="comment",
                field_name="Comment",
                field_type=LabResultFieldType.TEXT,
                display_order=4,
                is_required=False,
            ),
        ),
    ),
)


KAZAURE_BASELINE_TESTS: tuple[SeedTest, ...] = (
    SeedTest(
        test_code="HEM_FBC",
        test_name="Full Blood Count (FBC)",
        unit_name="Haematology",
        specimen_type="Blood",
        template_code="TPL_HEM_FBC_PANEL",
        price_minor=200000,
        turnaround_time_minutes=60,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
        billing_name="Full Blood Count (FBC)",
        display_order=1,
        critical_rules_json={
            "fields": {
                "haemoglobin": {
                    "critical_low": 6,
                    "severity": "CRITICAL",
                    "message": "Critical haemoglobin level",
                },
                "platelets": {
                    "critical_low": 50,
                    "severity": "CRITICAL",
                    "message": "Critical platelet count",
                },
            }
        },
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="HEM_PCV",
        test_name="Packed Cell Volume (PCV)",
        unit_name="Haematology",
        specimen_type="Blood",
        template_code="TPL_HEM_PCV_NUMERIC",
        price_minor=120000,
        turnaround_time_minutes=30,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_CRITICAL,
        billing_name="Packed Cell Volume (PCV)",
        display_order=2,
        critical_rules_json={
            "critical_low": 18,
            "critical_high": 60,
            "severity": "CRITICAL",
            "message": "Critical PCV result",
        },
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="HEM_MP",
        test_name="Malaria Parasite (MP)",
        unit_name="Haematology",
        specimen_type="Blood",
        template_code="TPL_HEM_MP_MIXED",
        price_minor=50000,
        turnaround_time_minutes=30,
        verification_policy=LabVerificationPolicy.OPTIONAL,
        billing_name="Malaria Parasite (MP)",
        display_order=3,
    ),
    SeedTest(
        test_code="HEM_BG",
        test_name="Blood Group",
        unit_name="Haematology",
        specimen_type="Blood",
        template_code="TPL_HEM_BLOOD_GROUP",
        price_minor=120000,
        turnaround_time_minutes=30,
        verification_policy=LabVerificationPolicy.OPTIONAL,
        billing_name="Blood Group",
        display_order=4,
    ),
    SeedTest(
        test_code="CHEM_FBS",
        test_name="Fasting Blood Sugar (FBS)",
        unit_name="Chemical Pathology",
        specimen_type="Blood",
        template_code="TPL_CHEM_GLUCOSE_NUMERIC",
        price_minor=100000,
        turnaround_time_minutes=60,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_CRITICAL,
        billing_name="Fasting Blood Sugar (FBS)",
        display_order=1,
        critical_rules_json={
            "critical_low": 50,
            "critical_high": 400,
            "severity": "CRITICAL",
            "message": "Critical fasting blood sugar",
        },
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="CHEM_RBS",
        test_name="Random Blood Sugar (RBS)",
        unit_name="Chemical Pathology",
        specimen_type="Blood",
        template_code="TPL_CHEM_GLUCOSE_NUMERIC",
        price_minor=100000,
        turnaround_time_minutes=45,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_CRITICAL,
        billing_name="Random Blood Sugar (RBS)",
        display_order=2,
        critical_rules_json={
            "critical_low": 50,
            "critical_high": 400,
            "severity": "CRITICAL",
            "message": "Critical random blood sugar",
        },
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="CHEM_UE",
        test_name="Urea & Electrolytes (U&E)",
        unit_name="Chemical Pathology",
        specimen_type="Blood",
        template_code="TPL_CHEM_UE_PANEL",
        price_minor=350000,
        turnaround_time_minutes=120,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_CRITICAL,
        billing_name="Urea & Electrolytes (U&E)",
        display_order=3,
        critical_rules_json={
            "fields": {
                "potassium": {
                    "critical_low": 2.5,
                    "critical_high": 6.5,
                    "severity": "CRITICAL",
                    "message": "Critical potassium level",
                }
            }
        },
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="CHEM_LFT",
        test_name="Liver Function Test (LFT)",
        unit_name="Chemical Pathology",
        specimen_type="Blood",
        template_code="TPL_CHEM_LFT_PANEL",
        price_minor=300000,
        turnaround_time_minutes=180,
        verification_policy=LabVerificationPolicy.OPTIONAL,
        billing_name="Liver Function Test (LFT)",
        display_order=4,
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="MICRO_UMCS",
        test_name="Urine M/C/S",
        unit_name="Microbiology",
        specimen_type="Urine",
        template_code="TPL_MICRO_UMCS_MIXED_STRUCTURED",
        price_minor=300000,
        turnaround_time_minutes=2880,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
        billing_name="Urine M/C/S",
        display_order=1,
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="MICRO_STOOL",
        test_name="Stool Microscopy",
        unit_name="Microbiology",
        specimen_type="Stool",
        template_code="TPL_MICRO_STOOL_MIXED",
        price_minor=120000,
        turnaround_time_minutes=180,
        verification_policy=LabVerificationPolicy.OPTIONAL,
        billing_name="Stool Microscopy",
        display_order=2,
        allows_scientist_verification=True,
    ),
    SeedTest(
        test_code="HISTO_BIOPSY",
        test_name="Biopsy Report",
        unit_name="Histopathology",
        specimen_type="Tissue",
        template_code="TPL_HISTO_BIOPSY_NARRATIVE",
        price_minor=750000,
        turnaround_time_minutes=7200,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
        billing_name="Biopsy Report",
        display_order=1,
        allows_scientist_verification=False,
        scientist_verification_restricted=True,
    ),
)


class LabCatalogSeedService:
    def __init__(self, db: Session):
        self.db = db

    def seed_kazaure_catalog(self, *, clinic_id: UUID, commit: bool = True) -> None:
        clinic = self.db.query(Clinic).filter(Clinic.id == clinic_id).first()
        if clinic is None:
            raise ValueError("Clinic not found for lab catalog seeding")

        units = self._ensure_lab_units(clinic_id=clinic_id)
        templates = self._ensure_templates()

        for seed in KAZAURE_BASELINE_TESTS:
            unit = units[seed.unit_name]
            template = templates[seed.template_code]
            catalog = self._ensure_catalog_entry(
                clinic_id=clinic_id,
                seed=seed,
                unit_id=unit.id,
                template_id=template.id,
            )
            config = self._ensure_config_entry(
                clinic_id=clinic_id,
                catalog_id=catalog.id,
                unit_id=unit.id,
                seed=seed,
                currency=clinic.billing_currency,
            )
            self._sync_charge_catalog_entry(
                clinic_id=clinic_id,
                unit_name=unit.name,
                seed=seed,
                currency=clinic.billing_currency,
            )
            catalog.unit_id = config.unit_id
            self.db.add(catalog)

        self.db.flush()
        if commit:
            self.db.commit()

    def _ensure_lab_units(self, *, clinic_id: UUID) -> dict[str, ServiceLine]:
        department = (
            self.db.query(Department)
            .filter(
                Department.clinic_id == clinic_id,
                Department.name.ilike(LAB_DEPARTMENT_NAME),
            )
            .first()
        )
        if department is None:
            department = Department(clinic_id=clinic_id, name=LAB_DEPARTMENT_NAME)
            self.db.add(department)
            self.db.flush()

        root = (
            self.db.query(ServiceLine)
            .filter(
                ServiceLine.clinic_id == clinic_id,
                ServiceLine.name.ilike(LAB_ROOT_SERVICE_LINE_NAME),
                ServiceLine.parent_id.is_(None),
            )
            .first()
        )
        if root is None:
            root = ServiceLine(
                clinic_id=clinic_id,
                name=LAB_ROOT_SERVICE_LINE_NAME,
                parent_id=None,
                department_id=department.id,
                requires_doctor=False,
                service_line_kind=ServiceLineKind.LAB_UNIT,
                is_active=True,
            )
            self.db.add(root)
            self.db.flush()
        else:
            root.department_id = department.id
            root.requires_doctor = False
            root.service_line_kind = ServiceLineKind.LAB_UNIT
            root.is_active = True
            self.db.add(root)
            self.db.flush()

        units: dict[str, ServiceLine] = {}
        for name in ("Haematology", "Chemical Pathology", "Microbiology", "Histopathology"):
            line = (
                self.db.query(ServiceLine)
                .filter(
                    ServiceLine.clinic_id == clinic_id,
                    ServiceLine.name.ilike(name),
                )
                .order_by(ServiceLine.parent_id.asc().nullsfirst())
                .first()
            )
            if line is None:
                line = ServiceLine(
                    clinic_id=clinic_id,
                    name=name,
                    parent_id=root.id,
                    department_id=department.id,
                    requires_doctor=False,
                    service_line_kind=ServiceLineKind.LAB_UNIT,
                    is_active=True,
                )
                self.db.add(line)
                self.db.flush()
            else:
                line.parent_id = root.id
                line.department_id = department.id
                line.requires_doctor = False
                line.service_line_kind = ServiceLineKind.LAB_UNIT
                line.is_active = True
                self.db.add(line)
                self.db.flush()
            units[name] = line
        return units

    def _ensure_templates(self) -> dict[str, LabResultTemplate]:
        templates: dict[str, LabResultTemplate] = {}
        for seed in SYSTEM_REFERENCE_TEMPLATES:
            template = (
                self.db.query(LabResultTemplate)
                .filter(
                    LabResultTemplate.code == seed.code,
                    LabResultTemplate.version == seed.version,
                )
                .first()
            )
            if template is None:
                template = LabResultTemplate(
                    code=seed.code,
                    name=seed.name,
                    result_type=seed.result_type,
                    version=seed.version,
                    description=seed.description,
                    is_active=True,
                )
                self.db.add(template)
                self.db.flush()
            else:
                template.name = seed.name
                template.result_type = seed.result_type
                template.description = seed.description
                template.is_active = True
                self.db.add(template)
                self.db.flush()

            self._ensure_template_fields(template_id=template.id, seed=seed)
            templates[seed.code] = template
        return templates

    def _ensure_template_fields(self, *, template_id: UUID, seed: SeedTemplate) -> None:
        for field_seed in seed.fields:
            field = (
                self.db.query(LabResultTemplateField)
                .filter(
                    LabResultTemplateField.template_id == template_id,
                    LabResultTemplateField.field_code == field_seed.field_code,
                )
                .first()
            )
            if field is None:
                field = LabResultTemplateField(
                    template_id=template_id,
                    field_code=field_seed.field_code,
                    field_name=field_seed.field_name,
                    field_type=field_seed.field_type,
                    display_order=field_seed.display_order,
                    is_required=field_seed.is_required,
                    unit=field_seed.unit,
                    reference_range_text=field_seed.reference_range_text,
                    reference_min=field_seed.reference_min,
                    reference_max=field_seed.reference_max,
                    reference_unit=field_seed.reference_unit,
                    options_json=field_seed.options_json,
                    validation_rules_json=field_seed.validation_rules_json,
                )
                self.db.add(field)
                continue

            field.field_name = field_seed.field_name
            field.field_type = field_seed.field_type
            field.display_order = field_seed.display_order
            field.is_required = field_seed.is_required
            field.unit = field_seed.unit
            field.reference_range_text = field_seed.reference_range_text
            field.reference_min = field_seed.reference_min
            field.reference_max = field_seed.reference_max
            field.reference_unit = field_seed.reference_unit
            field.options_json = field_seed.options_json
            field.validation_rules_json = field_seed.validation_rules_json
            self.db.add(field)

    def _ensure_catalog_entry(
        self,
        *,
        clinic_id: UUID,
        seed: SeedTest,
        unit_id: UUID,
        template_id: UUID,
    ) -> LabTestCatalog:
        catalog = (
            self.db.query(LabTestCatalog)
            .filter(
                LabTestCatalog.clinic_id == clinic_id,
                LabTestCatalog.test_code == seed.test_code,
            )
            .first()
        )
        if catalog is None:
            catalog = (
                self.db.query(LabTestCatalog)
                .filter(
                    LabTestCatalog.clinic_id == clinic_id,
                    LabTestCatalog.test_name == seed.test_name,
                )
                .first()
            )

        if catalog is None:
            catalog = LabTestCatalog(
                clinic_id=clinic_id,
                test_code=seed.test_code,
                test_name=seed.test_name,
                unit_id=unit_id,
                specimen_type=seed.specimen_type,
                default_template_id=template_id,
                is_active=True,
            )
            self.db.add(catalog)
            self.db.flush()
            return catalog

        catalog.test_code = seed.test_code
        catalog.test_name = seed.test_name
        catalog.unit_id = unit_id
        catalog.specimen_type = seed.specimen_type
        catalog.default_template_id = template_id
        catalog.is_active = True
        self.db.add(catalog)
        self.db.flush()
        return catalog

    def _ensure_config_entry(
        self,
        *,
        clinic_id: UUID,
        catalog_id: UUID,
        unit_id: UUID,
        seed: SeedTest,
        currency: str,
    ) -> LabTestConfig:
        config = (
            self.db.query(LabTestConfig)
            .filter(
                LabTestConfig.clinic_id == clinic_id,
                LabTestConfig.catalog_test_id == catalog_id,
            )
            .first()
        )
        if config is None:
            config = LabTestConfig(
                clinic_id=clinic_id,
                catalog_test_id=catalog_id,
                unit_id=unit_id,
                price_minor=seed.price_minor,
                currency=currency,
                turnaround_time_minutes=seed.turnaround_time_minutes,
                display_order=seed.display_order,
                is_enabled=seed.is_enabled,
                billing_name=seed.billing_name,
                verification_policy=seed.verification_policy,
                allows_scientist_verification=seed.allows_scientist_verification,
                scientist_verification_restricted=seed.scientist_verification_restricted,
                critical_rules_json=seed.critical_rules_json,
            )
            self.db.add(config)
            self.db.flush()
            return config

        config.unit_id = unit_id
        config.price_minor = seed.price_minor
        config.currency = currency
        config.turnaround_time_minutes = seed.turnaround_time_minutes
        config.display_order = seed.display_order
        config.is_enabled = seed.is_enabled
        config.billing_name = seed.billing_name
        config.verification_policy = seed.verification_policy
        config.allows_scientist_verification = seed.allows_scientist_verification
        config.scientist_verification_restricted = seed.scientist_verification_restricted
        config.critical_rules_json = seed.critical_rules_json
        self.db.add(config)
        self.db.flush()
        return config

    def _sync_charge_catalog_entry(
        self,
        *,
        clinic_id: UUID,
        unit_name: str,
        seed: SeedTest,
        currency: str,
    ) -> None:
        charge = (
            self.db.query(ChargeCatalog)
            .filter(
                ChargeCatalog.clinic_id == clinic_id,
                ChargeCatalog.code == seed.test_code,
            )
            .first()
        )
        if charge is None:
            charge = ChargeCatalog(
                clinic_id=clinic_id,
                code=seed.test_code,
                name=seed.billing_name,
                category=unit_name,
                default_amount_minor=seed.price_minor,
                currency=currency,
                active=seed.is_enabled,
            )
            self.db.add(charge)
            return

        charge.name = seed.billing_name
        charge.category = unit_name
        charge.default_amount_minor = seed.price_minor
        charge.currency = currency
        charge.active = seed.is_enabled
        self.db.add(charge)
