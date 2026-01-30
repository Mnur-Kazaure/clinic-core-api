import pytest
import uuid
from datetime import date, datetime
from sqlalchemy import text

from app.models.patient import Patient
from app.models.visit import Visit
from app.models.consultation import Consultation
from app.models.prescription import Prescription
from app.models.lab_request import LabRequest
from app.models.lab_result import LabResult
from app.shared.enums import (
    VisitStatus,
    PrescriptionStatus,
    RecordStatus,
    Gender,
    LabRequestStatus,
)


def _create_sqlite_triggers(db):
    trigger_tables = {
        "consultations": "record_status",
        "prescriptions": "record_status",
        "lab_results": "record_status",
    }
    for table, status_column in trigger_tables.items():
        if table == "consultations":
            immutable_checks = """
                NEW.visit_id != OLD.visit_id OR
                NEW.clinic_id != OLD.clinic_id OR
                NEW.doctor_id != OLD.doctor_id OR
                NEW.started_at != OLD.started_at OR
                NEW.completed_at != OLD.completed_at OR
                NEW.vitals != OLD.vitals OR
                NEW.presenting_complaints != OLD.presenting_complaints OR
                NEW.diagnosis != OLD.diagnosis OR
                NEW.notes != OLD.notes OR
                NEW.doctor_full_name != OLD.doctor_full_name OR
                NEW.signed_at != OLD.signed_at
            """
            void_checks = "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR " + immutable_checks
        elif table == "prescriptions":
            immutable_checks = """
                NEW.consultation_id != OLD.consultation_id OR
                NEW.visit_id != OLD.visit_id OR
                NEW.clinic_id != OLD.clinic_id OR
                NEW.prescribed_by != OLD.prescribed_by OR
                NEW.dispensed_by != OLD.dispensed_by OR
                NEW.drug_name != OLD.drug_name OR
                NEW.dosage != OLD.dosage OR
                NEW.frequency != OLD.frequency OR
                NEW.duration != OLD.duration OR
                NEW.instructions != OLD.instructions OR
                NEW.issued_at != OLD.issued_at OR
                NEW.dispensed_at != OLD.dispensed_at OR
                NEW.signed_at != OLD.signed_at
            """
            void_checks = (
                "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR "
                "NEW.status != 'CANCELLED' OR NEW.cancelled_at IS NULL OR " + immutable_checks
            )
        else:
            immutable_checks = """
                NEW.lab_request_id != OLD.lab_request_id OR
                NEW.clinic_id != OLD.clinic_id OR
                NEW.technician_id != OLD.technician_id OR
                NEW.result_value != OLD.result_value OR
                NEW.result_unit != OLD.result_unit OR
                NEW.reference_range != OLD.reference_range OR
                NEW.created_at != OLD.created_at OR
                NEW.signed_at != OLD.signed_at
            """
            void_checks = "NEW.record_status != 'VOIDED' OR NEW.void_reason IS NULL OR " + immutable_checks
        db.execute(
            text(
                f"""
                CREATE TRIGGER IF NOT EXISTS {table}_block_update_signed
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                WHEN OLD.{status_column} = 'VOIDED'
                     OR (OLD.{status_column} = 'SIGNED' AND ({void_checks}))
                BEGIN
                    SELECT RAISE(ABORT, 'signed record immutable');
                END;
                """
            )
        )
        db.execute(
            text(
                f"""
                CREATE TRIGGER IF NOT EXISTS {table}_block_delete_signed
                BEFORE DELETE ON {table}
                FOR EACH ROW
                WHEN OLD.{status_column} = 'SIGNED'
                BEGIN
                    SELECT RAISE(ABORT, 'signed record immutable');
                END;
                """
            )
        )
    db.commit()


