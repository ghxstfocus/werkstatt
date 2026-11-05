"""OP-169: Commit-Subject darf OP-NNN nicht doppeln.

Live-Beleg Loop-Test-4: `fix(werkstatt): OP-145: ### OP-145: Namens-Drift`
(3x in Folge). Ursache: _build_commit_subject prueft
`_line.upper().startswith(op_nnn.upper())`, aber _line beginnt mit
`### OP-145: ...` — der Prefix-Check greift nicht.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.committer import _build_commit_subject


def test_markdown_header_wird_gestrippt():
    aufgabe = "### OP-145: Namens-Drift `auftrag_bereits_erfuellt` (ghost)"
    subj = _build_commit_subject(aufgabe, "OP-145")
    assert subj.startswith("OP-145: ")
    assert "### OP-145" not in subj
    assert subj.count("OP-145") == 1


def test_ohne_markdown_header_bleibt_unveraendert():
    aufgabe = "OP-145: Namens-Drift"
    subj = _build_commit_subject(aufgabe, "OP-145")
    assert subj == "OP-145: Namens-Drift"


def test_ohne_op_nnn_header_wird_trotzdem_gestrippt():
    aufgabe = "### irgendein Aufgabentext"
    subj = _build_commit_subject(aufgabe, None)
    assert "###" not in subj
    assert subj == "irgendein Aufgabentext"
