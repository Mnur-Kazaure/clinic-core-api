import uuid
from datetime import date, datetime, timezone

import pytest
from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_specimen import LabSpecimen
from app.models.lab_specimen_event import LabSpecimenEvent
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab_foundation import LabSpecimenCreate, LabSpecimenEventCreate
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_request_service import LabRequestService
from app.services.lab_workspace_service import LabWorkspaceService
from app.shared.enums import (
    BillingReasonCode,
    Gender,
    LabRequestWorkflowStatus,
    LabResultFieldType,
    LabResultTemplateType,
    LabSpecimenEventType,
    LabSpecimenRejectionReasonCode,
    LabSpecimenStatus,
    UserRole,
    VisitStatus,
)
from fastapi import HTTPException


def _seed_foundation_context(db, clinic_id: uuid.UUID):
    code_suffix = clinic_id.hex[:8].upper()
    clinic = Clinic(
        id=clinic_id,
        name="Lab Foundation Clinic",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    unit = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Haematology Unit",
        parent_id=None,
        department_id=None,
        default_child_id=None,
        requires_doctor=False,
        is_active=True,
    )
    db.add(unit)
    db.commit()

    template = LabResultTemplate(
        id=uuid.uuid4(),
        code=f"MALARIA_TEMPLATE_{code_suffix}",
        name=f"Malaria Parasite Template {code_suffix}",
        result_type=LabResultTemplateType.QUALITATIVE,
        version=1,
        is_active=True,
    )
    db.add(template)
    db.commit()

    field = LabResultTemplateField(
        id=uuid.uuid4(),
        template_id=template.id,
        field_code="RESULT",
        field_name="Result",
        field_type=LabResultFieldType.SELECT,
        display_order=1,
        is_required=True,
        options_json=["Positive", "Negative"],
    )
    db.add(field)
    db.commit()

    catalog = LabTestCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        test_code="LAB_MALARIA_PARASITE",
        test_name="Malaria Parasite",
        unit_id=unit.id,
        specimen_type="Blood",
        default_template_id=template.id,
        is_active=True,
    )
    db.add(catalog)
    db.commit()

    config = LabTestConfig(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        catalog_test_id=catalog.id,
        unit_id=unit.id,
        price_minor=150000,
        currency="NGN",
        turnaround_time_minutes=60,
        display_order=1,
        is_enabled=True,
        billing_name="Malaria Parasite",
        critical_rules_json=None,
    )
    db.add(config)
    db.commit()

    charge = ChargeCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="LAB_MALARIA_PARASITE",
        name="Malaria Parasite",
        category="LAB",
        default_amount_minor=150000,
        currency="NGN",
        active=True,
    )
    db.add(charge)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Foundation Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cashier-{clinic_id}@example.test",
        password_hash="test",
        full_name="Foundation Cashier",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    lab_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-{clinic_id}@example.test",
        password_hash="test",
        full_name="Foundation Lab",
        role=UserRole.LAB.value,
        is_active=True,
    )
    lab_scientist = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-scientist-{clinic_id}@example.test",
        password_hash="test",
        full_name="Foundation Scientist",
        role=UserRole.LAB_SCIENTIST.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, lab_user, lab_scientist])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Foundation Patient",
        date_of_birth=date(1990, 1, 1),
        gender=Gender.FEMALE,
        phone_number="08000000011",
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

    return {
        "clinic": clinic,
        "unit": unit,
        "template": template,
        "field": field,
        "catalog": catalog,
        "config": config,
        "doctor": doctor,
        "cashier": cashier,
        "lab_user": lab_user,
        "lab_scientist": lab_scientist,
        "patient": patient,
        "visit": visit,
    }


def test_lab_request_links_catalog_and_payment_sets_workflow_paid(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)

    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )

    assert lab_request.lab_test_catalog_id == ctx["catalog"].id
    assert lab_request.lab_test_config_id == ctx["config"].id
    assert lab_request.target_unit_id == ctx["unit"].id
    assert lab_request.workflow_status == LabRequestWorkflowStatus.ORDERED

    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )
    db.refresh(lab_request)

    assert lab_request.workflow_status == LabRequestWorkflowStatus.PAID


