"""Phase: _phase_review_gate (OP-139 Phase 2b)."""
from __future__ import annotations

import sys as _sys

from werkstatt.audit import audit_safe
from werkstatt.state import RunState


def _phase_review_gate(state: RunState) -> int:
    """OP-168: Human-Gate vor Phase-Review-Loop-Abbruch.

    Wird nach jedem fehlgeschlagenen Phase-Review in
    `_phase_end_reflection` gerufen. Jede Reviewer-Ablehnung verlangt
    eine konkrete menschliche Entscheidung vor der naechsten Aktion.

    Optionen:
      j = Patches behalten; nach letzter Runde Ergebnis uebernehmen
      n = Patches verwerfen, Loop abbrechen
      e = Datei manuell editieren, dann erneut fragen
    Rueckgabe: 0 (j), 1 (n oder EOF). Fail-closed bei EOFError.
    OP-168b: Das Gate wird nach jeder Reject-Runde abgefragt.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    # OP-393: Im headless-Modus (Loop-Subprozess mit --headless) geht das
    # Gate ueber _frage_gate -> gate_bridge (SQLite-Polling, siehe OP-381).
    # Der TTY-Check ist dann nicht sinnvoll (stdin=/dev/null).
    from werkstatt import gates as _gates_mod
    _headless = bool(getattr(_gates_mod, "_HEADLESS", False))
    if not _headless:
        # Non-interactive stdin (pytest, pipe, cron) -> fail-closed.
        # Sonst wirft pytest's DontReadFromInput OSError statt EOFError.
        try:
            _is_tty = _sys.stdin.isatty()
        except (AttributeError, OSError):
            _is_tty = False
        if not _is_tty:
            audit_safe("loop_human_gate_eof",
                       {"gate": "phase_review",
                        "reason": "non_interactive"},
                       pd, pn)
            return 1
    print()
    print("PHASE-REVIEW GATE")
    print("  Reviewer hat die aktuelle Aenderung abgelehnt.")
    print(
        "  j = Patches behalten; Reflection fortsetzen, "
        "nach letzter Runde Ergebnis uebernehmen"
    )
    print("  n = Patches verwerfen, Loop abbrechen")
    print("  e = Datei manuell editieren (dann erneut fragen)")
    _prompt = (
        "\nPHASE-REVIEW GATE\n"
        "  Reviewer hat die aktuelle Aenderung abgelehnt.\n"
        "  j = Patches behalten; Reflection fortsetzen, "
        "nach letzter Runde Ergebnis uebernehmen\n"
        "  n = Patches verwerfen, Loop abbrechen\n"
        "  e = Datei manuell editieren (dann erneut fragen)\n"
        "Deine Wahl [j] behalten / [n] verwerfen / [e] manuell: "
    )
    while True:
        try:
            antwort = _gates_mod._frage_gate(
                "phase_review", _prompt, "jne",
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            audit_safe("loop_human_gate_eof",
                       {"gate": "phase_review"}, pd, pn)
            return 1
        if antwort == "j":
            audit_safe("loop_human_gate_approved",
                       {"gate": "phase_review"}, pd, pn)
            return 0
        if antwort == "n":
            audit_safe("loop_human_gate_rejected",
                       {"gate": "phase_review"}, pd, pn)
            return 1
        if antwort == "e":
            print("Bitte Datei manuell bearbeiten, dann Enter.")
            if not _headless:
                try:
                    input()
                except EOFError:
                    return 1
            # headless: kein Enter-Wait moeglich (stdin=/dev/null) —
            # direkt nochmal fragen.
            continue
        print("Ungueltige Eingabe. Erlaubt: j, n, e.")
