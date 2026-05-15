from app.services.lab_workspace_attention_service import LabWorkspaceAttentionService
from app.tests.test_lab_manager_governance_service import _seed_manager_context


def _attention_map(snapshot):
    return {item.key.value: item for item in snapshot.attention_items}


def _tab_map(snapshot):
    return {item.tab_key.value: item for item in snapshot.tab_badges}


def test_lab_workspace_bench_snapshot_is_unit_scoped_and_backend_owned(db):
    ctx = _seed_manager_context(db)

    snapshot = LabWorkspaceAttentionService(db).get_snapshot(
        clinic_id=ctx["clinic"].id,
        unit=ctx["haematology"],
    )

    attention = _attention_map(snapshot)
    tab_badges = _tab_map(snapshot)

    assert snapshot.unit_name == "Haematology"
    assert snapshot.pending_requests == 1
    assert snapshot.awaiting_specimen == 1
    assert snapshot.pending_verifications == 1
    assert snapshot.qc_failures == 1
    assert snapshot.specimen_issue_count == 1
    assert snapshot.queue_count == 0
    assert snapshot.result_workbench_count == 1
    assert snapshot.qc_attention_count == 1

    assert attention["PENDING_QUEUE"].count == 0
    assert attention["AWAITING_SPECIMEN"].tone == "warning"
    assert attention["PENDING_VERIFICATIONS"].count == 1
    assert attention["QC_FAILURES"].tone == "critical"

    assert tab_badges["SPECIMENS"].count == 1
    assert tab_badges["SPECIMENS"].tone == "critical"
    assert tab_badges["RESULTS"].count == 1
    assert tab_badges["RESULTS"].tone == "warning"
    assert tab_badges["QC"].count == 1
    assert tab_badges["QC"].tone == "critical"
