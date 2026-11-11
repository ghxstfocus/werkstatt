"""OP-040: _task_ende Idempotenz-Guard."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.state import RunState
from werkstatt.task_runner import _task_ende


def _run_state(tmp_path) -> RunState:
    return RunState(
        block_id="t", aufgabe="t", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="x", budget={},
        agent_docs={}, project_dir=tmp_path,
    )


def test_erster_aufruf_geht_durch(tmp_path):
    state = _run_state(tmp_path)
    ps = MagicMock()
    ps.get_task.return_value = None
    assert not _task_ende(state, ps, "t1", ok=False, name="x", failure="builder_failed")
    ps.mark_failed.assert_called_once_with("t1", failure="builder_failed")


def test_zweiter_aufruf_skip_nach_failed(tmp_path):
    state = _run_state(tmp_path)
    ps = MagicMock()
    ps.get_task.side_effect = [None, {"status": "failed"}]
    _task_ende(state, ps, "t1", ok=False, name="x", failure="patch_write_failed")
    _task_ende(state, ps, "t1", ok=False, name="x", failure="reviewer_rejected_no_patch")
    assert ps.mark_failed.call_count == 1


def test_zweiter_aufruf_skip_nach_done(tmp_path):
    state = _run_state(tmp_path)
    ps = MagicMock()
    ps.get_task.side_effect = [None, {"status": "done"}]
    assert _task_ende(state, ps, "t1", ok=True, name="x")
    assert not _task_ende(state, ps, "t1", ok=True, name="x")
    assert ps.mark_done.call_count == 1


def test_pending_erlaubt_erneuten_aufruf(tmp_path):
    state = _run_state(tmp_path)
    ps = MagicMock()
    ps.get_task.return_value = {"status": "pending"}
    assert _task_ende(state, ps, "t1", ok=True, name="x")
    ps.mark_done.assert_called_once()


def test_split_erlaubt_erneuten_aufruf(tmp_path):
    state = _run_state(tmp_path)
    ps = MagicMock()
    ps.get_task.return_value = {"status": "split"}
    _task_ende(state, ps, "t1", ok=False, name="x", failure="reviewer_high_bug")
    ps.mark_failed.assert_called_once()
