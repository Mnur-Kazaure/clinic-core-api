import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.charge_catalog import ChargeCatalog
from app.models.clinic import Clinic
from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_qc_result import LabQcResult
from app.models.lab_qc_run import LabQcRun
from app.models.lab_result import LabResult
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.lab_test_catalog import LabTestCatalog
from app.models.lab_test_config import LabTestConfig
from app.models.event_log import EventLog
from app.models.patient import Patient
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.schemas.lab_foundation import LabSpecimenCreate
from app.schemas.lab_safety import (
    LabQcResultCreate,
    LabQcRunCreate,
    LabResultAmendCreate,
    LabResultReleaseRequest,
    StructuredLabResultCreate,
    StructuredLabResultValueInput,
)
from app.services.billing_workflow_service import BillingWorkflowService
from app.services.lab_foundation_service import LabFoundationService
from app.services.lab_request_service import LabRequestService
from app.services.lab_safety_service import LabSafetyService
from app.shared.enums import (
    BillingReasonCode,
    Gender,
    LabCriticalAlertStatus,
    LabQcStatus,
    LabRequestWorkflowStatus,
    LabResultFieldType,
    LabResultLifecycleStatus,
    LabResultTemplateType,
    LabSpecimenStatus,
    LabVerificationPolicy,
    UserRole,
    VisitStatus,
)


def _seed_safety_context(
    db,
    clinic_id: uuid.UUID,
    *,
    verification_policy: LabVerificationPolicy,
    allows_scientist_verification: bool = False,
    scientist_verification_restricted: bool = False,
):
    code_suffix = clinic_id.hex[:8].upper()
    clinic = Clinic(
        id=clinic_id,
        name="Lab Safety Clinic",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    unit = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Chemical Pathology",
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
        code=f"HB_TEMPLATE_{code_suffix}",
        name=f"Hemoglobin Template {code_suffix}",
        result_type=LabResultTemplateType.PANEL,
        version=1,
        is_active=True,
    )
    db.add(template)
    db.commit()

    field = LabResultTemplateField(
        id=uuid.uuid4(),
        template_id=template.id,
        field_code="HEMOGLOBIN",
        field_name="Hemoglobin",
        field_type=LabResultFieldType.NUMBER,
        display_order=1,
        is_required=True,
        unit="g/dL",
        reference_range_text="12 - 16 g/dL",
        reference_min=12,
        reference_max=16,
        critical_rules_json={
            "critical_low": 6,
            "severity": "CRITICAL",
            "message": "Critical hemoglobin detected",
        },
    )
    db.add(field)
    db.commit()

    catalog = LabTestCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        test_code="LAB_HEMOGLOBIN",
        test_name="Hemoglobin",
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
        price_minor=300000,
        currency="NGN",
        turnaround_time_minutes=45,
        display_order=1,
        is_enabled=True,
        billing_name="Hemoglobin",
        verification_policy=verification_policy,
        allows_scientist_verification=allows_scientist_verification,
        scientist_verification_restricted=scientist_verification_restricted,
        critical_rules_json=None,
    )
    db.add(config)
    db.commit()

    charge = ChargeCatalog(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        code="LAB_HEMOGLOBIN",
        name="Hemoglobin",
        category="LAB",
        default_amount_minor=300000,
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
        full_name="Safety Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"cashier-{clinic_id}@example.test",
        password_hash="test",
        full_name="Safety Cashier",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    lab_tech = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-tech-{clinic_id}@example.test",
        password_hash="test",
        full_name="Safety Lab Tech",
        role=UserRole.LAB_TECH.value,
        is_active=True,
    )
    lab_scientist = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-scientist-{clinic_id}@example.test",
        password_hash="test",
        full_name="Safety Lab Scientist",
        role=UserRole.LAB_SCIENTIST.value,
        is_active=True,
    )
    lab_supervisor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-supervisor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Safety Lab Supervisor",
        role=UserRole.LAB_SUPERVISOR.value,
        is_active=True,
    )
    legacy_lab = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-legacy-{clinic_id}@example.test",
        password_hash="test",
        full_name="Safety Legacy Lab",
        role=UserRole.LAB.value,
        is_active=True,
    )
    db.add_all([doctor, cashier, lab_tech, lab_scientist, lab_supervisor, legacy_lab])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Safety Patient",
        date_of_birth=date(1988, 6, 1),
        gender=Gender.MALE,
        phone_number="08000000055",
        address="Test Address",
        occupation="Teacher",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.LAB_REQUESTED,
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
        "lab_tech": lab_tech,
        "lab_scientist": lab_scientist,
        "lab_supervisor": lab_supervisor,
        "legacy_lab": legacy_lab,
        "patient": patient,
        "visit": visit,
    }


