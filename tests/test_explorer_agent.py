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
    assert manifest["file_scan_succeeded"] is True
    assert manifest["file_index_truncated"] is False
    assert manifest["file_scan_complete"] is True
    assert manifest["files_offered"] == []
    assert manifest["files_omitted_from_prompt"] == 0
    assert "Inventar vollstaendig; keine Python-Dateien gefunden" in ask.call_args.args[2]
    assert "Scan fehlgeschlagen oder teilweise" not in ask.call_args.args[2]
    assert manifest["user_chars"] == len(ask.call_args.args[2])


def test_python_inventory_marks_prompt_omissions_and_scan_limit():
    paths = [f"src/module_{index}.py" for index in range(200)]

    context, manifest = _python_inventory_context(
        paths, scan_succeeded=True, index_truncated=True,
    )

    assert manifest == {
        "file_count": 200,
        "file_scan_succeeded": True,
        "file_index_truncated": True,
        "file_scan_complete": False,
        "file_scan_cap": 200,
        "files_offered": paths[:50],
        "files_omitted_from_prompt": 150,
        "prompt_file_cap": 50,
    }
    assert "Indexlimit 200 erreicht" in context
    assert "mindestens" not in context
    assert "150 ausgelassen" in context
    assert "kein Negativbeleg" in context
    assert paths[50] not in context


def test_python_inventory_scan_limit_is_visible(tmp_path):
    paths = sorted(
        str(tmp_path / f"module_{index}.py") for index in range(201)
    )
    def fake_walk(_root, *, topdown, onerror, followlinks):
        assert topdown is True
        assert followlinks is False
        yield str(tmp_path), [], [f"module_{index}.py" for index in range(201)]

    with patch("werkstatt.explorer.os.walk", side_effect=fake_walk):
        indexed, scan_succeeded, index_truncated = _list_py_file_inventory(tmp_path)

    assert indexed == paths[:200]
    assert scan_succeeded is True
    assert index_truncated is True


def test_python_inventory_nonzero_find_is_not_complete(tmp_path):
    def fake_walk(_root, *, topdown, onerror, followlinks):
        onerror(PermissionError("unreadable directory"))
        yield str(tmp_path), [], ["partial.py"]

    with patch("werkstatt.explorer.os.walk", side_effect=fake_walk):
        indexed, scan_succeeded, index_truncated = _list_py_file_inventory(tmp_path)

    assert indexed == [str(tmp_path / "partial.py")]
    assert scan_succeeded is False
    assert index_truncated is False


def test_python_inventory_does_not_turn_scan_error_into_empty_repo():
    context, manifest = _python_inventory_context([], scan_succeeded=False, index_truncated=False)

    assert manifest["file_scan_complete"] is False
    assert "Scan fehlgeschlagen oder teilweise" in context
    assert "keine Python-Dateien gefunden" not in context


def test_explorer_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    result = run_explorer(st, "X")
    assert result["key_files"] == []
