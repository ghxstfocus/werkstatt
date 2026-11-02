"""OP-067: pytest_changed feuert in Reflection-Runden.

Der Runden-Patches-Kontext (state.patches_aktuell_runde) wird von
_setze_runde_patches in _reflection_loop gesetzt, damit
_expand_cmd_placeholders {changed_test_files} auch dann fuellen kann,
wenn state.patches (Primaerquelle) leer ist.
"""
from pathlib import Path

from werkstatt.state import RunState
from werkstatt.verify import _expand_cmd_placeholders


def _make_state() -> RunState:
    """Minimaler RunState mit den 12 Pflichtfeldern."""
    return RunState(
        block_id="test-op-067",
        aufgabe="test",
        start_ts="2026-11-02T00:00:00",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={},
        project_dir=Path("/opt/werkstatt"),
    )


def test_pytest_changed_feat_in_reflection():
    state = _make_state()
    state.patches = []

    # Positiv-Fall: Test-File in patches_aktuell_runde
    state.patches_aktuell_runde = [
        {"file": "tests/test_pytest_changed_reflection.py"}
    ]
    result = _expand_cmd_placeholders(
        ["pytest", "{changed_test_files}", "-q"], state, state.project_dir,
    )
    assert result is not None, "sollte Liste liefern"
    assert any("test_pytest_changed_reflection" in tok for tok in result), \
        f"erwartet test-file in {result}"

    # Negativ-Fall: nur Nicht-Test-Datei
    state.patches_aktuell_runde = [{"file": "werkstatt/verify.py"}]
    result = _expand_cmd_placeholders(
        ["pytest", "{changed_test_files}", "-q"], state, state.project_dir,
    )
    assert result is None, \
        "kein {changed_test_files} -> Stage wird uebersprungen"

    # Regression: Primaerpfad ueber state.patches funktioniert weiter
    state.patches_aktuell_runde = []
    state.patches = [{"file": "tests/test_pytest_changed_reflection.py"}]
    result = _expand_cmd_placeholders(
        ["pytest", "{changed_test_files}", "-q"], state, state.project_dir,
    )
    assert result is not None
    assert any("test_pytest_changed_reflection" in tok for tok in result)
