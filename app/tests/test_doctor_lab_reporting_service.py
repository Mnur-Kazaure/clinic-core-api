import uuid
from datetime import date, datetime, timedelta, timezone

from app.models.clinic import Clinic
from app.models.lab_critical_alert import LabCriticalAlert
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.models.lab_result_template import LabResultTemplate
from app.models.lab_result_template_field import LabResultTemplateField
from app.models.lab_result_value import LabResultValue
from app.models.lab_specimen import LabSpecimen
from app.models.patient import Patient
from app.models.patient_mrn import PatientMRN
from app.models.service_line import ServiceLine
from app.models.user import User
from app.models.visit import Visit
from app.services.doctor_lab_reporting_service import DoctorLabReportingService
from app.shared.enums import (
    Gender,
    LabCriticalAlertSeverity,
    LabCriticalAlertStatus,
    LabCriticalAlertType,
    LabResultFieldType,
    LabResultLifecycleStatus,
    LabResultTemplateType,
    LabSpecimenStatus,
    MRNStatus,
    UserRole,
    VisitStatus,
)


def _seed_reporting_context(db, clinic_id: uuid.UUID):
    clinic = Clinic(
        id=clinic_id,
        name="Reporting Clinic",
        billing_currency="NGN",
    )
    db.add(clinic)
    db.commit()

    doctor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"doctor-{clinic_id}@example.test",
        password_hash="test",
        full_name="Reporting Doctor",
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    lab_user = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"lab-{clinic_id}@example.test",
        password_hash="test",
        full_name="Reporting Lab User",
        role=UserRole.LAB.value,
        is_active=True,
    )
    supervisor = User(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        email=f"sup-{clinic_id}@example.test",
        password_hash="test",
        full_name="Reporting Supervisor",
        role=UserRole.LAB.value,
        is_active=True,
    )
    db.add_all([doctor, lab_user, supervisor])
    db.commit()

    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Musa Abdullahi",
        date_of_birth=date(1986, 5, 4),
        gender=Gender.MALE,
        phone_number="08030000000",
        address="Kazaure",
        occupation="Teacher",
    )
    db.add(patient)
    db.commit()

    mrn = PatientMRN(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        mrn="MRN-00412",
        status=MRNStatus.ACTIVE,
        issued_at=datetime.now(timezone.utc),
        issued_by=doctor.id,
        check_digit="7",
    )
    db.add(mrn)
    db.commit()

    unit = ServiceLine(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        name="Haematology",
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
        code="FBC_TEMPLATE",
        name="Full Blood Count",
        result_type=LabResultTemplateType.PANEL,
        version=1,
        is_active=True,
    )
    db.add(template)
    db.commit()

    field_hb = LabResultTemplateField(
        id=uuid.uuid4(),
        template_id=template.id,
        field_code="HB",
        field_name="Hemoglobin",
        field_type=LabResultFieldType.NUMBER,
        display_order=1,
        is_required=True,
        unit="g/dL",
        reference_range_text="12 - 16 g/dL",
        reference_min=12,
        reference_max=16,
        reference_unit="g/dL",
    )
    field_platelet = LabResultTemplateField(
        id=uuid.uuid4(),
        template_id=template.id,
        field_code="PLT",
        field_name="Platelets",
        field_type=LabResultFieldType.NUMBER,
        display_order=2,
        is_required=True,
        unit="x10^9/L",
        reference_range_text="150 - 450 x10^9/L",
        reference_min=150,
        reference_max=450,
        reference_unit="x10^9/L",
    )
    db.add_all([field_hb, field_platelet])
    db.commit()

    visit_one = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc) - timedelta(days=2),
        version=1,
    )
    visit_two = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor.id,
        status=VisitStatus.IN_CONSULTATION,
        started_at=datetime.now(timezone.utc) - timedelta(days=30),
        version=1,
    )
    db.add_all([visit_one, visit_two])
    db.commit()

    return {
        "clinic": clinic,
        "doctor": doctor,
        "lab_user": lab_user,
        "supervisor": supervisor,
        "patient": patient,
        "unit": unit,
        "template": template,
        "field_hb": field_hb,
        "field_platelet": field_platelet,
        "visit_one": visit_one,
        "visit_two": visit_two,
    }


def _build_released_result(
    *,
    db,
    clinic_id,
    request_id,
    template_id,
    technician_id,
    released_by,
    entered_at,
    released_at,
    amended_from_result_id=None,
    result_value="summary",
):
    result = LabResult(
        id=uuid.uuid4(),
        lab_request_id=request_id,
        request_item_id=request_id,
        clinic_id=clinic_id,
        technician_id=technician_id,
        template_id=template_id,
        template_version=1,
        status=LabResultLifecycleStatus.RELEASED,
        entered_by=technician_id,
        entered_at=entered_at,
        verified_by=released_by,
        verified_at=released_at - timedelta(minutes=5),
        released_by=released_by,
        released_at=released_at,
        amended_from_result_id=amended_from_result_id,
        result_value=result_value,
        result_unit=None,
        reference_range=None,
    )
    db.add(result)
    db.commit()
    return result