def _seed_visit(db, clinic_id, doctor_id):
    patient = Patient(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        full_name="Test Patient",
        date_of_birth=date(2000, 1, 1),
        gender=Gender.MALE,
        phone_number="000",
        address="Test",
        occupation="Test",
    )
    db.add(patient)
    db.commit()

    visit = Visit(
        id=uuid.uuid4(),
        clinic_id=clinic_id,
        patient_id=patient.id,
        assigned_doctor_id=doctor_id,
        status=VisitStatus.IN_CONSULTATION,
    )
    db.add(visit)
    db.commit()
    return patient, visit


def test_signed_consultation_update_hard_fails(db, doctor, clinic_id):
    _create_sqlite_triggers(db)
    patient, visit = _seed_visit(db, clinic_id, doctor.id)

    consultation = Consultation(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        doctor_id=doctor.id,
        started_at=datetime(2026, 1, 1, 0, 0, 0),
        completed_at=datetime(2026, 1, 1, 1, 0, 0),
        record_status=RecordStatus.SIGNED,
        signed_at=datetime(2026, 1, 1, 1, 0, 0),
        notes="Initial",
    )
    db.add(consultation)
    db.commit()

    consultation.notes = "Modified"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()

    consultation.record_status = RecordStatus.VOIDED
    consultation.void_reason = "Clinical error"
    db.commit()

    consultation.notes = "Should fail"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_signed_prescription_update_hard_fails(db, doctor, clinic_id):
    _create_sqlite_triggers(db)
    patient, visit = _seed_visit(db, clinic_id, doctor.id)

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        prescribed_by=doctor.id,
        drug_name="Drug",
        dosage="10mg",
        frequency="1x",
        duration="5d",
        status=PrescriptionStatus.ISSUED,
        record_status=RecordStatus.SIGNED,
        signed_at=datetime(2026, 1, 1, 1, 0, 0),
        issued_at=datetime(2026, 1, 1, 1, 0, 0),
    )
    db.add(prescription)
    db.commit()

    prescription.duration = "7d"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_signed_lab_result_update_hard_fails(db, doctor, clinic_id):
    _create_sqlite_triggers(db)
    patient, visit = _seed_visit(db, clinic_id, doctor.id)

    lab_request = LabRequest(
        id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        requested_by=doctor.id,
        test_name="CBC",
        status=LabRequestStatus.PENDING,
    )
    db.add(lab_request)
    db.commit()

    lab_result = LabResult(
        id=uuid.uuid4(),
        lab_request_id=lab_request.id,
        clinic_id=clinic_id,
        technician_id=doctor.id,
        result_value="Normal",
        record_status=RecordStatus.SIGNED,
        signed_at=datetime(2026, 1, 1, 1, 0, 0),
    )
    db.add(lab_result)
    db.commit()

    lab_result.result_value = "Updated"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()

    lab_result.record_status = RecordStatus.VOIDED
    lab_result.void_reason = "Incorrect sample"
    db.commit()

    lab_result.result_value = "Change after void"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_signed_prescription_void_allowed_with_reason(db, doctor, clinic_id):
    _create_sqlite_triggers(db)
    _, visit = _seed_visit(db, clinic_id, doctor.id)

    prescription = Prescription(
        id=uuid.uuid4(),
        consultation_id=uuid.uuid4(),
        visit_id=visit.id,
        clinic_id=clinic_id,
        prescribed_by=doctor.id,
        drug_name="Drug",
        dosage="10mg",
        frequency="1x",
        duration="5d",
        status=PrescriptionStatus.ISSUED,
        record_status=RecordStatus.SIGNED,
        signed_at=datetime(2026, 1, 1, 1, 0, 0),
        issued_at=datetime(2026, 1, 1, 1, 0, 0),
    )
    db.add(prescription)
    db.commit()

    prescription.record_status = RecordStatus.VOIDED
    prescription.void_reason = "Duplicate order"
    prescription.status = PrescriptionStatus.CANCELLED
    prescription.cancelled_at = datetime(2026, 1, 2, 1, 0, 0)
    db.commit()

    prescription.drug_name = "Should fail"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
