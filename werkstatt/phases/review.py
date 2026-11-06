"""Phase: _phase_review_gate (OP-139 Phase 2b)."""
from __future__ import annotations

import sys as _sys

from werkstatt.audit import audit_safe
from werkstatt.state import RunState


def _phase_review_gate(state: RunState) -> int:
    """OP-168: Human-Gate vor Phase-Review-Loop-Abbruch.

    Wird gerufen, wenn _phase_end_reflection nach 2 Runden
    aufgegeben hat. Verhindert stummes `LOOP FEHLGESCHLAGEN`
    mit dirty Tree (Loop-Test-4, 2026-11-05).

    Optionen:
      j = Patches behalten, Loop fortsetzen (Phase 5 + Commit)
      n = Patches verwerfen, Loop abbrechen
      e = Datei manuell editieren, dann erneut fragen

    Rueckgabe: 0 (j), 1 (n oder EOF). Fail-closed bei EOFError.
    Teilfix: Gate sitzt NACH _phase_end_reflection, nicht
    zwischen den internen Runden. Vollstaendig: OP-168b.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    # OP-168: Non-interactive stdin (pytest, pipe, cron) -> fail-closed.
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
    print("  Phase-Review ist nach 2 Runden erschoepft.")
    print("  j = Patches behalten, Loop fortsetzen (Phase 5 + Commit)")
    print("  n = Patches verwerfen, Loop abbrechen")
    print("  e = Datei manuell editieren (dann erneut fragen)")
    while True:
        try:
            antwort = input("Deine Wahl [j/n/e]: ").strip().lower()
        except EOFError:
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
            try:
                input()
            except EOFError:
                return 1
            continue
        print("Ungueltige Eingabe. Erlaubt: j, n, e.")
