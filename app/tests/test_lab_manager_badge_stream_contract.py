import json

from fastapi import HTTPException

from app.api.v1.lab import _encode_sse_event, get_lab_manager_badges
from app.core.guards.lab_guards import require_lab_manager_user
from app.services.lab_manager_badge_service import LabManagerBadgeService
from app.tests.test_lab_manager_governance_service import _seed_manager_context


def test_lab_manager_badge_stream_encoder_formats_snapshot_payload(db):
    ctx = _seed_manager_context(db)
    snapshot = LabManagerBadgeService(db).get_snapshot(
        clinic_id=ctx["clinic"].id,
        user_id=ctx["manager"].id,
    )

    encoded = _encode_sse_event(
        event="badge_snapshot",
        data=snapshot.model_dump(mode="json"),
        event_id=snapshot.generated_at.isoformat(),
    )

    assert "event: badge_snapshot" in encoded
    assert f"id: {snapshot.generated_at.isoformat()}" in encoded

    data_line = next(line for line in encoded.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    section_keys = {item["section_key"] for item in payload["sections"]}
    assert "PENDING_VERIFICATIONS" in section_keys
    assert "RECEIPT_REGISTER" in section_keys


def test_lab_manager_badges_handler_returns_manager_scoped_snapshot(db):
    ctx = _seed_manager_context(db)
    payload = get_lab_manager_badges(db=db, current_user=ctx["manager"])
    section_keys = {item.section_key.value for item in payload.sections}
    assert section_keys == {
        "PENDING_VERIFICATIONS",
        "CRITICAL_ALERTS",
        "SPECIMEN_ISSUES",
        "QUALITY_CONTROL",
        "SALES_REVENUE",
        "RECEIPT_REGISTER",
    }


def test_lab_manager_guard_blocks_non_manager_users(db):
    ctx = _seed_manager_context(db)

    try:
        require_lab_manager_user(user=ctx["tech"])
        assert False, "Expected lab manager guard to reject non-manager user"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Lab manager access required"
