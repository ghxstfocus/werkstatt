"""OP-090: Human-Gate zeigt Hinweis bei erschoepfter Reflection."""
from __future__ import annotations

from types import SimpleNamespace


def test_human_gate_body_reflection_erschoepft() -> None:
    """Bei reflection_erschoepft=True: Hinweis im Body."""
    from werkstatt.gates import _human_gate_body
    state = SimpleNamespace(architect_prosa="")
    state.reflection_erschoepft = True
    body = _human_gate_body(state)
    assert "Reflection erschoepft" in body
    assert "j = Patches behalten" in body
    assert "n = Patches verwerfen" in body


def test_human_gate_body_kein_erschoepft_hinweis() -> None:
    """Ohne Flag: kein Erschoepfungs-Hinweis."""
    from werkstatt.gates import _human_gate_body
    state = SimpleNamespace(architect_prosa="")
    state.reflection_erschoepft = False
    body = _human_gate_body(state)
    assert "Reflection erschoepft" not in body


def test_plan_gate_fail_closed_bei_ungueltiger_antwort() -> None:
    """OP-093: 3x ungueltig → return 1 (kein Endlos-Retry)."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from werkstatt.gates import _human_gate_plan

    state = SimpleNamespace(
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
        rc = _human_gate_plan(state, auto_approve=False)
    assert rc == 1


def test_human_gate_plan_revidierter_kontext(monkeypatch, tmp_path):
    """Nachbesserung: kontext='revidierter_plan' zeigt klareren Prompt."""
    from types import SimpleNamespace
    from unittest.mock import patch

    from werkstatt.gates import _human_gate_plan

    state = SimpleNamespace(
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
        rc = _human_gate_plan(state, auto_approve=False, kontext="revidierter_plan")
    assert rc == 1
    assert any("REVIDIERTER PLAN" in p for p in captured), f"captured={captured}"
    assert any("keine weitere Reflection" in p for p in captured)
