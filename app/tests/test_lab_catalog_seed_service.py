import uuid
from datetime import date, datetime, timezone

from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_catalog_seed_service import LabCatalogSeedService
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_request_service import LabRequestService
from app.services.lab_workspace_service import LabWorkspaceService
from app.shared.enums import (
    BillingReasonCode,
    Gender,
    LabResultTemplateType,
    LabVerificationPolicy,
    ServiceLineKind,
    UserRole,
    VisitStatus,
)


def test_kazaure_lab_seed_creates_units_templates_catalog_and_config(db):
    clinic_id = uuid.uuid4()
    db.add(Clinic(id=clinic_id, name="Kazaure Seed Clinic", billing_currency="NGN"))
    db.commit()

    seeder = LabCatalogSeedService(db)
    seeder.seed_kazaure_catalog(clinic_id=clinic_id)
    seeder.seed_kazaure_catalog(clinic_id=clinic_id)

    unit_names = {
        row.name
        for row in db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic_id,
            ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            ServiceLine.parent_id.is_not(None),
        )
        .all()
    }
    assert unit_names == {
        "Haematology",
        "Chemical Pathology",
        "Microbiology",
        "Histopathology",
    }

    template = (
        db.query(LabResultTemplate)
        .filter(LabResultTemplate.code == "TPL_MICRO_UMCS_MIXED_STRUCTURED")
        .one()
    )
    assert template.result_type == LabResultTemplateType.MIXED_STRUCTURED

    fbc_catalog = (
        db.query(LabTestCatalog)
        .filter(
            LabTestCatalog.clinic_id == clinic_id,
            LabTestCatalog.test_code == "HEM_FBC",
        )
        .one()
    )
    assert fbc_catalog.test_name == "Full Blood Count (FBC)"
    assert fbc_catalog.specimen_type == "Blood"

    fbc_config = (
        db.query(LabTestConfig)
        .filter(
            LabTestConfig.clinic_id == clinic_id,
            LabTestConfig.catalog_test_id == fbc_catalog.id,
        )
        .one()
    )
    assert fbc_config.unit_id == fbc_catalog.unit_id
    assert fbc_config.price_minor == 200000
    assert fbc_config.turnaround_time_minutes == 60
    assert fbc_config.display_order == 1
    assert fbc_config.verification_policy == LabVerificationPolicy.REQUIRED_BEFORE_RELEASE
    assert fbc_config.allows_scientist_verification is True
    assert isinstance(fbc_config.critical_rules_json, dict)
    assert db.query(LabTestCatalog).filter(LabTestCatalog.clinic_id == clinic_id).count() == 11
    assert (
        db.query(LabTestConfig)
        .filter(LabTestConfig.clinic_id == clinic_id)
        .count()
        == 11
    )

    fbc_charge = (
        db.query(ChargeCatalog)
        .filter(
            ChargeCatalog.clinic_id == clinic_id,
            ChargeCatalog.code == "HEM_FBC",
        )
        .one()
    )
    assert fbc_charge.name == "Full Blood Count (FBC)"
    assert fbc_charge.category == "Haematology"
    assert fbc_charge.default_amount_minor == 200000


def test_lab_charge_items_use_seeded_catalog_grouping_and_display_order(db):
    clinic_id = uuid.uuid4()
    db.add(Clinic(id=clinic_id, name="Billing Seed Clinic", billing_currency="NGN"))
    db.commit()

    LabCatalogSeedService(db).seed_kazaure_catalog(clinic_id=clinic_id)

    items = BillingWorkflowService(db).list_charge_items(
        clinic_id=clinic_id,
        service_type="LAB_TEST",
    )

    haematology_codes = [item["code"] for item in items if item["category"] == "Haematology"]
    assert haematology_codes == ["HEM_FBC", "HEM_PCV", "HEM_MP", "HEM_BG"]

    chemistry_codes = [item["code"] for item in items if item["category"] == "Chemical Pathology"]
    assert chemistry_codes == ["CHEM_FBS", "CHEM_RBS", "CHEM_UE", "CHEM_LFT"]

    assert all(not item["code"].startswith("LAB_") for item in items)
    assert all(item["display_order"] is not None for item in items)


def test_seeded_rbs_request_repairs_and_resolves_template_in_chemical_pathology(db):
    clinic_id = uuid.uuid4()
    clinic = Clinic(id=clinic_id, name="Chemical Seed Clinic", billing_currency="NGN")
    db.add(clinic)
    db.commit()

    LabCatalogSeedService(db).seed_kazaure_catalog(clinic_id=clinic_id)

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Chemical Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cashier-{clinic_id}@example.test",
        password_hash="test",
        full_name="Chemical Cashier",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    db.add_all([doctor, cashier])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Chemical Patient",
        date_of_birth=date(1991, 1, 1),
        gender=Gender.MALE,
        phone_number="08000000022",
        address="Test Address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    request = LabRequestService(db).create_request(
        visit=visit,
        test_name="Random Blood Sugar (RBS)",
        test_code="CHEM_RBS",
        doctor_id=doctor.id,
        actor=doctor,
    )
    request.lab_test_catalog_id = None
    request.lab_test_config_id = None
    request.target_unit_id = None
    db.add(request)
    db.commit()

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic_id,
        cashier_user=cashier,
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic_id,
        visit_id=visit.id,
        billing_item_ids=[request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )

    chemical_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic_id,
            ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            ServiceLine.name == "Chemical Pathology",
        )
        .one()
    )

    template = LabFoundationService(db).get_request_template(lab_request=request)
    overview = LabWorkspaceService(db).get_unit_overview(
        clinic_id=clinic_id,
        unit=chemical_unit,
    )

    db.refresh(request)
    assert request.target_unit_id == chemical_unit.id
    assert request.lab_test_catalog_id is not None
    assert request.lab_test_config_id is not None
    assert template["code"] == "TPL_CHEM_GLUCOSE_NUMERIC"
    assert overview.unrouted_requests == 0
    assert overview.pending_requests == 1
