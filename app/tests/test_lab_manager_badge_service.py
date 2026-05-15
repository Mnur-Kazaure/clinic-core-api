import uuid
from datetime import datetime, timezone

from app.models.lab_qc_run import LabQcRun
from app.models.lab_specimen import LabSpecimen
from app.models.payment_receipt import PaymentReceipt
from app.models.payment_receipt_item import PaymentReceiptItem
from app.services.lab_manager_badge_service import LabManagerBadgeService
from app.shared.enums import (
    BillingReasonCode,
    GovernanceSectionKey,
    LabQcStatus,
    LabSpecimenStatus,
)
from app.tests.test_lab_manager_governance_service import _seed_manager_context


def _snapshot_map(snapshot):
    return {item.section_key.value: item for item in snapshot.sections}


def test_lab_manager_badge_snapshot_separates_live_and_checkpoint_sections(db):
    ctx = _seed_manager_context(db)
    service = LabManagerBadgeService(db)

    snapshot = service.get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )
    badge_map = _snapshot_map(snapshot)

    assert badge_map["PENDING_VERIFICATIONS"].count == 1
    assert badge_map["PENDING_VERIFICATIONS"].tone == "warning"
    assert badge_map["QUALITY_CONTROL"].count == 1
    assert badge_map["QUALITY_CONTROL"].tone == "critical"
    assert badge_map["CRITICAL_ALERTS"].count == 0
    assert badge_map["SALES_REVENUE"].count == 0
    assert badge_map["RECEIPT_REGISTER"].count == 0
    assert badge_map["SPECIMEN_ISSUES"].count == 0


def test_lab_manager_badge_checkpoint_counts_new_sales_and_receipts_only(db):
    ctx = _seed_manager_context(db)
    service = LabManagerBadgeService(db)

    service.mark_section_viewed(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
        section_key=GovernanceSectionKey.SALES_REVENUE,
    )
    service.mark_section_viewed(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
        section_key=GovernanceSectionKey.RECEIPT_REGISTER,
    )

    now = datetime.now(timezone.utc)
    receipt = PaymentReceipt(
        id=uuid.uuid4(),
        clinic_id=ctx["clinic"].id,
        patient_id=ctx["patient"].id,
        visit_id=ctx["visit"].id,
        receipt_number="SHK-2026-00002",
        total_amount_minor=200000,
        currency="NGN",
        payment_method=BillingReasonCode.TRANSFER,
        collected_by=ctx["cashier"].id,
        occurred_at=now,
    )
    db.add(receipt)
    db.flush()
    db.add(
        PaymentReceiptItem(
            id=uuid.uuid4(),
            clinic_id=ctx["clinic"].id,
            receipt_id=receipt.id,
            billing_item_id=ctx["lab_request"].billing_item_id,
            amount_minor=200000,
        )
    )
    db.commit()

    snapshot = service.get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )
    badge_map = _snapshot_map(snapshot)

    assert badge_map["SALES_REVENUE"].count == 1
    assert badge_map["SALES_REVENUE"].tone == "info"
    assert badge_map["RECEIPT_REGISTER"].count == 1
    assert badge_map["RECEIPT_REGISTER"].tone == "info"


def test_lab_manager_badge_checkpoint_counts_new_specimen_issues_but_not_old_ones(db):
    ctx = _seed_manager_context(db)
    service = LabManagerBadgeService(db)

    service.mark_section_viewed(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
        section_key=GovernanceSectionKey.SPECIMEN_ISSUES,
    )

    now = datetime.now(timezone.utc)
    db.add(
        LabSpecimen(
            id=uuid.uuid4(),
            clinic_id=ctx["clinic"].id,
            accession_number="LAB-20260319-00002",
            request_item_id=ctx["lab_request"].id,
            target_unit_id=ctx["haematology"].id,
            specimen_type="Blood",
            specimen_source="Blood",
            specimen_sequence=2,
            status=LabSpecimenStatus.LOST,
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()

    snapshot = service.get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )
    badge_map = _snapshot_map(snapshot)

    assert badge_map["SPECIMEN_ISSUES"].count == 1
    assert badge_map["SPECIMEN_ISSUES"].tone == "critical"


def test_lab_manager_badge_checkpoint_does_not_clear_unresolved_qc_attention(db):
    ctx = _seed_manager_context(db)
    service = LabManagerBadgeService(db)

    before = service.get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )
    before_map = _snapshot_map(before)
    assert before_map["QUALITY_CONTROL"].count == 1

    after_view = service.mark_section_viewed(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
        section_key=GovernanceSectionKey.QUALITY_CONTROL,
    )
    after_map = _snapshot_map(after_view)

    assert after_map["QUALITY_CONTROL"].count == 1
    assert after_map["QUALITY_CONTROL"].tone == "critical"

    db.add(
        LabQcRun(
            id=uuid.uuid4(),
            clinic_id=ctx["clinic"].id,
            unit_id=ctx["haematology"].id,
            machine_id=None,
            qc_level="Low",
            performed_by=ctx["supervisor"].id,
            performed_at=datetime.now(timezone.utc),
            status=LabQcStatus.WARNING,
        )
    )
    db.commit()

    refreshed = service.get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )
    refreshed_map = _snapshot_map(refreshed)

    assert refreshed_map["QUALITY_CONTROL"].count == 2
