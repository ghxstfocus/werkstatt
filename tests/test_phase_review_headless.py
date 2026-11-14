"""OP-393: _phase_review_gate im headless-Modus -> _frage_gate statt input.

Live-Bug 2026-11-10 10:23: Loop-Subprozess (--headless) crasht am
Phase-Review-Gate mit loop_human_gate_eof, weil stdin=/dev/null
nicht-TTY ist. Fix: headless -> _frage_gate -> gate_bridge.
"""
from __future__ import annotations

import sys
from pathlib import Path

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402, I001
from werkstatt import gate_bridge, gates as gates_mod  # noqa: E402
from werkstatt.phases import review as review_mod  # noqa: E402


def _mk_state():
    return mk_state(project_dir="/tmp", project_name="test")


def test_headless_nutzt_frage_gate_und_liefert_j(monkeypatch):
    """Headless -> _frage_gate('phase_review', ...) wird gerufen, 'j' -> 0."""
    from werkstatt import gates as gates_mod
    from werkstatt.phases.review import _phase_review_gate

    monkeypatch.setattr(gates_mod, "_HEADLESS", True)

    aufrufe: list[tuple] = []

    def _fake_frage(kind, prompt, optionen="jna", **_kwargs):
        aufrufe.append((kind, optionen))
        return "j"

    monkeypatch.setattr(gates_mod, "_frage_gate", _fake_frage)

    rc = _phase_review_gate(_mk_state())
    assert rc == 0, f"rc={rc}, aufrufe={aufrufe}"
    assert len(aufrufe) == 1
    assert aufrufe[0][0] == "phase_review"
    assert aufrufe[0][1] == "jne"


def test_headless_n_liefert_1(monkeypatch):
    from werkstatt import gates as gates_mod
    from werkstatt.phases.review import _phase_review_gate

    monkeypatch.setattr(gates_mod, "_HEADLESS", True)
    monkeypatch.setattr(gates_mod, "_frage_gate", lambda k, p, o="jna", **_kwargs: "n")

    assert _phase_review_gate(_mk_state()) == 1


def test_headless_a_erteilt_keine_freigabe(monkeypatch):
    from werkstatt import gates as gates_mod
    from werkstatt.phases import review as review_mod
    from werkstatt.phases.review import _phase_review_gate

    monkeypatch.setattr(gates_mod, "_HEADLESS", True)
    antworten = iter(["a", "j"])
    aufrufe: list[tuple] = []
    audit_events: list[tuple] = []

    def _frage(kind, prompt, optionen="jna", **_kwargs):
        aufrufe.append((kind, optionen))
        return next(antworten)

    monkeypatch.setattr(gates_mod, "_frage_gate", _frage)
    monkeypatch.setattr(
        review_mod, "audit_safe",
        lambda kind, payload, *_args: audit_events.append((kind, payload)),
    )

    rc = _phase_review_gate(_mk_state())
    assert rc == 0
    assert aufrufe == [("phase_review", "jne"), ("phase_review", "jne")]
    assert not any(kind == "loop_human_gate_auto" for kind, _ in audit_events)


def test_headless_eof_liefert_1(monkeypatch):
    """_frage_gate wirft EOFError (Gate-Timeout o.ae.) -> 1."""
    from werkstatt import gates as gates_mod
    from werkstatt.phases.review import _phase_review_gate

    monkeypatch.setattr(gates_mod, "_HEADLESS", True)

    def _raise(*a, **kw):
        raise EOFError

    monkeypatch.setattr(gates_mod, "_frage_gate", _raise)
    assert _phase_review_gate(_mk_state()) == 1


def test_headless_phase_review_opens_and_waits_on_bridge(monkeypatch):
    monkeypatch.setattr(gates_mod, "_HEADLESS", True)
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "run-review")
    monkeypatch.setattr(review_mod, "audit_safe", lambda *args: None)
    opened = []
    waited = []

    def signal_open(run_id, gate_id, prompt, optionen, typ="jna", project="werkstatt"):
        opened.append((run_id, gate_id, prompt, optionen, typ, project))

    def wait(run_id, gate_id, **_kwargs):
        waited.append((run_id, gate_id))
        return "j"

    monkeypatch.setattr(gate_bridge, "signal_open", signal_open)
    monkeypatch.setattr(gate_bridge, "wait", wait)

    assert review_mod._phase_review_gate(_mk_state()) == 0
    assert len(opened) == 1
    run_id, gate_id, _prompt, optionen, typ, project = opened[0]
    assert run_id == "run-review"
    assert gate_id.startswith("phase_review-")
    assert optionen == "jne"
    assert typ == "jna"
    assert project == "test"
    assert waited == [(run_id, gate_id)]