def test_create_specimen_generates_accession_and_events(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )

    service = LabFoundationService(db)
    specimen_one = service.create_specimen(
        lab_request=lab_request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="blood",
            container_type="EDTA tube",
            collection_site="venous",
            specimen_sequence=1,
            print_label=True,
        ),
    )
    specimen_two = service.create_specimen(
        lab_request=lab_request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="blood",
            container_type="EDTA tube",
            collection_site="venous",
            specimen_sequence=2,
        ),
    )

    today_prefix = datetime.now(timezone.utc).strftime("LAB-%Y%m%d-")
    assert specimen_one.accession_number.startswith(today_prefix)
    assert specimen_two.accession_number.startswith(today_prefix)
    assert specimen_one.accession_number.endswith("00001")
    assert specimen_two.accession_number.endswith("00002")

    db.refresh(lab_request)
    assert lab_request.workflow_status == LabRequestWorkflowStatus.AWAITING_SPECIMEN

    events = (
        db.query(LabSpecimenEvent)
        .filter(LabSpecimenEvent.specimen_id == specimen_one.id)
        .order_by(LabSpecimenEvent.performed_at.asc())
        .all()
    )
    assert [event.event_type for event in events] == [
        LabSpecimenEventType.CREATED,
        LabSpecimenEventType.LABEL_PRINTED,
    ]


def test_specimen_events_transition_status_and_request_workflow(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )

    service = LabFoundationService(db)
    specimen = service.create_specimen(
        lab_request=lab_request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="blood",
            status=LabSpecimenStatus.PENDING_COLLECTION,
        ),
    )

    service.record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenEventCreate(event_type=LabSpecimenEventType.COLLECTED),
    )
    service.record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenEventCreate(event_type=LabSpecimenEventType.RECEIVED),
    )
    service.record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenEventCreate(event_type=LabSpecimenEventType.ANALYSIS_STARTED),
    )

    db.refresh(specimen)
    db.refresh(lab_request)
    assert specimen.status == LabSpecimenStatus.IN_PROCESS
    assert lab_request.workflow_status == LabRequestWorkflowStatus.IN_ANALYSIS

    service.record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
        payload=LabSpecimenEventCreate(
            event_type=LabSpecimenEventType.REJECTED,
            rejection_reason_code=LabSpecimenRejectionReasonCode.OTHER,
            rejection_reason_text="Control sample failed",
        ),
    )

    db.refresh(specimen)
    assert specimen.status == LabSpecimenStatus.REJECTED

    recollection_event = service.record_specimen_event(
        specimen_id=specimen.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenEventCreate(
            event_type=LabSpecimenEventType.RECOLLECTION_REQUESTED,
            notes="Patient to return for repeat collection",
        ),
    )
    db.refresh(lab_request)
    assert recollection_event.event_type == LabSpecimenEventType.RECOLLECTION_REQUESTED
    assert lab_request.workflow_status == LabRequestWorkflowStatus.AWAITING_SPECIMEN


def test_technician_rejection_reasons_are_limited(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )
    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )

    service = LabFoundationService(db)
    specimen = service.create_specimen(
        lab_request=lab_request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="blood",
            status=LabSpecimenStatus.RECEIVED,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        service.record_specimen_event(
            specimen_id=specimen.id,
            clinic_id=ctx["clinic"].id,
            actor_id=ctx["lab_user"].id,
            payload=LabSpecimenEventCreate(
                event_type=LabSpecimenEventType.REJECTED,
                rejection_reason_code=LabSpecimenRejectionReasonCode.HEMOLYSED_SAMPLE,
                rejection_reason_text="Sample quality issue",
            ),
        )

    assert exc.value.status_code == 403


def test_get_request_template_repairs_missing_seeded_request_links(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )
    lab_request.lab_test_catalog_id = None
    lab_request.lab_test_config_id = None
    lab_request.target_unit_id = None
    db.add(lab_request)
    db.commit()

    template = LabFoundationService(db).get_request_template(lab_request=lab_request)

    db.refresh(lab_request)
    assert template["id"] == ctx["template"].id
    assert lab_request.lab_test_catalog_id == ctx["catalog"].id
    assert lab_request.lab_test_config_id == ctx["config"].id
    assert lab_request.target_unit_id == ctx["unit"].id


def test_workspace_repairs_paid_seeded_request_before_counting_unrouted(db, clinic_id):
    ctx = _seed_foundation_context(db, clinic_id)
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA_PARASITE",
        doctor_id=ctx["doctor"].id,
        actor=ctx["doctor"],
    )
    lab_request.lab_test_catalog_id = None
    lab_request.lab_test_config_id = None
    lab_request.target_unit_id = None
    db.add(lab_request)
    db.commit()

    BillingWorkflowService(db).start_shift(
        clinic_id=ctx["clinic"].id,
        cashier_user=ctx["cashier"],
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=ctx["clinic"].id,
        visit_id=ctx["visit"].id,
        billing_item_ids=[lab_request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=ctx["cashier"],
    )

    overview = LabWorkspaceService(db).get_unit_overview(
        clinic_id=ctx["clinic"].id,
        unit=ctx["unit"],
    )

    db.refresh(lab_request)
    assert lab_request.target_unit_id == ctx["unit"].id
    assert overview.unrouted_requests == 0
    assert overview.pending_requests == 1