def test_visit_results_return_latest_active_released_result_only(db, clinic_id):
    ctx = _seed_reporting_context(db, clinic_id)

    request = LabRequest(
        id=uuid.uuid4(),
        visit_id=ctx["visit_one"].id,
        clinic_id=clinic_id,
        requested_by=ctx["doctor"].id,
        test_name="Full Blood Count",
        test_code="LAB_FBC",
        target_unit_id=ctx["unit"].id,
    )
    db.add(request)
    db.commit()

    original = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=3),
        released_at=datetime.now(timezone.utc) - timedelta(hours=2),
        result_value="Original FBC",
    )
    amended = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
        released_at=datetime.now(timezone.utc) - timedelta(minutes=45),
        amended_from_result_id=original.id,
        result_value="Amended FBC",
    )

    db.add_all(
        [
            LabResultValue(
                result_id=amended.id,
                template_field_id=ctx["field_hb"].id,
                value_number=8.0,
                abnormal_flag=True,
                critical_flag=False,
            ),
            LabResultValue(
                result_id=amended.id,
                template_field_id=ctx["field_platelet"].id,
                value_number=18,
                abnormal_flag=True,
                critical_flag=True,
            ),
            LabSpecimen(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                accession_number="LAB-20260313-00042",
                request_item_id=request.id,
                target_unit_id=ctx["unit"].id,
                specimen_type="Blood",
                specimen_source="blood",
                specimen_sequence=1,
                status=LabSpecimenStatus.RECEIVED,
            ),
            LabCriticalAlert(
                id=uuid.uuid4(),
                result_id=amended.id,
                result_value_id=None,
                request_item_id=request.id,
                visit_id=ctx["visit_one"].id,
                patient_id=ctx["patient"].id,
                unit_id=ctx["unit"].id,
                alert_type=LabCriticalAlertType.CRITICAL_RESULT,
                severity=LabCriticalAlertSeverity.CRITICAL,
                message="Critical platelet count",
                target_role="DOCTOR",
                status=LabCriticalAlertStatus.DELIVERED,
            ),
        ]
    )
    db.commit()

    summaries = DoctorLabReportingService(db).list_visit_results(visit=ctx["visit_one"])

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.result_id == amended.id
    assert summary.is_amended is True
    assert summary.is_superseded is False
    assert summary.has_abnormal is True
    assert summary.has_critical is True
    assert summary.critical_alert_count == 1
    assert summary.accession_numbers == ["LAB-20260313-00042"]


def test_result_detail_includes_specimen_alerts_and_prior_versions(db, clinic_id):
    ctx = _seed_reporting_context(db, clinic_id)

    request = LabRequest(
        id=uuid.uuid4(),
        visit_id=ctx["visit_one"].id,
        clinic_id=clinic_id,
        requested_by=ctx["doctor"].id,
        test_name="Full Blood Count",
        test_code="LAB_FBC",
        target_unit_id=ctx["unit"].id,
    )
    db.add(request)
    db.commit()

    original = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=4),
        released_at=datetime.now(timezone.utc) - timedelta(hours=3),
        result_value="Original FBC",
    )
    amended = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=2),
        released_at=datetime.now(timezone.utc) - timedelta(hours=1),
        amended_from_result_id=original.id,
        result_value="Amended FBC",
    )
    db.add_all(
        [
            LabResultValue(
                result_id=amended.id,
                template_field_id=ctx["field_hb"].id,
                value_number=8.0,
                abnormal_flag=True,
                critical_flag=False,
            ),
            LabResultValue(
                result_id=amended.id,
                template_field_id=ctx["field_platelet"].id,
                value_number=18,
                abnormal_flag=True,
                critical_flag=True,
            ),
            LabSpecimen(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                accession_number="LAB-20260313-00099",
                request_item_id=request.id,
                target_unit_id=ctx["unit"].id,
                specimen_type="Blood",
                specimen_source="blood",
                container_type="EDTA tube",
                collection_site="venous",
                specimen_sequence=1,
                status=LabSpecimenStatus.RECEIVED,
                collected_at=datetime.now(timezone.utc) - timedelta(hours=3),
                received_at=datetime.now(timezone.utc) - timedelta(hours=2, minutes=50),
            ),
            LabCriticalAlert(
                id=uuid.uuid4(),
                result_id=amended.id,
                result_value_id=None,
                request_item_id=request.id,
                visit_id=ctx["visit_one"].id,
                patient_id=ctx["patient"].id,
                unit_id=ctx["unit"].id,
                alert_type=LabCriticalAlertType.CRITICAL_RESULT,
                severity=LabCriticalAlertSeverity.CRITICAL,
                message="Critical platelet count",
                target_role="DOCTOR",
                status=LabCriticalAlertStatus.DELIVERED,
            ),
        ]
    )
    db.commit()

    detail = DoctorLabReportingService(db).get_visit_result_detail(
        visit=ctx["visit_one"],
        result_id=amended.id,
    )

    assert detail.patient_name == "Musa Abdullahi"
    assert detail.patient_mrn == "MRN-00412"
    assert detail.unit_name == "Haematology"
    assert detail.has_critical is True
    assert "Critical" in detail.state_labels
    assert "Amended" in detail.state_labels
    assert len(detail.values) == 2
    assert detail.values[0].field_code == "HB"
    assert len(detail.specimens) == 1
    assert detail.specimens[0].accession_number == "LAB-20260313-00099"
    assert len(detail.alerts) == 1
    assert detail.alerts[0].message == "Critical platelet count"
    assert len(detail.prior_versions) == 1
    assert detail.prior_versions[0].result_id == original.id
    assert detail.prior_versions[0].is_superseded is True


