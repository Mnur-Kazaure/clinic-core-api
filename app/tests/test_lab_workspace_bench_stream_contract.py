import json

from app.api.v1.lab import _encode_sse_event, get_lab_workspace_bench_snapshot
from app.services.lab_workspace_attention_service import LabWorkspaceAttentionService
from app.tests.test_lab_manager_governance_service import _seed_manager_context


def test_lab_workspace_bench_stream_encoder_formats_snapshot_payload(db):
    ctx = _seed_manager_context(db)
    snapshot = LabWorkspaceAttentionService(db).get_snapshot(
        clinic_id=ctx["clinic"].id,
        unit=ctx["haematology"],
    )

    encoded = _encode_sse_event(
        event="bench_snapshot",
        data=snapshot.model_dump(mode="json"),
        event_id=snapshot.generated_at.isoformat(),
    )

    assert "event: bench_snapshot" in encoded
    assert f"id: {snapshot.generated_at.isoformat()}" in encoded

    data_line = next(line for line in encoded.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    attention_keys = {item["key"] for item in payload["attention_items"]}
    tab_keys = {item["tab_key"] for item in payload["tab_badges"]}

    assert "PENDING_QUEUE" in attention_keys
    assert "QC_FAILURES" in attention_keys
    assert "QUEUE" in tab_keys
    assert "QC" in tab_keys


def test_lab_workspace_bench_handler_returns_selected_unit_snapshot(db):
    ctx = _seed_manager_context(db)
    payload = get_lab_workspace_bench_snapshot(
        db=db,
        current_user=ctx["tech"],
        selected_unit=ctx["haematology"],
    )

    assert payload.unit_id == ctx["haematology"].id
    assert payload.unit_name == "Haematology"
    assert {item.key.value for item in payload.attention_items} == {
        "PENDING_QUEUE",
        "AWAITING_SPECIMEN",
        "PENDING_VERIFICATIONS",
        "CRITICAL_ALERTS",
        "QC_FAILURES",
        "COMPLETED_TODAY",
    }
