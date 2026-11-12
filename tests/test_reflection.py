"""Tests fuer den Reflection Circuit-Breaker (OP-089).

Prueft, dass `_reflection_loop` bei fehlendem Fortschritt (konstanter
Diff-Hash und konstante Bug-Signaturen) fruehzeitig abbricht und den
audit-Event `reflection_no_progress` emittiert, waehrend wechselnde
Hashes den Loop bis `max_runden` weiterlaufen lassen.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from werkstatt import reflection

# Import von factories: tests/ ist kein Package, deshalb sys.path.
_here = Path(__file__).parent
if str(_here) not in _sys.path:
    _sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402

_VERIFY_ERRORS = [
    {
        "stage_id": "pytest_changed",
        "datei": "tests/x.py",
        "text": "FAILED tests/x.py::test_y - AssertionError: boom",
    }
]


def _make_state(tmp_path):
    """Spec-State fuer _reflection_loop Circuit-Breaker (OP-174 P2).

    Baut ueber mk_state() — vollstaendiger RunState mit Defaults.
    Nur echte RunState-Felder werden ueberschrieben:
    - api_key, project_dir, project_name
    - last_verify_errors (das Signal fuer Circuit-Breaker-Test)
    - patches, reviewer_bugs (leer, aber explizit)

    Zombie-Felder aus der alten SimpleNamespace-Version entfernt
    (2026-11-06 gemessen):
    - phase, runde, reflection_runden, reflection_errors:
      werden von _reflection_loop nicht gelesen
    - task (statt aktuelle_task): _reflection_loop liest
      aktuelle_task als dict, nicht "task"
    - plan, phase_state, messages, history: nirgends gelesen
    Alle 9 waren Attrappen ohne Spec-Relevanz.
    """
    return mk_state(
        api_key="x",
        project_dir=tmp_path,
        project_name="t",
        last_verify_errors=list(_VERIFY_ERRORS),
        patches=[],
        reviewer_bugs=[],
    )


def _setup_mocks(monkeypatch):
    run_builder = MagicMock(return_value=True)
    apply_patches = MagicMock(return_value=True)
    verify_patches = MagicMock(return_value=False)
    ruff_fix = MagicMock(return_value=None)
    audit_mock = MagicMock()
    log_line = MagicMock(return_value=None)
    run_reviewer = MagicMock(return_value=True)
    task_ende = MagicMock(return_value=None)
    human_gate = MagicMock(return_value=True)

    import werkstatt.roles.builder as _builder
    monkeypatch.setattr(_builder, "run_builder", run_builder, raising=False)
    monkeypatch.setattr(reflection, "run_builder", run_builder, raising=False)
    monkeypatch.setattr(
        reflection, "_apply_patches_with_diagnose", apply_patches, raising=False
    )
    monkeypatch.setattr(reflection, "_verify_patches", verify_patches, raising=False)
    monkeypatch.setattr(reflection, "_ruff_fix_changed", ruff_fix, raising=False)
    monkeypatch.setattr(reflection, "audit", audit_mock, raising=False)
    monkeypatch.setattr(reflection, "log_line", log_line, raising=False)
    monkeypatch.setattr(reflection, "run_reviewer", run_reviewer, raising=False)
    monkeypatch.setattr(reflection, "_task_ende", task_ende, raising=False)
    monkeypatch.setattr(reflection, "_human_gate", human_gate, raising=False)

    return SimpleNamespace(
        run_builder=run_builder,
        apply_patches=apply_patches,
        verify_patches=verify_patches,
        ruff_fix=ruff_fix,
        audit=audit_mock,
        log_line=log_line,
        run_reviewer=run_reviewer,
        task_ende=task_ende,
        human_gate=human_gate,
    )


def test_reflection_no_progress_abbruch(tmp_path, monkeypatch):
    state = _make_state(tmp_path)
    mocks = _setup_mocks(monkeypatch)
    monkeypatch.setattr(
        reflection, "_diff_hash_for_state", lambda s: "same_hash", raising=False
    )

    result = reflection._reflection_loop(state, max_runden=5)

    assert result is False
    assert mocks.run_builder.call_count <= 2
    assert any(
        call.args and call.args[0] == "reflection_no_progress"
        for call in mocks.audit.call_args_list
    )


def test_reflection_fortschritt_kein_abbruch(tmp_path, monkeypatch):
    """Spec (OP-175-B-Update): echter Fortschritt = anderer Hash UND
    andere verify-Fehler. Vor Loop-Test-6 reichte "anderer Hash"
    allein als Fortschritts-Signal -- das war falsch (Builder baut
    neuen Patch, Fehler bleibt -> keine Reparatur). Neuer Vertrag:
    wechselnde Fehler + wechselnder Hash = kein Abbruch."""
    state = _make_state(tmp_path)
    mocks = _setup_mocks(monkeypatch)
    hashes = iter(["h1", "h2", "h3", "h4"])
    monkeypatch.setattr(
        reflection, "_diff_hash_for_state", lambda s: next(hashes), raising=False
    )

    _runde = [0]
    def _verify_mit_wechselnden_errors(st, phase=None):
        _runde[0] += 1
        st.last_verify_errors = [
            {
                "stage_id": "pytest_changed",
                "datei": "tests/x.py",
                "text": f"FAILED tests/x.py::test_y - AssertionError: boom{_runde[0]}",
            }
        ]
        return False
    monkeypatch.setattr(
        reflection, "_verify_patches",
        _verify_mit_wechselnden_errors, raising=False,
    )

    result = reflection._reflection_loop(state, max_runden=3)

    assert result is False
    assert mocks.run_builder.call_count == 3


def test_targeted_recovery_stops_after_affected_stages_pass(
    tmp_path, monkeypatch,
):
    state = _make_state(tmp_path)
    state.patches = [{"file": "app.py", "old_string": "old", "new_string": "new"}]
    mocks = _setup_mocks(monkeypatch)
    applied = MagicMock(return_value=(1, []))
    monkeypatch.setattr(
        reflection, "_apply_patches_with_diagnose", applied, raising=False,
    )
    verifications = []
    verify_results = iter([False, True])

    def verify_selected(st, phase=None, stage_ids=None):
        verifications.append((phase, stage_ids))
        ok = next(verify_results)
        st.last_verify_errors = [] if ok else ["pytest_regression: still failing"]
        return ok

    monkeypatch.setattr(
        reflection, "_verify_patches", verify_selected, raising=False,
    )
    mocks.run_builder.side_effect = lambda st: setattr(
        st, "patches", [{"file": "app.py", "old_string": "old", "new_string": "new"}],
    ) or True

    result = reflection._reflection_loop(
        state,
        error_context="pytest_regression failed",
        phase="phase_end",
        verify_stage_ids={"pytest_regression"},
    )

    assert result is True
    assert mocks.run_builder.call_count == 1
    assert verifications == [
        ("phase_end", {"pytest_regression"}),
        ("phase_end", {"pytest_regression"}),
    ]
