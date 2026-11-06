"""OP-164: Reviewer versteht Rename-Aufgaben.

Wenn der Reviewer einen HIGH-Bug "Bestehende Zuweisung/Funktion X
entfernt" meldet, der Diff aber im selben Hunk eine +-Zeile mit
einem anderen Identifier zeigt, ist das ein Rename, kein Entfernen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")

import werkstatt.reviewer as rv
from werkstatt.state import RunState

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def _mk_state(tmp_path, *, task_desc: str) -> RunState:
    """Spec-State fuer Reviewer-Rename (OP-174 P3).

    Alle Felder in RunState deklariert. mk_state fail-loud bei
    Tippfehler in Feldnamen. SimpleNamespace-Import bleibt fuer
    Mock-Bundles (ns = SimpleNamespace() im Test).
    """
    return mk_state(
        project_dir=tmp_path,
        project_name="test",
        api_key="dummy",
        baseline_gruen=True,
        aktuelle_task={
            "id": "t1",
            "name": "rename",
            "description": task_desc,
            "task_files": ["x.py"],
            "action": "update",
        },
    )


def _mk_reply(bugs):
    ns = SimpleNamespace()
    ns.ok = True
    ns.error = ""
    ns.content = json.dumps({
        "approved": not any(b.get("severity") == "high" for b in bugs),
        "bugs": bugs,
        "summary": "test",
    })
    return ns


def _run(monkeypatch, tmp_path, *, task_desc, diff, bugs):
    (tmp_path / "x.py").write_text("# stub\n")
    state = _mk_state(tmp_path, task_desc=task_desc)
    monkeypatch.setattr(rv, "_get_git_diff", lambda pd, task_files=None: diff)
    monkeypatch.setattr(rv, "ask_llm", lambda *a, **kw: _mk_reply(bugs))
    monkeypatch.setattr(rv, "audit", lambda *a, **kw: None)
    monkeypatch.setattr(rv, "_reviewer_system", lambda *a, **kw: "")
    monkeypatch.setattr(rv, "_reviewer_history_block",
                        lambda s: "", raising=False)
    return rv.run_reviewer(state)


def test_rename_ok(monkeypatch, tmp_path):
    """(a) Rename-OK: -alt +neu im selben Hunk -> medium, approved."""
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,3 +1,3 @@\n"
        "-auftrag_bereits_erfuellt = True\n"
        "+auftrag_bereits_erfuellt_bestaetigt = True\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": (
            "Bestehende Zuweisung auftrag_bereits_erfuellt entfernt."
        ),
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc=(
            "Variable auftrag_bereits_erfuellt umbenennen zu "
            "auftrag_bereits_erfuellt_bestaetigt"
        ),
        diff=diff, bugs=bugs,
    )
    assert ok is True


def test_rename_fehler(monkeypatch, tmp_path):
    """(b) Rename-Fehler: -alt ohne +neu im selben Hunk -> HIGH."""
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,3 +1,2 @@\n"
        "-auftrag_bereits_erfuellt = True\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": (
            "Bestehende Zuweisung auftrag_bereits_erfuellt entfernt."
        ),
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc="Variable auftrag_bereits_erfuellt umbenennen",
        diff=diff, bugs=bugs,
    )
    assert ok is False


def test_kein_rename_kontext(monkeypatch, tmp_path):
    """(c) Kein Rename-Kontext: HIGH bleibt HIGH."""
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,3 +1,3 @@\n"
        "-alter_wert = 1\n"
        "+neuer_wert = 2\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": "Bestehende Zuweisung alter_wert entfernt.",
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc="Refactor: Struktur verbessern",
        diff=diff, bugs=bugs,
    )
    assert ok is False
