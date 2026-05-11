from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.models.clinic import Clinic
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab_foundation import LabSpecimenCreate
from app.schemas.lab_safety import StructuredLabResultCreate
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_catalog_seed_service import LabCatalogSeedService
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_request_service import LabRequestService
from app.services.lab_request_workflow_service import LabRequestWorkflowService
from app.services.lab_safety_service import LabSafetyService
from app.shared.enums import BillingReasonCode, Gender, ServiceLineKind, UserRole, VisitStatus


def _seed_rbs_workflow_context(db):
    clinic = Clinic(
        id=uuid.uuid4(),
        name="Workflow Clinic",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    LabCatalogSeedService(db).seed_kazaure_catalog(clinic_id=clinic.id)

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"doctor-{clinic.id}@example.test",
        password_hash="test",
        full_name="Workflow Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"cashier-{clinic.id}@example.test",
        password_hash="test",
        full_name="Workflow Cashier",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    lab_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"lab-{clinic.id}@example.test",
        password_hash="test",
        full_name="Workflow Lab",
        role=UserRole.LAB.value,
        is_active=True,
    )
    supervisor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email=f"supervisor-{clinic.id}@example.test",
        password_hash="test",
        full_name="Workflow Supervisor",
        role=UserRole.LAB_SUPERVISOR.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, lab_user, supervisor])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Workflow Patient",
        date_of_birth=date(1990, 1, 1),
        gender=Gender.MALE,
        phone_number="08000000033",
        address="Workflow Address",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
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
    visit.status = VisitStatus.LAB_REQUESTED
    db.add(visit)
    db.commit()

    chemical_unit = (
        db.query(ServiceLine)
        .filter(
            ServiceLine.clinic_id == clinic.id,
            ServiceLine.service_line_kind == ServiceLineKind.LAB_UNIT,
            ServiceLine.name == "Chemical Pathology",
        )
        .one()
    )

    BillingWorkflowService(db).start_shift(
        clinic_id=clinic.id,
        cashier_user=cashier,
        opening_float_minor=0,
    )
    BillingWorkflowService(db).pay_billing_items(
        clinic_id=clinic.id,
        visit_id=visit.id,
        billing_item_ids=[request.billing_item_id],
        payment_method=BillingReasonCode.CASH,
        cashier_user=cashier,
    )

    return {
        "clinic": clinic,
        "visit": visit,
        "request": request,
        "chemical_unit": chemical_unit,
        "lab_user": lab_user,
        "supervisor": supervisor,
    }


def test_workflow_state_shows_paid_rbs_request_defaults_and_pending_checklist(db):
    ctx = _seed_rbs_workflow_context(db)
    request = ctx["request"]
    request.lab_test_catalog_id = None
    request.lab_test_config_id = None
    request.target_unit_id = None
    db.add(request)
    db.commit()

    snapshot = LabRequestWorkflowService(db).get_workflow_state(lab_request=request)

    db.refresh(request)
    assert request.target_unit_id == ctx["chemical_unit"].id
    assert snapshot.unit_name == "Chemical Pathology"
    assert snapshot.specimen_defaults.specimen_type == "Blood"
    assert snapshot.specimen_defaults.specimen_source == "Blood"
    assert snapshot.specimen_defaults.container_type == "Fluoride oxalate / plain tube"
    assert snapshot.status_chips[0].value == "Paid"
    assert snapshot.checklist[0].state == "complete"
    assert snapshot.checklist[1].state == "pending"
    assert snapshot.completion_message == (
        "A received specimen is required before this lab request can be completed."
    )


def test_workflow_state_becomes_policy_aware_for_critical_rbs_result(db):
    ctx = _seed_rbs_workflow_context(db)
    request = ctx["request"]
    foundation = LabFoundationService(db)
    safety = LabSafetyService(db)

    foundation.create_specimen(
        lab_request=request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="Blood",
            container_type="Fluoride oxalate / plain tube",
            status="RECEIVED",
        ),
    )
    template = foundation.get_request_template(lab_request=request)
    field = template["fields"][0]
    result = safety.submit_structured_result(
        lab_request=request,
        actor_id=ctx["lab_user"].id,
        payload=StructuredLabResultCreate(
            values=[
                {
                    "template_field_id": field.id,
                    "value_number": 450,
                }
            ]
        ),
    )

    pending_snapshot = LabRequestWorkflowService(db).get_workflow_state(lab_request=request)
    assert pending_snapshot.completion_message == (
        "A verified and released result is required before this lab request can be completed."
    )
    assert pending_snapshot.checklist[3].state == "pending"
    assert pending_snapshot.checklist[4].state == "pending"
    assert pending_snapshot.can_complete is False

    safety.verify_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["supervisor"].id,
    )
    safety.release_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["supervisor"].id,
    )

    ready_snapshot = LabRequestWorkflowService(db).get_workflow_state(lab_request=request)
    assert ready_snapshot.checklist[3].state == "complete"
    assert ready_snapshot.checklist[4].state == "complete"
    assert ready_snapshot.checklist[5].state == "complete"
    assert ready_snapshot.can_complete is True
    assert ready_snapshot.completion_message == "This lab request is ready to be completed."


def test_workflow_state_blocks_completion_when_visit_is_not_lab_requested(db):
    ctx = _seed_rbs_workflow_context(db)
    request = ctx["request"]
    foundation = LabFoundationService(db)
    safety = LabSafetyService(db)

    foundation.create_specimen(
        lab_request=request,
        actor_id=ctx["lab_user"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="Blood",
            container_type="Fluoride oxalate / plain tube",
            status="RECEIVED",
        ),
    )
    template = foundation.get_request_template(lab_request=request)
    field = template["fields"][0]
    result = safety.submit_structured_result(
        lab_request=request,
        actor_id=ctx["lab_user"].id,
        payload=StructuredLabResultCreate(
            values=[
                {
                    "template_field_id": field.id,
                    "value_number": 120,
                }
            ]
        ),
    )
    safety.release_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["supervisor"].id,
    )

    ctx["visit"].status = VisitStatus.IN_CONSULTATION
    db.add(ctx["visit"])
    db.commit()

    snapshot = LabRequestWorkflowService(db).get_workflow_state(lab_request=request)

    assert snapshot.can_complete is False
    assert snapshot.status_chips[-1].value == "Blocked"
    assert snapshot.completion_message == (
        "The visit must be in LAB_REQUESTED before this lab request can be completed."
    )
    assert snapshot.checklist[-1].detail == "Move the visit to LAB_REQUESTED before completion."
