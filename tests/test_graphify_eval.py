from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from tools import graphify_eval
from werkstatt.phases.explorer import _append_graphify_candidates
from werkstatt.state import LLMReply, RunState


def test_graphify_eval_compares_same_gold_set_and_records_live_provenance(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "src" / "target.py"
    source.parent.mkdir()
    source.write_text("def target(): return 1\n", encoding="utf-8")
    dataset = tmp_path / "eval.csv"
    with dataset.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["query", "expected_relevant_files"],
        )
        writer.writeheader()
        writer.writerow({
            "query": "target implementation",
            "expected_relevant_files": "src/target.py;tests/test_target.py",
        })

    monkeypatch.setattr(
        graphify_eval,
        "graphify_candidates",
        lambda *_args, **_kwargs: {
            "status": "ok", "index_sha256": "a" * 64,
            "graphify_version": "test", "stale_source_count": 0,
            "retrieval_method": "graphify_cli_query",
            "native_query_status": "native_query",
            "candidates": [{
                "file": "src/target.py",
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }],
        },
    )
    monkeypatch.setattr(
        graphify_eval,
        "_rank_source_files",
        lambda *_args, **_kwargs: (
            [{"file": "src/target.py"}, {"file": "unrelated.py"}],
            {"index_scan_succeeded": True},
        ),
    )

    report = graphify_eval.evaluate(tmp_path, dataset)

    assert report["case_count"] == 1
    assert report["all_selected_graphify_sources_current"] is True
    assert report["macro_metrics"]["graphify"] == {
        "precision_at_k": 0.2, "recall_at_k": 0.5, "mrr": 1.0,
    }
    assert report["macro_metrics"]["explorer"]["precision_at_k"] == 0.2
    assert report["macro_metrics"]["graphify_seeded"]["recall_at_k"] == 0.5
    assert report["delta_graphify_minus_explorer"]["precision_at_k"] == 0.0
    assert report["cases"][0]["graphify"]["index_sha256"] == "a" * 64
    assert report["cases"][0]["graphify"]["retrieval_method"] == (
        "graphify_cli_query"
    )
    assert report["cases"][0]["graphify"]["source_sha256"][
        "src/target.py"
    ] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert report["cases"][0]["graphify_seeded"]["source_sha256"][
        "src/target.py"
    ] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_graphify_eval_rejects_missing_gold_cases(tmp_path: Path) -> None:
    dataset = tmp_path / "empty.csv"
    dataset.write_text("query,expected_relevant_files\n", encoding="utf-8")

    try:
        graphify_eval.evaluate(tmp_path, dataset)
    except ValueError as exc:
        assert "keine Faelle" in str(exc)
    else:
        raise AssertionError("empty retrieval evaluation must fail")


def test_graphify_candidates_fill_only_remaining_bounded_slots() -> None:
    result = {"key_files": [{"file": f"content-{index}.py"} for index in range(4)]}
    seen = {item["file"] for item in result["key_files"]}
    candidates = [
        {"file": "content-0.py"},
        {"file": "graph-related.py", "why": "relationship"},
        {"file": "second-related.py"},
    ]

    added = _append_graphify_candidates(
        result, seen, candidates, ["checkpoint"],
        lambda path, why, confidence, limit, *, search_terms: {
            "file": path, "why": why, "confidence": confidence,
            "limit": limit, "search_terms": search_terms,
        },
    )

    assert added == 1
    assert [item["file"] for item in result["key_files"]] == [
        "content-0.py", "content-1.py", "content-2.py", "content-3.py",
        "graph-related.py",
    ]


@pytest.mark.parametrize(
    ("retrieval_method", "status", "stale_count"),
    [
        ("graphify_cli_query", "ok", 0),
        ("werkstatt_fallback", "partial_stale", 1),
    ],
)
def test_explorer_prioritizes_only_fresh_native_graphify(
    tmp_path: Path,
    monkeypatch,
    retrieval_method: str,
    status: str,
    stale_count: int,
) -> None:
    from werkstatt import explorer
    from werkstatt.phase_state import PhaseState
    from werkstatt.phases import explorer as explorer_actions

    paths = []
    content_paths = []
    for index in range(5):
        path = tmp_path / "src" / f"candidate_{index}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"class Candidate{index}: pass\n", encoding="utf-8")
        paths.append(path.relative_to(tmp_path).as_posix())
        content_path = tmp_path / "src" / f"content_{index}.py"
        content_path.write_text(
            f"class Content{index}: pass\n", encoding="utf-8",
        )
        content_paths.append(content_path.relative_to(tmp_path).as_posix())

    state = RunState(
        aufgabe="Implementiere eine projektweite Retry-Policy",
        project_dir=tmp_path,
        project_name="demo",
        docs={},
    )
    monkeypatch.setattr(explorer_actions, "audit", lambda *_a, **_kw: True)
    monkeypatch.setattr(explorer, "_messen", lambda *_a, **_kw: {})
    monkeypatch.setattr(explorer, "_format_findings", lambda _measurements: "")
    monkeypatch.setattr(
        "werkstatt.graphify_index.graphify_candidates",
        lambda *_a, **_kw: {
            "status": status,
            "retrieval_method": retrieval_method,
            "stale_source_count": stale_count,
            "index_sha256": "a" * 64,
            "candidates": [
                {"file": path, "why": "Graphify dependency candidate"}
                for path in paths
            ],
        },
    )
    monkeypatch.setattr(
        "werkstatt.graphify_index.refresh_graphify_index",
        lambda *_a, **_kw: {"status": "unavailable"},
    )
    monkeypatch.setattr(
        "werkstatt.explorer._rank_source_files",
        lambda *_a, **_kw: (
            (_ for _ in ()).throw(AssertionError(
                "fresh native Graphify should fill the candidate budget",
            ))
            if retrieval_method == "graphify_cli_query"
            else ([
                {"file": path, "why": "content match", "confidence": "high"}
                for path in content_paths
            ], {"index_scan_succeeded": True})
        ),
    )

    result, _phase_state = explorer_actions._phase_project_context_tools(
        state, state.aufgabe, "demo", PhaseState("demo", tmp_path / ".werkstatt"),
    )

    assert result == 0
    expected_paths = (
        paths if retrieval_method == "graphify_cli_query" else content_paths
    )
    assert [
        item["file"] for item in state.explorer_context["key_files"]
    ] == expected_paths
    assert all(
        item["source_complete"] is True
        and len(item["source_sha256"]) == 64
        for item in state.explorer_context["key_files"]
    )


