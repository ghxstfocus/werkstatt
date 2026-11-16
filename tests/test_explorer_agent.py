"""Tests fuer werkstatt/explorer.py (Phase 14)."""
from __future__ import annotations

import hashlib
import json
from unittest.mock import patch

from werkstatt.explorer import (
    _list_py_file_inventory,
    _python_inventory_context,
    _rank_python_source_files,
    _rank_source_files,
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
    assert "begrenzte lexikalische Auswahl" in ask.call_args.args[1]
    assert manifest["budget_event"] == "explorer_context"
    assert manifest["measurement_count"] == 0
    assert manifest["file_count"] == 0
    assert manifest["file_scan_succeeded"] is True
    assert manifest["file_index_truncated"] is False
    assert manifest["file_scan_complete"] is True
    assert manifest["files_offered"] == []
    assert manifest["files_omitted_from_prompt"] == 0
    assert manifest["required_context_complete"] is True
    assert manifest["request_chars"] <= manifest["max_request_chars"]
    assert "Inventar vollstaendig; keine Quell-/Textdateien" in ask.call_args.args[2]
    assert "Scan fehlgeschlagen oder teilweise" not in ask.call_args.args[2]
    assert manifest["user_chars"] == len(ask.call_args.args[2])
    for section in manifest["sections"]:
        excerpt = ask.call_args.args[2][
            section["prompt_start"]:section["prompt_end"]
        ]
        assert len(excerpt) == section["chars"]
        assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == (
            section["sha256"]
        )


def test_python_inventory_marks_prompt_omissions_and_scan_limit():
    paths = [
        *(f"src/module_{index}_target.py" for index in range(75)),
        *(f"src/other_{index}.py" for index in range(125)),
    ]

    context, manifest = _python_inventory_context(
        paths, scan_succeeded=True, index_truncated=True, query="target",
    )

    assert {
        key: value for key, value in manifest.items()
        if key != "path_manifest"
    } == {
        "file_count": 200,
        "file_scan_succeeded": True,
        "file_index_truncated": True,
        "file_scan_complete": False,
        "file_scan_cap": 200,
        "file_selection_strategy": "query_path_terms_v1",
        "query_tokens_used": 1,
        "query_common_tokens_ignored": 0,
        "query_matched_file_count": 75,
        "files_unmatched_by_query": 125,
        "query_matches_omitted_due_to_prompt_cap": 25,
        "files_offered": paths[:50],
        "files_omitted_from_prompt": 150,
        "prompt_file_cap": 50,
    }
    paths_by_name = {item["path"]: item for item in manifest["path_manifest"]}
    included = paths_by_name[paths[0]]
    assert context[included["prompt_start"]:included["prompt_end"]] == paths[0]
    assert included["status"] == "included"
    assert paths_by_name[paths[50]]["status"] == "omitted_prompt_cap"
    assert "prompt_start" not in paths_by_name[paths[50]]
    assert paths_by_name[paths[-1]]["status"] == "not_selected_by_query"
    assert "Indexlimit 200 erreicht" in context
    assert "mindestens" not in context
    assert "25 passende Pfade" in context
    assert "kein Negativbeleg" in context
    assert paths[50] not in context


def test_explorer_file_path_offsets_bind_to_actual_request(tmp_path):
    source = tmp_path / "src" / "target.py"
    source.parent.mkdir()
    source.write_text("def target():\n    return True\n", encoding="utf-8")
    state = _state(tmp_path)

    class FakeReply:
        ok = True
        content = '{"findings":"target file found","key_files":[],"next_reads":[]}'

    with patch("werkstatt.explorer.ask_llm", return_value=FakeReply()) as ask:
        run_explorer(state, "Explain the target")

    user = ask.call_args.args[2]
    manifest = ask.call_args.kwargs["context_manifest"]
    record = next(
        item for item in manifest["path_manifest"]
        if item["path"] == "src/target.py"
    )
    assert record["status"] == "included"
    excerpt = user[record["prompt_start"]:record["prompt_end"]]
    assert excerpt == "src/target.py"
    assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == record["sha256"]


def test_explorer_blocks_oversized_context_before_model_call(tmp_path):
    state = _state(tmp_path)
    events = []
    with patch("werkstatt.explorer.EXPLORER_REQUEST_MAX_CHARS", 1), \
         patch("werkstatt.explorer.ask_llm") as ask, \
         patch(
             "werkstatt.explorer.audit",
             side_effect=lambda *args: events.append(args),
         ):
        result = run_explorer(state, "A sufficiently long question")

    ask.assert_not_called()
    assert result["context_budget"]["action"] == "blocked"
    assert result["context_budget"]["required_context_complete"] is False
    assert "nicht als vollstaendige Antwort" in result["findings"]
    event = next(
        payload for name, payload, *_ in events if name == "explorer_result"
    )
    assert event["context_budget"]["action"] == "blocked"


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


def test_content_retrieval_ranks_specific_source_hits_and_reports_scope(tmp_path):
    (tmp_path / "alpha.py").write_text(
        "def unrelated():\n    return 1\n", encoding="utf-8",
    )
    (tmp_path / "beta.py").write_text(
        "def quasarledger_sync():\n    return 2\n", encoding="utf-8",
    )

    matches, manifest = _rank_python_source_files(
        tmp_path, "Find the QuasarLedger synchronization logic",
    )

    assert [item["file"] for item in matches] == ["beta.py"]
    assert "quasarledger" in matches[0]["matched_terms"]
    assert manifest["indexed_file_scope"] == (
        "Python-Dateien, kein Vollindex des Projekts"
    )
    assert manifest["content_scanned_file_count"] == 2
    assert manifest["index_scan_succeeded"] is True
    assert manifest["omissions_are_not_negative_evidence"] is True
    assert len(matches[0]["source_sha256"]) == 64


def test_content_retrieval_excludes_already_selected_and_common_terms(tmp_path):
    (tmp_path / "alpha.py").write_text(
        "commonword firstthing\n", encoding="utf-8",
    )
    (tmp_path / "beta.py").write_text(
        "commonword secondthing\n", encoding="utf-8",
    )

    matches, manifest = _rank_python_source_files(
        tmp_path, "commonword", exclude={"alpha.py"},
    )

    assert matches == []
    assert manifest["matching_file_count"] == 0
    assert manifest["common_or_unmatched_tokens_ignored"] == 1


def test_source_retrieval_finds_typescriptx_and_hashes_selected_source(tmp_path):
    target = tmp_path / "frontend" / "dashboard.tsx"
    target.parent.mkdir()
    target.write_text(
        "export function quasarLedgerSync() { return true; }\n",
        encoding="utf-8",
    )

    matches, manifest = _rank_source_files(
        tmp_path, "Find the QuasarLedger synchronization logic",
    )

    assert [item["file"] for item in matches] == ["frontend/dashboard.tsx"]
    assert matches[0]["source_sha256"] == hashlib.sha256(
        target.read_bytes(),
    ).hexdigest()
    assert ".tsx" in manifest["indexed_extensions"]
    assert ".py" in manifest["indexed_extensions"]
    assert manifest["indexed_file_scope"].startswith("Quell-/Textdateien")


def test_explorer_wires_content_retrieval_into_actual_role_request(tmp_path):
    unrelated = tmp_path / "alpha.py"
    unrelated.write_text("def unrelated(): return 1\n", encoding="utf-8")
    relevant = tmp_path / "beta.py"
    source = "def quasarledger_sync(): return 2\n"
    relevant.write_text(source, encoding="utf-8")
    state = _state(tmp_path)

    class FakeReply:
        ok = True
        content = '{"findings":"candidate found","key_files":[],"next_reads":[]}'

    with patch("werkstatt.explorer.ask_llm", return_value=FakeReply()) as ask:
        result = run_explorer(state, "Explain QuasarLedger synchronization")

    user = ask.call_args.args[2]
    manifest = ask.call_args.kwargs["context_manifest"]
    retrieval = manifest["content_retrieval"]
    assert result["content_retrieval"] == retrieval
    assert retrieval["indexed_file_scope"] == (
        "Quell-/Textdateien der Extension-Allowlist, kein Vollindex "
        "des Projekts"
    )
    assert [item["file"] for item in retrieval["selected_sources"]] == [
        "beta.py",
    ]
    candidate = retrieval["selected_sources"][0]
    excerpt = user[candidate["prompt_start"]:candidate["prompt_end"]]
    assert excerpt == "beta.py"
    assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == (
        candidate["prompt_sha256"]
    )
    assert hashlib.sha256(relevant.read_bytes()).hexdigest() == (
        candidate["source_sha256"]
    )
    excerpt = user[
        candidate["source_excerpt_prompt_start"]:
        candidate["source_excerpt_prompt_end"]
    ]
    assert json.loads(excerpt) == "000001 | def quasarledger_sync(): return 2"
    assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == (
        candidate["source_excerpt_prompt_sha256"]
    )
    assert candidate["source_excerpt_complete"] is True
    assert "Keine gueltigen spezifischen Quell-/Texttreffer" not in user


def test_explorer_supplements_path_matches_with_distinct_content_evidence(
    tmp_path,
):
    (tmp_path / "quasarledger_client.py").write_text(
        "def client(): return None\n", encoding="utf-8",
    )
    relevant = tmp_path / "sync_engine.py"
    source = "def quasarledger_sync(): return True\n"
    relevant.write_text(source, encoding="utf-8")
    state = _state(tmp_path)

    class FakeReply:
        ok = True
        content = '{"findings":"found","key_files":[],"next_reads":[]}'

    with patch("werkstatt.explorer.ask_llm", return_value=FakeReply()) as ask:
        result = run_explorer(state, "Explain QuasarLedger synchronization")

    retrieval = result["content_retrieval"]
    assert retrieval["selected_files"] == ["sync_engine.py"]
    assert retrieval["matching_file_count"] == 1
    assert retrieval["indexed_file_count"] == 2
    user = ask.call_args.args[2]
    candidate = retrieval["selected_sources"][0]
    excerpt = user[
        candidate["source_excerpt_prompt_start"]:
        candidate["source_excerpt_prompt_end"]
    ]
    assert json.loads(excerpt) == "000001 | def quasarledger_sync(): return True"


def test_content_retrieval_reports_total_byte_budget_omissions(tmp_path):
    (tmp_path / "alpha.py").write_text("x" * 10, encoding="utf-8")
    (tmp_path / "beta.py").write_text(
        "def quasarledger(): pass\n", encoding="utf-8",
    )

    matches, manifest = _rank_python_source_files(
        tmp_path, "QuasarLedger", max_total_bytes=10,
    )

    assert matches == []
    assert manifest["content_scanned_bytes"] == 10
    assert manifest["files_skipped_total_byte_cap"] == 1
    assert manifest["omissions_are_not_negative_evidence"] is True


def test_python_inventory_does_not_turn_scan_error_into_empty_repo():
    context, manifest = _python_inventory_context([], scan_succeeded=False, index_truncated=False)

    assert manifest["file_scan_complete"] is False
    assert "Scan fehlgeschlagen oder teilweise" in context
    assert "keine Python-Dateien gefunden" not in context


def test_python_inventory_prioritizes_only_query_matching_paths():
    paths = ["src/alpha_service.py", "src/beta_service.py", "src/tests.py"]

    context, manifest = _python_inventory_context(
        paths, scan_succeeded=True, index_truncated=False,
        query="Fix the beta service failure",
    )

    assert manifest["query_matched_file_count"] == 1
    assert manifest["files_offered"] == ["src/beta_service.py"]
    assert manifest["files_unmatched_by_query"] == 2
    assert "src/alpha_service.py" not in context
    assert "kein Negativbeleg" in context


def test_python_inventory_offers_no_arbitrary_paths_without_query_match():
    paths = ["src/alpha.py", "src/beta.py"]

    context, manifest = _python_inventory_context(
        paths, scan_succeeded=True, index_truncated=True,
        query="Explain the architecture",
    )

    assert manifest["files_offered"] == []
    assert manifest["query_matched_file_count"] == 0
    assert manifest["files_unmatched_by_query"] == 2
    assert manifest["file_scan_complete"] is False
    assert "keine beliebigen Dateien angeboten" in context
    assert "gezielt nachgeladen" in context


def test_explorer_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    result = run_explorer(st, "X")
    assert result["key_files"] == []