def test_patient_history_is_longitudinal_and_filtered_by_test_identifier(db, clinic_id):
    ctx = _seed_reporting_context(db, clinic_id)

    request_recent = LabRequest(
        id=uuid.uuid4(),
        visit_id=ctx["visit_one"].id,
        clinic_id=clinic_id,
        requested_by=ctx["doctor"].id,
        test_name="Full Blood Count",
        test_code="LAB_FBC",
        target_unit_id=ctx["unit"].id,
    )
    request_old = LabRequest(
        id=uuid.uuid4(),
        visit_id=ctx["visit_two"].id,
        clinic_id=clinic_id,
        requested_by=ctx["doctor"].id,
        test_name="Full Blood Count",
        test_code="LAB_FBC",
        target_unit_id=ctx["unit"].id,
    )
    request_other = LabRequest(
        id=uuid.uuid4(),
        visit_id=ctx["visit_two"].id,
        clinic_id=clinic_id,
        requested_by=ctx["doctor"].id,
        test_name="Malaria Parasite",
        test_code="LAB_MALARIA",
        target_unit_id=ctx["unit"].id,
    )
    db.add_all([request_recent, request_old, request_other])
    db.commit()

    recent_result = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request_recent.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=2),
        released_at=datetime.now(timezone.utc) - timedelta(hours=1),
        result_value="Recent",
    )
    old_result = _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request_old.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(days=20),
        released_at=datetime.now(timezone.utc) - timedelta(days=20, minutes=-10),
        result_value="Old",
    )
    _build_released_result(
        db=db,
        clinic_id=clinic_id,
        request_id=request_other.id,
        template_id=ctx["template"].id,
        technician_id=ctx["lab_user"].id,
        released_by=ctx["supervisor"].id,
        entered_at=datetime.now(timezone.utc) - timedelta(days=5),
        released_at=datetime.now(timezone.utc) - timedelta(days=5, minutes=-5),
        result_value="Other",
    )

    db.add_all(
        [
            LabResultValue(
                result_id=recent_result.id,
                template_field_id=ctx["field_hb"].id,
                value_number=8.0,
                abnormal_flag=True,
                critical_flag=False,
            ),
            LabResultValue(
                result_id=old_result.id,
                template_field_id=ctx["field_hb"].id,
                value_number=11.2,
                abnormal_flag=True,
                critical_flag=False,
            ),
            LabSpecimen(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                accession_number="LAB-20260313-00120",
                request_item_id=request_recent.id,
                target_unit_id=ctx["unit"].id,
                specimen_type="Blood",
                specimen_source="blood",
                specimen_sequence=1,
                status=LabSpecimenStatus.RECEIVED,
            ),
            LabSpecimen(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                accession_number="LAB-20260211-00011",
                request_item_id=request_old.id,
                target_unit_id=ctx["unit"].id,
                specimen_type="Blood",
                specimen_source="blood",
                specimen_sequence=1,
                status=LabSpecimenStatus.RECEIVED,
            ),
        ]
    )
    db.commit()

    history = DoctorLabReportingService(db).list_patient_history(
        patient_id=ctx["patient"].id,
        clinic_id=clinic_id,
        test_identifier="LAB_FBC",
    )

    assert len(history) == 2
    assert history[0].result_id == recent_result.id
    assert history[1].result_id == old_result.id
    assert history[0].accession_numbers == ["LAB-20260313-00120"]
    assert history[1].accession_numbers == ["LAB-20260211-00011"]
