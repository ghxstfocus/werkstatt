from tools import audit_drift


def test_catalog_reader_includes_additive_frozenset_assignment() -> None:
    kinds = audit_drift.finde_katalog()

    assert "llm_call" in kinds
    assert "loop_checkpoint_decision" in kinds


def test_code_reader_resolves_chat_and_web_audit_wrappers() -> None:
    kinds = audit_drift.finde_code_kinds()

    assert "chat_job_queued" in kinds
    assert "chat_job_tool_call" in kinds
    assert "web_loop_paused" in kinds


def test_code_reader_resolves_role_worker_audit_callbacks() -> None:
    kinds = audit_drift.finde_code_kinds()

    assert "planner_role_artifact_rejected" in kinds
    assert "planner_role_artifact_reused" in kinds
