"""Frontend contracts for handing an open gate to the project chat."""
from pathlib import Path


def test_gate_edit_hands_context_to_debug_chat_without_answering_gate() -> None:
    gate = Path("static/gate_panel.js").read_text(encoding="utf-8")
    chat = Path("static/chat.js").read_text(encoding="utf-8")

    assert 'e: "Im Chat debuggen"' in gate
    start = gate.index('var operation = opt === "e"')
    end = gate.index("operation.then", start)
    dispatch = gate[start:end]
    assert "? _debuggeImChat(ctx, g)" in dispatch
    assert ": _sendeAntwort(ctx, g.gate_id, opt)" in dispatch

    assert "run_id: ctx.run_id" in gate
    assert "gate_id: gate.gate_id" in gate
    assert 'window.WerkstattMode.setMode("debug")' in gate
    assert "uebergebeGate(_aktuellesProjekt, kontext)" in gate
    assert "uebergebeGate: uebergebeGate" in chat
    assert "JSON.stringify(kontext, null, 2)" in chat
    assert "_sende(prompt)" in chat


def test_chat_gate_handoff_waits_for_project_history() -> None:
    chat = Path("static/chat.js").read_text(encoding="utf-8")

    assert "zustand.loadPromise = _ladeSessions(projekt)" in chat
    assert "return zustand.loadPromise;" in chat
    assert "var latest = data.summaries.length" in chat
    assert "data.summaries[0].session_id" in chat
    assert "return _wechsleSession(latest);" in chat
    assert "var bereit = zustand.projekt === projekt && zustand.initialisiert" in chat


def test_gate_option_a_never_means_auto_approve() -> None:
    gate = Path("static/gate_panel.js").read_text(encoding="utf-8")
    assert r'a: "a \u2014 Plan anpassen"' in gate
    assert r'a: "a \u2014 Auto"' not in gate
