"""OP-090: Human-Gate zeigt Hinweis bei erschoepfter Reflection."""
from __future__ import annotations

from types import SimpleNamespace


def test_human_gate_body_reflection_erschoepft() -> None:
    """Bei reflection_erschoepft=True: Hinweis im Body."""
    from werkstatt.gates import _human_gate_body
    state = SimpleNamespace()
    state.reflection_erschoepft = True
    body = _human_gate_body(state)
    assert "Reflection erschoepft" in body
    assert "j = Patches behalten" in body
    assert "n = Patches verwerfen" in body


def test_human_gate_body_kein_erschoepft_hinweis() -> None:
    """Ohne Flag: kein Erschoepfungs-Hinweis."""
    from werkstatt.gates import _human_gate_body
    state = SimpleNamespace()
    state.reflection_erschoepft = False
    body = _human_gate_body(state)
    assert "Reflection erschoepft" not in body