def _create_paid_request_with_received_specimen(db, ctx):
    lab_request = LabRequestService(db).create_request(
        visit=ctx["visit"],
        test_name="Hemoglobin",
        test_code="LAB_HEMOGLOBIN",
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
    LabFoundationService(db).create_specimen(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=LabSpecimenCreate(
            specimen_type="Blood",
            specimen_source="blood",
            status=LabSpecimenStatus.RECEIVED,
        ),
    )
    db.refresh(lab_request)
    return lab_request


def test_structured_result_marks_abnormal_without_alert_when_not_critical(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_ABNORMAL,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)

    result = LabSafetyService(db).submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=8.0,
                )
            ]
        ),
    )

    stored_value_rows = (
        db.query(LabResultValue)
        .filter(LabResultValue.result_id == result.id)
        .all()
    )
    assert stored_value_rows
    db.refresh(lab_request)
    assert lab_request.workflow_status == LabRequestWorkflowStatus.RESULT_ENTERED
    assert result.status == LabResultLifecycleStatus.SUBMITTED

    stored_values = result._value_rows
    assert len(stored_values) == 1
    assert stored_values[0].abnormal_flag is True
    assert stored_values[0].critical_flag is False

    alerts = LabSafetyService(db).list_result_alerts(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
    )
    assert alerts == []


def test_critical_result_creates_alert_and_requires_verification_before_release(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_IF_CRITICAL,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)
    service = LabSafetyService(db)

    result = service.submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=5.5,
                )
            ]
        ),
    )

    alerts = service.list_result_alerts(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
    )
    assert len(alerts) == 1
    assert alerts[0].status == LabCriticalAlertStatus.CREATED
    assert alerts[0].target_role == "DOCTOR"
    assert alerts[0].target_user_id == ctx["doctor"].id

    with pytest.raises(HTTPException) as exc:
        service.release_result(
            result_id=result.id,
            clinic_id=ctx["clinic"].id,
            actor_id=ctx["lab_supervisor"].id,
        )

    assert exc.value.status_code == 409
    assert "supervisor verification" in exc.value.detail

    verified = service.verify_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
    )
    assert verified.status == LabResultLifecycleStatus.VERIFIED

    released = service.release_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
    )
    assert released.status == LabResultLifecycleStatus.RELEASED

    alerts = service.list_result_alerts(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
    )
    assert alerts[0].status == LabCriticalAlertStatus.DELIVERED


def test_qc_failure_creates_scoped_alert_and_marks_run_failed(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.OPTIONAL,
    )
    service = LabSafetyService(db)

    qc_run = service.create_qc_run(
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
        payload=LabQcRunCreate(
            unit_id=ctx["unit"].id,
            machine_id=uuid.uuid4(),
            qc_level="NORMAL",
            notes="Morning QC run",
        ),
    )

    qc_result = service.record_qc_result(
        qc_run_id=qc_run.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
        payload=LabQcResultCreate(
            analyte_name="Hemoglobin",
            expected_min=12.0,
            expected_max=16.0,
            observed_value=18.2,
        ),
    )

    assert qc_result.status == LabQcStatus.FAIL
    db.refresh(qc_run)
    assert qc_run.status == LabQcStatus.FAIL
    alerts = db.query(LabCriticalAlert).filter(LabCriticalAlert.unit_id == ctx["unit"].id).all()
    assert len(alerts) == 1


