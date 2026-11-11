"""OP-090: Human-Gate zeigt Hinweis bei erschoepfter Reflection."""
from __future__ import annotations

import sys
from pathlib import Path

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def test_human_gate_body_reflection_erschoepft() -> None:
    """Bei reflection_erschoepft=True: Hinweis im Body."""
    from werkstatt.gates import _human_gate_body
    state = mk_state(architect_prosa="", reflection_erschoepft=True)
    body = _human_gate_body(state)
    assert "Reflection erschoepft" in body
    assert "j = Patches behalten" in body
    assert "n = Patches verwerfen" in body


def test_human_gate_body_kein_erschoepft_hinweis() -> None:
    """Ohne Flag: kein Erschoepfungs-Hinweis."""
    from werkstatt.gates import _human_gate_body
    state = mk_state(architect_prosa="", reflection_erschoepft=False)
    body = _human_gate_body(state)
    assert "Reflection erschoepft" not in body


def test_plan_gate_fail_closed_bei_ungueltiger_antwort() -> None:
    """OP-093: 3x ungueltig → return 1 (kein Endlos-Retry)."""
    from unittest.mock import patch

    from werkstatt.gates import _human_gate_plan

    state = mk_state(
        project_dir="/tmp",
        project_name="test",
        tasks=[{"id": "t1"}],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
    )
    with patch.dict("os.environ", {"WERKSTATT_IN_TEST": "0"}), \
         patch("builtins.input",
               side_effect=["x", "y", "z", "sollte_nicht_kommen"]), \
         patch("werkstatt.gates.audit"):
        rc = _human_gate_plan(state, )
    assert rc == 1


def test_human_gate_plan_revidierter_kontext(monkeypatch, tmp_path):
    """Nachbesserung: kontext='revidierter_plan' zeigt klareren Prompt."""
    from unittest.mock import patch

    from werkstatt.gates import _human_gate_plan

    state = mk_state(
        project_dir=str(tmp_path),
        project_name="probe",
        tasks=[{"id": "t1"}],
        tests=[], akzeptanzkriterien=[], phasen=[],
    )
    captured = []
    def _fake_input(prompt=""):
        captured.append(prompt)
        return "n"
    with patch.dict("os.environ", {"WERKSTATT_IN_TEST": "0"}), \
         patch("builtins.input", side_effect=_fake_input), \
         patch("werkstatt.gates.audit"):
        rc = _human_gate_plan(state, kontext="revidierter_plan")
    assert rc == 1
    assert any("REVIDIERTER PLAN" in p for p in captured), f"captured={captured}"
    assert any("keine weitere Reflection" in p for p in captured)


def test_plan_gate_ui_options_match_editability(monkeypatch, tmp_path) -> None:
    from werkstatt import gates, render

    captured = []

    def fake_gate(_kind, _prompt, optionen="jna", timeout=None):
        captured.append(optionen)
        return "j"

    monkeypatch.setenv("WERKSTATT_IN_TEST", "0")
    monkeypatch.setattr(gates, "_frage_gate", fake_gate)
    monkeypatch.setattr(gates, "audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(render, "plan", lambda *args, **kwargs: None)

    state = mk_state(
        project_dir=str(tmp_path),
        project_name="probe",
        tasks=[{"id": "t1"}],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
    )
    assert gates._human_gate_plan(state, kontext="revidierter_plan") == 0
    assert captured[-1] == "jn"

    assert gates._human_gate_plan(state) == 0
    assert captured[-1] == "jna"


def test_input_is_confined_to_shared_gate_adapter() -> None:
    import ast
    from pathlib import Path

    from werkstatt import gates

    tree = ast.parse(Path(gates.__file__).read_text(encoding="utf-8"))
    input_functions = {
        fn.name
        for fn in ast.walk(tree)
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "input"
            for node in ast.walk(fn)
        )
    }
    assert input_functions == {"_frage_gate"}


def test_plan_edit_wait_uses_gate_bridge_in_headless(monkeypatch, tmp_path) -> None:
    from werkstatt import gates, render

    answers = iter(("a", "j", "j"))
    calls = []

    def fake_gate(kind, _prompt, optionen="jna", timeout=None):
        calls.append((kind, optionen))
        return next(answers)

    monkeypatch.setenv("WERKSTATT_IN_TEST", "0")
    monkeypatch.setattr(gates, "_HEADLESS", True)
    monkeypatch.setattr(gates, "_frage_gate", fake_gate)
    monkeypatch.setattr(gates, "audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(render, "plan", lambda *args, **kwargs: None)
    state = mk_state(
        project_dir=str(tmp_path),
        project_name="probe",
        tasks=[{"id": "t1"}],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
    )

    assert gates._human_gate_plan(state) == 0
    assert calls == [("plan", "jna"), ("plan_edit_continue", "j"), ("plan", "jna")]


def test_adr_mini_prompt_uses_gate_bridge_in_headless(monkeypatch, tmp_path) -> None:
    from werkstatt import gates

    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    calls = []

    def fake_gate(kind, _prompt, optionen="jna", timeout=None):
        calls.append((kind, optionen))
        return "n"

    monkeypatch.setenv("WERKSTATT_ADR_MINI", "1")
    monkeypatch.setenv("WERKSTATT_IN_TEST", "0")
    monkeypatch.setattr(gates, "_HEADLESS", True)
    monkeypatch.setattr(gates, "_frage_gate", fake_gate)
    monkeypatch.setattr(gates, "audit", lambda *args, **kwargs: None)
    state = mk_state(project_dir=str(tmp_path), project_name="probe")

    assert gates._adr_mini_phase(state) is True
    assert calls == [("adr_mini", "jn")]
