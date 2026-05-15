import uuid
from datetime import date, datetime, timezone

from app.models.billing_item import BillingItem
from app.models.clinic import Clinic
from app.models.event_log import EventLog
from app.models.lab_qc_result import LabQcResult
from app.models.lab_qc_run import LabQcRun
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.lab_staff_assignment_profile import LabStaffAssignmentProfile
from app.models.lab_user_unit_access import LabUserUnitAccess
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.lab_manager_governance_service import LabManagerGovernanceService
from app.shared.enums import (
    BillingItemStatus,
    BillingReasonCode,
    Gender,
    LabConfigurationRequestType,
    LabQcStatus,
    LabRequestStatus,
    LabRequestWorkflowStatus,
    LabResultLifecycleStatus,
    LabSpecimenStatus,
    LabStaffAssignmentStatus,
    ServiceLineKind,
    UserRole,
    VisitStatus,
    MRNStatus,
)


def _seed_manager_context(db):
    clinic = Clinic(
        id=uuid.uuid4(),
        name="Specialist Hospital Kazaure",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    lab_root = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Medical Laboratory",
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    haematology = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Haematology",
        parent_id=lab_root.id,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    microbiology = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        name="Microbiology",
        parent_id=lab_root.id,
        service_line_kind=ServiceLineKind.LAB_UNIT,
        is_active=True,
    )
    db.add_all([lab_root, haematology, microbiology])
    db.commit()

    manager = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="lab.manager@example.test",
        password_hash="hashed",
        full_name="Lab HOD",
        role=UserRole.LAB_MANAGER.value,
        is_active=True,
    )
    tech = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="lab.tech@example.test",
        password_hash="hashed",
        full_name="Lab Tech One",
        role=UserRole.LAB_TECH.value,
        is_active=True,
        default_lab_unit_id=haematology.id,
    )
    supervisor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="lab.supervisor@example.test",
        password_hash="hashed",
        full_name="Lab Supervisor",
        role=UserRole.LAB_SUPERVISOR.value,
        is_active=True,
        default_lab_unit_id=haematology.id,
    )
    cashier = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="cashier@example.test",
        password_hash="hashed",
        full_name="Lab Cashier",
        role=UserRole.CASHIER.value,
        is_active=True,
    )
    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        email="doctor@example.test",
        password_hash="hashed",
        full_name="Ordering Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    db.add_all([manager, tech, supervisor, cashier, doctor])
    db.commit()

    db.add_all(
        [
            LabUserUnitAccess(user_id=tech.id, service_line_id=haematology.id),
            LabUserUnitAccess(user_id=supervisor.id, service_line_id=haematology.id),
            LabStaffAssignmentProfile(
                clinic_id=clinic.id,
                user_id=tech.id,
                assignment_status=LabStaffAssignmentStatus.ACTIVE,
                updated_by=manager.id,
            ),
        ]
    )
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        full_name="Musa Abdullahi",
        date_of_birth=date(1990, 1, 1),
        gender=Gender.MALE,
        phone_number="08000000000",
        address="Kazaure",
        occupation="Trader",
    )
    db.add(patient)
    db.commit()

    db.add(
        PatientMRN(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            mrn="MRN-00412",
            status=MRNStatus.ACTIVE,
            issued_at=datetime.now(timezone.utc),
            issued_by=manager.id,
            check_digit="1",
        )
    )
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        service_line_id=haematology.id,
        status=VisitStatus.LAB_REQUESTED,
        started_at=datetime.now(timezone.utc),
        version=1,
    )
    db.add(visit)
    db.commit()

    billing_item = BillingItem(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        visit_id=visit.id,
        charge_code="HEM_FBC",
        item_name="Full Blood Count",
        service_type="LAB_TEST",
        quantity=1,
        unit_price_minor=200000,
        total_minor=200000,
        amount_paid_minor=200000,
        currency="NGN",
        status=BillingItemStatus.PAID,
        created_by=doctor.id,
    )
    db.add(billing_item)
    db.commit()

    lab_request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        billing_item_id=billing_item.id,
        clinic_id=clinic.id,
        requested_by=doctor.id,
        test_name="Full Blood Count",
        test_code="HEM_FBC",
        target_unit_id=haematology.id,
        workflow_status=LabRequestWorkflowStatus.RESULT_ENTERED,
        status=LabRequestStatus.PENDING,
    )
    db.add(lab_request)
    db.commit()

    lab_result = LabResult(
        id=uuid.uuid4(),
        lab_request_id=lab_request.id,
        request_item_id=lab_request.id,
        clinic_id=clinic.id,
        technician_id=tech.id,
        entered_by=tech.id,
        status=LabResultLifecycleStatus.SUBMITTED,
        result_value="Panel",
        entered_at=datetime.now(timezone.utc),
    )
    db.add(lab_result)
    db.commit()

    db.add(
        LabResultValue(
            id=uuid.uuid4(),
            result_id=lab_result.id,
            template_field_id=uuid.uuid4(),
            value_number=5.5,
            abnormal_flag=True,
            critical_flag=False,
        )
    )
    db.commit()

    specimen = LabSpecimen(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        accession_number="LAB-20260319-00001",
        request_item_id=lab_request.id,
        target_unit_id=haematology.id,
        specimen_type="Blood",
        specimen_source="Blood",
        specimen_sequence=1,
        status=LabSpecimenStatus.REJECTED,
        rejection_reason_text="Clotted sample",
        rejected_by=tech.id,
        rejected_at=datetime.now(timezone.utc),
    )
    db.add(specimen)
    db.commit()

    qc_run = LabQcRun(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        unit_id=haematology.id,
        machine_id=None,
        qc_level="Normal",
        performed_by=supervisor.id,
        performed_at=datetime.now(timezone.utc),
        status=LabQcStatus.FAIL,
    )
    db.add(qc_run)
    db.commit()

    db.add(
        LabQcResult(
            id=uuid.uuid4(),
            qc_run_id=qc_run.id,
            analyte_name="Hemoglobin",
            expected_min=12,
            expected_max=16,
            observed_value=18,
            status=LabQcStatus.FAIL,
        )
    )
    db.commit()

    receipt = PaymentReceipt(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        patient_id=patient.id,
        visit_id=visit.id,
        receipt_number="SHK-2026-00001",
        total_amount_minor=200000,
        currency="NGN",
        payment_method=BillingReasonCode.CASH,
        collected_by=cashier.id,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(receipt)
    db.commit()

    db.add(
        PaymentReceiptItem(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            receipt_id=receipt.id,
            billing_item_id=billing_item.id,
            amount_minor=200000,
        )
    )
    db.commit()

    return {
        "clinic": clinic,
        "manager": manager,
        "tech": tech,
        "supervisor": supervisor,
        "cashier": cashier,
        "doctor": doctor,
        "haematology": haematology,
        "microbiology": microbiology,
        "patient": patient,
        "visit": visit,
        "lab_request": lab_request,
        "lab_result": lab_result,
        "specimen": specimen,
        "receipt": receipt,
    }


def test_lab_manager_dashboard_returns_governance_sections(db):
    ctx = _seed_manager_context(db)
    service = LabManagerGovernanceService(db)
    service.create_configuration_request(
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["manager"].id,
        payload=type(
            "Payload",
            (),
            {
                "request_type": LabConfigurationRequestType.NEW_STAFF_ACCOUNT,
                "justification": "Need a night-shift microbiology scientist.",
                "linked_staff_id": None,
                "linked_unit_id": ctx["microbiology"].id,
                "linked_test_code": None,
                "request_payload_json": {"requested_role": "LAB_SCIENTIST"},
            },
        )(),
    )

    dashboard = service.get_dashboard(clinic_id=ctx["clinic"].id)

    assert dashboard.overview.total_tests_today == 1
    assert dashboard.overview.active_staff_on_duty == 2
    assert dashboard.unit_operations[0].unit_name == "Haematology"
    assert dashboard.pending_verifications[0].test_name == "Full Blood Count"
    assert dashboard.specimen_issues[0].accession_number == "LAB-20260319-00001"
    assert dashboard.quality_control.fail_runs == 1
    assert dashboard.sales_revenue.receipt_count == 1
    assert dashboard.receipt_register.rows[0].cashier_name == "Lab Cashier"
    assert dashboard.configuration_requests[0].request_type == LabConfigurationRequestType.NEW_STAFF_ACCOUNT
    assert any(item.source_type == "CONFIGURATION_REQUEST" for item in dashboard.activity_audit)


def test_lab_manager_can_update_staff_assignment_scope(db):
    ctx = _seed_manager_context(db)
    service = LabManagerGovernanceService(db)

    response = service.update_staff_assignment(
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["manager"].id,
        staff_id=ctx["tech"].id,
        payload=type(
            "Payload",
            (),
            {
                "allowed_lab_unit_ids": [ctx["haematology"].id, ctx["microbiology"].id],
                "default_lab_unit_id": ctx["microbiology"].id,
                "assignment_status": LabStaffAssignmentStatus.TEMP_COVERAGE,
                "coverage_note": "Cover microbiology night shift this week",
                "model_fields_set": {
                    "allowed_lab_unit_ids",
                    "default_lab_unit_id",
                    "assignment_status",
                    "coverage_note",
                },
            },
        )(),
    )

    assert response.assignment_status == LabStaffAssignmentStatus.TEMP_COVERAGE
    assert response.default_unit_name == "Microbiology"
    assert sorted(unit.name for unit in response.allowed_units) == ["Haematology", "Microbiology"]

    audit_events = db.query(EventLog).filter(EventLog.event_type == "LAB_STAFF_ASSIGNMENT_UPDATED").all()
    assert len(audit_events) == 1


def test_lab_manager_configuration_request_is_audited(db):
    ctx = _seed_manager_context(db)
    service = LabManagerGovernanceService(db)

    response = service.create_configuration_request(
        clinic_id=ctx["clinic"].id,
        actor_id=ctx["manager"].id,
        payload=type(
            "Payload",
            (),
            {
                "request_type": LabConfigurationRequestType.PRICE_REVIEW,
                "justification": "Review U&E pricing against current reagent cost.",
                "linked_staff_id": None,
                "linked_unit_id": ctx["haematology"].id,
                "linked_test_code": "CHEM_UE",
                "request_payload_json": {"proposed_price_minor": 400000},
            },
        )(),
    )

    assert response.status.name == "PENDING"
    assert response.linked_unit_name == "Haematology"

    audit_events = db.query(EventLog).filter(EventLog.event_type == "LAB_CONFIGURATION_REQUEST_SUBMITTED").all()
    assert len(audit_events) == 1


def test_lab_manager_dashboard_uses_clinic_currency_when_sales_window_is_empty(db):
    ctx = _seed_manager_context(db)
    service = LabManagerGovernanceService(db)

    dashboard = service.get_dashboard(
        clinic_id=ctx["clinic"].id,
        start_date=date(2026, 3, 18),
        end_date=date(2026, 3, 18),
    )

    assert dashboard.sales_revenue.currency == "NGN"
    assert dashboard.sales_revenue.receipt_count == 0