def test_scout_keeps_bounded_grep_when_graphify_is_current_but_weak(
    tmp_path: Path, monkeypatch,
) -> None:
    from werkstatt import scout

    source = tmp_path / "src" / "relevant.py"
    source.parent.mkdir()
    source.write_text(
        "# markerneedle describes the exact behavior\nVALUE = 1\n",
        encoding="utf-8",
    )
    graph_source = tmp_path / "src" / "graph_neighbor.py"
    graph_source.write_text("VALUE = 2\n", encoding="utf-8")
    state = RunState(
        aufgabe="Finde `markerneedle` im Projekt", project_dir=tmp_path,
        project_name="demo", explorer_context={"key_files": []},
    )
    captured: dict[str, str] = {}
    monkeypatch.setattr(scout, "audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, fn: fn())
    monkeypatch.setattr(
        scout,
        "ask_llm",
        lambda *_args, **kwargs: (
            captured.update({"content": _args[2]})
            or LLMReply(ok=True, content='{"relevante_dateien": []}')
        ),
    )
    monkeypatch.setattr(
        "werkstatt.graphify_index.graphify_candidates",
        lambda *_args, **_kwargs: {
            "status": "ok", "index_sha256": "b" * 64,
            "graphify_version": "test",
            "native_subgraph": "EDGE graph_neighbor --uses [EXTRACTED]--> relevant()",
            "candidates": [{
                "file": "src/graph_neighbor.py", "why": "weak relationship",
                "symbols": [{"symbol": "graph_neighbor"}],
                "relationships": [{"relation": "uses"}],
            }],
        },
    )
    monkeypatch.setattr(
        "werkstatt.explorer._datei_inhalt_mit_fundstellen",
        lambda *_args, **_kwargs: {
            "source_sha256": "c" * 64, "text": "VALUE = 2",
        },
    )

    result = scout._run_scout(state, state.aufgabe, {}, [], "test-key")

    assert result == {"relevante_dateien": []}
    assert "GRAPHIFY-KANDIDATEN" in captured["content"]
    assert "GREP-TREFFER" in captured["content"]
    assert "relevant.py" in captured["content"]
    assert "graph_neighbor" in captured["content"]
    assert "uses" in captured["content"]
    assert "EDGE graph_neighbor" in captured["content"]
    assert "nicht vertrauenswuerdige" in captured["content"]


def test_scout_queries_graphify_for_implementation_tasks_without_explorer(
    tmp_path: Path, monkeypatch,
) -> None:
    """Scout can start from the goal and own discovery at its checkpoint."""
    from werkstatt import scout

    goal = "Implementiere die Retry-Policy fuer Benachrichtigungen im Projekt"
    state = RunState(
        aufgabe=goal,
        project_dir=tmp_path,
        project_name="demo",
        explorer_context={},
        docs={},
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(scout, "audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, fn: fn())
    monkeypatch.setattr(
        scout,
        "ask_llm",
        lambda *_args, **kwargs: (
            captured.update({"content": _args[2], "manifest": kwargs["context_manifest"]})
            or LLMReply(ok=True, content='{"relevante_dateien": []}')
        ),
    )

    def graphify(_root, query, **kwargs):
        captured["query"] = query
        captured["limit"] = kwargs["limit"]
        return {
            "status": "ok",
            "index_sha256": "b" * 64,
            "graphify_version": "test",
            "candidates": [{
                "file": "src/retry_policy.py",
                "why": "Graphify symbol/relationship match",
                "symbols": [{"symbol": "RetryPolicy"}],
                "relationships": [{"relation": "calls"}],
            }],
        }

    monkeypatch.setattr(
        "werkstatt.graphify_index.graphify_candidates", graphify,
    )
    monkeypatch.setattr(
        "werkstatt.graphify_index.refresh_graphify_index",
        lambda *_args, **_kwargs: {"status": "not_needed"},
    )
    monkeypatch.setattr(
        "werkstatt.explorer._datei_inhalt_mit_fundstellen",
        lambda *_args, **_kwargs: {
            "source_sha256": "c" * 64,
            "text": "class RetryPolicy: pass",
            "line_ranges": [[1, 1]],
            "total_lines": 1,
            "complete": True,
        },
    )

    result = scout._run_scout(state, goal, {}, [], "test-key")

    assert result == {"relevante_dateien": []}
    assert captured["query"].startswith(goal)
    assert captured["limit"] == 6
    content = captured["content"]
    assert isinstance(content, str)
    assert "GRAPHIFY-KANDIDATEN" in content
    assert "src/retry_policy.py" in content
    assert "RetryPolicy" in content
    assert "source_complete" in content
    assert "source_sha256" in content
    assert "source_line_ranges" in content