def test_technician_cannot_verify_or_release_results(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)
    service = LabSafetyService(db)
    result = service.submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=10.5,
                )
            ]
        ),
    )

    with pytest.raises(HTTPException) as verify_exc:
        service.verify_result(
            result_id=result.id,
            clinic_id=ctx["clinic"].id,
            actor_id=ctx["lab_tech"].id,
        )
    assert verify_exc.value.status_code == 403

    with pytest.raises(HTTPException) as release_exc:
        service.release_result(
            result_id=result.id,
            clinic_id=ctx["clinic"].id,
            actor_id=ctx["lab_tech"].id,
        )
    assert release_exc.value.status_code == 403


def test_scientist_verification_requires_explicit_policy_and_separation(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
        allows_scientist_verification=True,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)
    service = LabSafetyService(db)
    result = service.submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=11.1,
                )
            ]
        ),
    )

    verified = service.verify_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
    )
    assert verified.status == LabResultLifecycleStatus.VERIFIED

    ctx_self = _seed_safety_context(
        db,
        uuid.uuid4(),
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
        allows_scientist_verification=True,
    )
    self_entered_request = _create_paid_request_with_received_specimen(db, ctx_self)
    self_entered_result = service.submit_structured_result(
        lab_request=self_entered_request,
        actor_id=ctx_self["lab_scientist"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx_self["field"].id,
                    value_number=11.4,
                )
            ]
        ),
    )
    with pytest.raises(HTTPException) as separation_exc:
        service.verify_result(
            result_id=self_entered_result.id,
            clinic_id=self_entered_result.clinic_id,
            actor_id=ctx_self["lab_scientist"].id,
        )
    assert separation_exc.value.status_code == 409


def test_qc_failure_blocks_release_until_supervisor_override(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)
    service = LabSafetyService(db)
    result = service.submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=10.2,
                )
            ]
        ),
    )
    service.verify_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
    )
    qc_run = service.create_qc_run(
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
        payload=LabQcRunCreate(
            unit_id=ctx["unit"].id,
            machine_id=uuid.uuid4(),
            qc_level="NORMAL",
        ),
    )
    service.record_qc_result(
        qc_run_id=qc_run.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_scientist"].id,
        payload=LabQcResultCreate(
            analyte_name="Hemoglobin",
            expected_min=12.0,
            expected_max=16.0,
            observed_value=18.2,
        ),
    )

    with pytest.raises(HTTPException) as qc_exc:
        service.release_result(
            result_id=result.id,
            clinic_id=ctx["clinic"].id,
            actor_id=ctx["lab_supervisor"].id,
        )
    assert qc_exc.value.status_code == 409
    assert "QC failure blocks release" in qc_exc.value.detail

    released = service.release_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
        payload=LabResultReleaseRequest(
            qc_override_reason="Supervisor reviewed analyzer drift and approved release"
        ),
    )
    assert released.status == LabResultLifecycleStatus.RELEASED
    override_events = (
        db.query(EventLog)
        .filter(EventLog.event_type == "LAB_QC_OVERRIDE")
        .all()
    )
    assert override_events


def test_supervisor_amendment_creates_new_version_with_reason(db, clinic_id):
    ctx = _seed_safety_context(
        db,
        clinic_id,
        verification_policy=LabVerificationPolicy.REQUIRED_BEFORE_RELEASE,
    )
    lab_request = _create_paid_request_with_received_specimen(db, ctx)
    service = LabSafetyService(db)
    result = service.submit_structured_result(
        lab_request=lab_request,
        actor_id=ctx["lab_tech"].id,
        payload=StructuredLabResultCreate(
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=9.5,
                )
            ]
        ),
    )
    service.verify_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
    )
    released = service.release_result(
        result_id=result.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
    )

    amended = service.amend_result(
        result_id=released.id,
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["lab_supervisor"].id,
        payload=LabResultAmendCreate(
            amendment_reason="Corrected decimal placement after bench review",
            values=[
                StructuredLabResultValueInput(
                    template_field_id=ctx["field"].id,
                    value_number=12.5,
                )
            ],
        ),
    )

    assert amended.status == LabResultLifecycleStatus.RELEASED
    assert amended.amended_from_result_id == released.id
    assert amended.amendment_reason == "Corrected decimal placement after bench review"
    db.refresh(released)
    assert released.record_status.value == "AMENDED"
