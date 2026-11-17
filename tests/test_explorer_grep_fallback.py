"""Explorer-Grep-Fallback bei leeren key_files.

Live-Bug 2026-11-09 20:25 (Run werkstatt-20261109-202502-4e5bfd9c):
- Aufgabe "OP-389b: DRY-Migration auf `require_ws_auth`"
- Suchbegriff extrahiert: ['require_ws_auth']
- _messen() fand nichts (kein .py-Pfad, keine Migration)
- key_files=[], loop_explorer_leer, state_contract_violation, loop_failed
- Loop crasht nach 2 Sekunden, kein Task gebaut

Fix: deterministischer Grep-Fallback ueber .py-Dateien, wenn
_suchbegriffe gesetzt und key_files leer. Kein LLM, testbar.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch


def _state(tmp_path: Path, aufgabe: str):
    """Minimaler RunState-Mock (SimpleNamespace reicht, Explorer-Phase
    braucht nur project_dir, project_name, api_key, explorer_context)."""
    from types import SimpleNamespace
    return SimpleNamespace(
        project_dir=tmp_path,
        project_name="test",
        api_key="sk-test",
        explorer_context=None,
        explorer_findings={},
        suchbegriffe=[],
        # Felder, die collect_project_context ab Zeile 220+ liest:
        tasks=None,
        auftrag_bereits_erfuellt=False,
        auftrag_bereits_erfuellt_bestaetigt=False,
        auftrag_bereits_erfuellt_quelle="",
    )


def test_grep_fallback_findet_dateien_bei_backtick_suchbegriff(tmp_path):
    """Aufgabe mit `require_ws_auth` und vorhandener Datei -> key_files > 0."""
    (tmp_path / "werkstatt").mkdir()
    (tmp_path / "werkstatt" / "auth.py").write_text(
        "def require_ws_auth(ws):\n    return True\n"
    )
    (tmp_path / "werkstatt" / "irrelevant.py").write_text(
        "def foo():\n    pass\n"
    )

    from werkstatt.roles import project_context as exp

    state = _state(tmp_path, "OP-XXX: DRY-Migration auf `require_ws_auth`")

    # run_explorer leer mocken (deterministisch, kein LLM)
    with (
        patch.object(exp, "run_explorer", create=True, return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        _rc, _ps = exp.collect_project_context(
            state,
            "OP-XXX: DRY-Migration auf `require_ws_auth`",
            "test",
            None,
        )

    # state.explorer_context muss gesetzt sein
    ctx = state.explorer_context or {}
    files = [k.get("file") for k in ctx.get("key_files", [])]
    assert "werkstatt/auth.py" in files, (
        f"Grep-Fallback muss auth.py finden (enthaelt require_ws_auth). "
        f"Gefunden: {files}"
    )
    assert "werkstatt/irrelevant.py" not in files, (
        f"irrelevant.py darf NICHT in key_files sein. Gefunden: {files}"
    )
    evidence = next(
        item for item in ctx["key_files"]
        if item.get("file") == "werkstatt/auth.py"
    )
    assert evidence["source_line_ranges"] == [[1, 2]]
    assert evidence["source_total_lines"] == 2
    assert evidence["source_complete"] is True
    assert "000001 | def require_ws_auth(ws):" in evidence["preview"]
    assert evidence["source_sha256"] == hashlib.sha256(
        (tmp_path / "werkstatt" / "auth.py").read_bytes(),
    ).hexdigest()


def test_inhaltssuche_findet_auftragsbegriff_ohne_pfad_oder_backticks(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "alpha.py").write_text(
        "def unrelated():\n    return 1\n", encoding="utf-8",
    )
    target = tmp_path / "src" / "beta.tsx"
    target.write_text(
        "export function quasarLedgerSync() { return 2; }\n",
        encoding="utf-8",
    )
    from werkstatt.roles import project_context as exp

    task = "Finde die QuasarLedger synchronization logic"
    state = _state(tmp_path, task)
    with (
        patch.object(exp, "run_explorer", create=True, return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        exp.collect_project_context(state, task, "test", None)

    context = state.explorer_context
    evidence = next(
        item for item in context["key_files"]
        if item["file"] == "src/beta.tsx"
    )
    retrieval = context["content_retrieval"]
    assert "000001 | export function quasarLedgerSync()" in evidence["preview"]
    assert evidence["source_line_ranges"] == [[1, 1]]
    assert evidence["source_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert retrieval["selected_files"] == ["src/beta.tsx"]
    assert retrieval["indexed_file_scope"] == (
        "Quell-/Textdateien der Extension-Allowlist, kein Vollindex "
        "des Projekts"
    )


def test_content_retrieval_from_explorer_is_reused_for_architect_handoff(
    tmp_path: Path,
    monkeypatch,
):
    target = tmp_path / "src" / "beta.tsx"
    target.parent.mkdir()
    target.write_text(
        "export function quasarLedgerSync() { return 2; }\n",
        encoding="utf-8",
    )
    from werkstatt import explorer as explorer_module
    from werkstatt.roles import project_context as phase_explorer

    task = "Finde die QuasarLedger synchronization logic"
    source_candidates, _retrieval = explorer_module._rank_source_files(
        tmp_path, task, limit=5,
    )
    assert source_candidates[0]["file"] == "src/beta.tsx"
    state = _state(tmp_path, task)

    with (
        patch.object(phase_explorer, "group_start"),
        patch.object(phase_explorer, "group_end"),
        patch.object(phase_explorer, "step"),
        patch.object(phase_explorer, "audit"),
    ):
        phase_explorer.collect_project_context(state, task, "test", None)

    evidence = next(
        item for item in state.explorer_context["key_files"]
        if item["file"] == "src/beta.tsx"
    )
    assert evidence["source_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert "000001 | export function quasarLedgerSync()" in evidence["preview"]
    assert state.explorer_context["content_retrieval"]["selected_files"] == [
        "src/beta.tsx",
    ]
    assert state.explorer_context["dispatch"]["role"] == "project_context_tools"


def test_leerer_retrievalbericht_bleibt_fuer_scout_erhalten(tmp_path):
    (tmp_path / "alpha.py").write_text("def alpha():\n    pass\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("def beta():\n    pass\n", encoding="utf-8")
    from werkstatt.roles import project_context as exp

    task = "Suche nach dem seltenen Begriff QuasarLedgerNonce"
    state = _state(tmp_path, task)
    with (
        patch.object(exp, "run_explorer", create=True, return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _ = exp.collect_project_context(state, task, "test", None)

    assert rc == 0
    assert state.explorer_context["key_files"] == []
    assert state.explorer_context["content_retrieval"]["matching_file_count"] == 0
    assert state.explorer_context["content_retrieval"][
        "omissions_are_not_negative_evidence"
    ] is True


def test_explorer_vorschau_wird_vor_handoff_aus_repo_neu_gelesen(tmp_path):
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "core.py"
    source.write_text("def actual_source():\n    return 7\n")

    from werkstatt.roles import project_context as exp

    state = _state(tmp_path, "Analysiere src/core.py")
    untrusted_preview = "FORGED PREVIEW"
    with (
        patch.object(
            exp,
            "run_explorer", create=True,
            return_value={
                "findings": "Vorschlag",
                "key_files": [{
                    "file": "src/core.py",
                    "preview": untrusted_preview,
                    "why": "Explorer-Vorschlag",
                    "confidence": "high",
                }],
            },
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        exp.collect_project_context(
            state, "Analysiere src/core.py", "test", None,
        )

    evidence = next(
        item for item in state.explorer_context["key_files"]
        if item["file"] == "src/core.py"
    )
    assert untrusted_preview not in evidence["preview"]
    assert "000001 | def actual_source():" in evidence["preview"]
    assert evidence["source_line_ranges"] == [[1, 2]]
    assert evidence["source_complete"] is True


def test_eindeutige_literalersetzung_ueberspringt_explorer_llm(tmp_path):
    """Belegte Ein-Datei-Ersetzung braucht keine explorative LLM-Suche."""
    target = tmp_path / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_text("value = 'old_value'\n", encoding="utf-8")
    from werkstatt.roles import project_context as exp

    aufgabe = "Ersetze `old_value` durch `new_value` in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(
            exp, "run_explorer", create=True,
            side_effect=AssertionError("Explorer-LLM waere hier redundant"),
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp.collect_project_context(
            state, aufgabe, "test", None,
        )

    assert rc == 0
    files = [item.get("file") for item in state.explorer_context["key_files"]]
    assert "werkstatt/sample.py" in files


def test_eng_einzeldatei_aenderung_ueberspringt_explorer_llm(tmp_path):
    """Ein enges, explizites Ziel braucht keinen zusaetzlichen Explorer-LLM-Call."""
    target = tmp_path / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_text("value = 1\n", encoding="utf-8")
    from werkstatt.roles import project_context as exp

    aufgabe = "Aendere den Wert in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(
            exp, "run_explorer", create=True,
            side_effect=AssertionError("Explorer-LLM ist fuer das enge Ziel redundant"),
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp.collect_project_context(
            state, aufgabe, "test", None,
        )

    assert rc == 0
    files = [item.get("file") for item in state.explorer_context["key_files"]]
    assert "werkstatt/sample.py" in files


def test_graphify_runs_from_complete_explorer_seeds_after_five_direct_files(
    tmp_path: Path, monkeypatch,
):
    from werkstatt.roles import project_context as phase_explorer

    paths = [f"src/module_{index}.py" for index in range(5)]
    for index, relative in enumerate(paths):
        path = tmp_path / relative
        path.parent.mkdir(exist_ok=True)
        path.write_text(f"VALUE_{index} = {index}\n", encoding="utf-8")
    task = "Pruefe " + " ".join(paths)
    state = _state(tmp_path, task)
    observed: dict[str, object] = {}

    def graph_query(*_args, **kwargs):
        observed["seed_paths"] = kwargs.get("seed_paths")
        observed["seed_sha256"] = kwargs.get("seed_sha256")
        return {
            "status": "ok", "candidates": [], "seed_paths": paths[:3],
            "index_sha256": "a" * 64,
        }

    monkeypatch.setattr(
        "werkstatt.graphify_index.graphify_candidates", graph_query,
    )
    monkeypatch.setattr(
        "werkstatt.graphify_index.refresh_graphify_index",
        lambda *_args: {"status": "not_needed"},
    )
    with (
        patch.object(
            phase_explorer, "run_explorer", create=True,
            return_value={"findings": "Five explicit files were read."},
        ),
        patch.object(phase_explorer, "group_start"),
        patch.object(phase_explorer, "group_end"),
        patch.object(phase_explorer, "step"),
        patch.object(phase_explorer, "audit"),
    ):
        rc, _phase_state = phase_explorer.collect_project_context(
            state, task, "test", None,
        )

    assert rc == 0
    assert observed["seed_paths"] == paths[:3]
    assert set(observed["seed_sha256"]) == set(paths)
    assert len(state.explorer_context["key_files"]) == 5


def test_failed_related_file_scan_is_visible_and_disables_explorer_skip(
    tmp_path, monkeypatch,
):
    target = tmp_path / "werkstatt" / "sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("value = 1\n", encoding="utf-8")
    from werkstatt import explorer as explorer_module
    from werkstatt.roles import project_context as phase_explorer

    monkeypatch.setattr(
        explorer_module,
        "_verwandte_dateien",
        lambda *_args: (_ for _ in ()).throw(OSError("private path detail")),
    )
    audit_events = []
    task = "Aendere den Wert in werkstatt/sample.py"
    state = _state(tmp_path, task)

    with (
        patch.object(phase_explorer, "group_start"),
        patch.object(phase_explorer, "group_end"),
        patch.object(phase_explorer, "step"),
        patch.object(
            phase_explorer,
            "audit",
            side_effect=lambda *args: audit_events.append(args),
        ),
    ):
        rc, _phase_state = phase_explorer.collect_project_context(
            state, task, "test", None,
        )

    assert rc == 0
    assert state.explorer_context["dispatch"]["role"] == "project_context_tools"
    assert state.explorer_context["related_files_scan"] == {
        "status": "failed",
        "explicit_file_count": 1,
        "error_type": "OSError",
    }
    assert "gelten als unbekannt" in state.explorer_context["findings"]
    assert "private path detail" not in state.explorer_context["findings"]
    assert any(
        event[0] == "loop_explorer_related_files_failed"
        and event[1]["exception_type"] == "OSError"
        for event in audit_events
    )


def test_diagnostische_einzeldatei_nutzt_keine_explorer_llm_rolle(tmp_path):
    """Diagnoseauftraege erhalten Quellenbelege ohne Explorer-Modellaufruf."""
    target = tmp_path / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_text("value = 1\n", encoding="utf-8")
    from werkstatt.roles import project_context as exp

    aufgabe = "Pruefe die Ursache in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(
            exp, "run_explorer", create=True,
            side_effect=AssertionError("Explorer-Rolle wurde entfernt"),
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp.collect_project_context(
            state, aufgabe, "test", None,
        )

    assert rc == 0
    evidence = next(
        item for item in state.explorer_context["key_files"]
        if item["file"] == "werkstatt/sample.py"
    )
    assert evidence["source_complete"] is True
    assert state.explorer_context["dispatch"]["role"] == "project_context_tools"
