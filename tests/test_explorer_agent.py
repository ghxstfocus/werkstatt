"""Tests fuer werkstatt/explorer.py (Phase 14)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.explorer import (
    _list_py_file_inventory,
    _python_inventory_context,
    run_explorer,
)
from werkstatt.state import RunState


def _state(tmp_path):
    return RunState(
        block_id="t", aufgabe="X", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p",
    )


def test_explorer_liefert_json(tmp_path):
    st = _state(tmp_path)
    fake = '{"findings": "X ist relevant", "key_files": [{"file": "a.py", "why": "entry", "symbols": "main", "confidence": "high"}], "next_reads": ["a.py"]}'

    class FakeReply:
        ok = True
        content = fake

    with patch(
        "werkstatt.explorer.ask_llm", return_value=FakeReply(),
    ) as ask:
        result = run_explorer(st, "Wie funktioniert X?")
        assert result["findings"] == "X ist relevant"
        assert len(result["key_files"]) == 1
        assert result["key_files"][0]["file"] == "a.py"
    manifest = ask.call_args.kwargs["context_manifest"]
    assert manifest["budget_event"] == "explorer_context"
    assert manifest["measurement_count"] == 0
    assert manifest["file_count"] == 0
    assert manifest["file_scan_complete"] is False
    assert manifest["files_offered"] == []
    assert manifest["files_omitted_from_prompt"] == 0
    assert "Inventar unvollstaendig oder nicht verfuegbar" in ask.call_args.args[2]
    assert "keine Python-Dateien gefunden" not in ask.call_args.args[2]
    assert manifest["user_chars"] == len(ask.call_args.args[2])


def test_python_inventory_marks_prompt_omissions_and_scan_limit():
    paths = [f"src/module_{index}.py" for index in range(200)]

    context, manifest = _python_inventory_context(
        paths, scan_complete=False,
    )

    assert manifest == {
        "file_count": 200,
        "file_scan_complete": False,
        "file_scan_cap": 200,
        "files_offered": paths[:50],
        "files_omitted_from_prompt": 150,
        "prompt_file_cap": 50,
    }
    assert "Inventar unvollstaendig oder nicht verfuegbar" in context
    assert "mindestens" not in context
    assert "150 ausgelassen" in context
    assert "kein Negativbeleg" in context
    assert paths[50] not in context


def test_python_inventory_scan_limit_is_visible(tmp_path):
    paths = [f"{tmp_path}/module_{index}.py" for index in range(201)]
    result = type("Result", (), {"stdout": "\n".join(paths), "returncode": 0})()

    with patch("werkstatt.explorer.subprocess.run", return_value=result):
        indexed, complete = _list_py_file_inventory(tmp_path)

    assert indexed == paths[:200]
    assert complete is False


def test_python_inventory_nonzero_find_is_not_complete(tmp_path):
    result = type("Result", (), {
        "stdout": f"{tmp_path}/partial.py\n",
        "returncode": 1,
    })()

    with patch("werkstatt.explorer.subprocess.run", return_value=result):
        indexed, complete = _list_py_file_inventory(tmp_path)

    assert indexed == [f"{tmp_path}/partial.py"]
    assert complete is False


def test_python_inventory_does_not_turn_scan_error_into_empty_repo():
    context, manifest = _python_inventory_context([], scan_complete=False)

    assert manifest["file_scan_complete"] is False
    assert "unvollstaendig oder nicht verfuegbar" in context
    assert "keine Python-Dateien gefunden" not in context


def test_explorer_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    result = run_explorer(st, "X")
    assert result["key_files"] == []
