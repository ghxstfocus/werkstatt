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
