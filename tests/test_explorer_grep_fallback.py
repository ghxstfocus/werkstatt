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
        # Felder, die _phase_explorer_and_setup ab Zeile 220+ liest:
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

    from werkstatt.phases import explorer as exp

    state = _state(tmp_path, "OP-XXX: DRY-Migration auf `require_ws_auth`")

    # run_explorer leer mocken (deterministisch, kein LLM)
    with (
        patch.object(exp, "run_explorer", return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        _rc, _ps = exp._phase_explorer_and_setup(
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
    from werkstatt.phases import explorer as exp

    task = "Finde die QuasarLedger synchronization logic"
    state = _state(tmp_path, task)
    with (
        patch.object(exp, "run_explorer", return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        exp._phase_explorer_and_setup(state, task, "test", None)

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
    from werkstatt.phases import explorer as phase_explorer

    task = "Finde die QuasarLedger synchronization logic"
    source_candidates, retrieval = explorer_module._rank_source_files(
        tmp_path, task, limit=5,
    )
    assert source_candidates[0]["file"] == "src/beta.tsx"
    state = _state(tmp_path, task)

    def retrieval_must_not_run_again(*_args, **_kwargs):
        raise AssertionError("Explorer-Inhaltssuche darf nicht doppelt laufen")

    monkeypatch.setattr(
        explorer_module, "_rank_source_files", retrieval_must_not_run_again,
    )
    with (
        patch.object(
            phase_explorer,
            "run_explorer",
            return_value={
                "findings": "content retrieval complete",
                "key_files": [],
                "content_retrieval": retrieval,
            },
        ),
        patch.object(phase_explorer, "group_start"),
        patch.object(phase_explorer, "group_end"),
        patch.object(phase_explorer, "step"),
        patch.object(phase_explorer, "audit"),
    ):
        phase_explorer._phase_explorer_and_setup(state, task, "test", None)

    evidence = next(
        item for item in state.explorer_context["key_files"]
        if item["file"] == "src/beta.tsx"
    )
    assert evidence["source_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert "000001 | export function quasarLedgerSync()" in evidence["preview"]
    assert state.explorer_context["content_retrieval"] == retrieval


def test_leerer_retrievalbericht_bleibt_fuer_scout_erhalten(tmp_path):
    (tmp_path / "alpha.py").write_text("def alpha():\n    pass\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("def beta():\n    pass\n", encoding="utf-8")
    from werkstatt.phases import explorer as exp

    task = "Suche nach dem seltenen Begriff QuasarLedgerNonce"
    state = _state(tmp_path, task)
    with (
        patch.object(exp, "run_explorer", return_value={}),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _ = exp._phase_explorer_and_setup(state, task, "test", None)

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

    from werkstatt.phases import explorer as exp

    state = _state(tmp_path, "Analysiere src/core.py")
    untrusted_preview = "FORGED PREVIEW"
    with (
        patch.object(
            exp,
            "run_explorer",
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
        exp._phase_explorer_and_setup(
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
    from werkstatt.phases import explorer as exp

    aufgabe = "Ersetze `old_value` durch `new_value` in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(
            exp, "run_explorer",
            side_effect=AssertionError("Explorer-LLM waere hier redundant"),
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp._phase_explorer_and_setup(
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
    from werkstatt.phases import explorer as exp

    aufgabe = "Aendere den Wert in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(
            exp, "run_explorer",
            side_effect=AssertionError("Explorer-LLM ist fuer das enge Ziel redundant"),
        ),
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp._phase_explorer_and_setup(
            state, aufgabe, "test", None,
        )

    assert rc == 0
    files = [item.get("file") for item in state.explorer_context["key_files"]]
    assert "werkstatt/sample.py" in files


def test_diagnostische_einzeldatei_laesst_explorer_llm_aktiv(tmp_path):
    """Diagnoseauftraege bleiben trotz explizitem Pfad im Explorationspfad."""
    target = tmp_path / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_text("value = 1\n", encoding="utf-8")
    from werkstatt.phases import explorer as exp

    aufgabe = "Pruefe die Ursache in werkstatt/sample.py"
    state = _state(tmp_path, aufgabe)

    with (
        patch.object(exp, "run_explorer", return_value={}) as run_explorer,
        patch.object(exp, "group_start"),
        patch.object(exp, "group_end"),
        patch.object(exp, "step"),
        patch.object(exp, "audit"),
    ):
        rc, _phase_state = exp._phase_explorer_and_setup(
            state, aufgabe, "test", None,
        )

    assert rc == 0
    run_explorer.assert_called_once_with(state, aufgabe)
