"""Spec: REVIEWER_SYSTEM prueft negative Anweisungen.

Fix B 2026-10-31: Reviewer hatte keinen Auftrags-Treue-Check.
Damit wurde eine Umnummerierung nicht als HIGH-Bug erkannt,
obwohl die Aufgabe "nicht umnummerieren" forderte.
"""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")

import werkstatt.reviewer as rv
from werkstatt.reviewer import REVIEWER_SYSTEM


class TestReviewerAuftragTreue:
    def test_check_ist_im_system_prompt(self) -> None:
        assert "AUFTRAG-TREUE-CHECK" in REVIEWER_SYSTEM

    def test_check_nennt_negative_marker(self) -> None:
        s = REVIEWER_SYSTEM.lower()
        assert "nicht" in s
        assert "kein" in s
        assert "behalte" in s
        assert "erhalte" in s

    def test_check_nennt_umnummerierung(self) -> None:
        assert "umnummerier" in REVIEWER_SYSTEM.lower()

    def test_high_severity_dokumentiert(self) -> None:
        idx = REVIEWER_SYSTEM.find("AUFTRAG-TREUE-CHECK")
        assert idx >= 0
        assert "HIGH" in REVIEWER_SYSTEM[idx:idx + 100]




# ===========================================================================
# OP-164b: Verhaltens-Tests (Wert-Kipp + type-ignore Over-Delivery)
# ===========================================================================


def _mk_state(tmp_path, *, task_desc: str, task_files=None):
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.api_key = "dummy"
    s.baseline_gruen = True
    s.aktuelle_task = {
        "id": "t1",
        "name": "test",
        "description": task_desc,
        "task_files": task_files or ["x.py"],
        "action": "update",
    }
    return s


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


def _run(monkeypatch, tmp_path, *, task_desc, diff, bugs, task_files=None):
    (tmp_path / "x.py").write_text("# stub\n")
    state = _mk_state(tmp_path, task_desc=task_desc, task_files=task_files)
    monkeypatch.setattr(rv, "_get_git_diff", lambda pd, task_files=None: diff)
    monkeypatch.setattr(rv, "ask_llm", lambda *a, **kw: _mk_reply(bugs))
    monkeypatch.setattr(rv, "audit", lambda *a, **kw: None)
    monkeypatch.setattr(rv, "_reviewer_system", lambda *a, **kw: "")
    monkeypatch.setattr(rv, "_reviewer_history_block",
                        lambda s: "", raising=False)
    return rv.run_reviewer(state)


def test_wert_kipp_rename_ok_medium(monkeypatch, tmp_path):
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-auftrag_bereits_erfuellt = True\n"
        "+auftrag_bereits_erfuellt_bestaetigt = True\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": "Wert geändert: auftrag_bereits_erfuellt True->False",
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


def test_wert_kipp_ohne_rename_bleibt_high(monkeypatch, tmp_path):
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-auftrag_bereits_erfuellt = True\n"
        "+auftrag_bereits_erfuellt_bestaetigt = True\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": "Wert geändert: auftrag_bereits_erfuellt True->False",
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc="Fix den Bug in gates.py",
        diff=diff, bugs=bugs,
    )
    assert ok is False


def test_type_ignore_fremdfeld_medium(monkeypatch, tmp_path):
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-reflection_erschoepft = True\n"
        "+reflection_erschoepft = False  # type: ignore[attr-defined]\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": (
            "type: ignore auf reflection_erschoepft hinzugefügt"
        ),
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc="Variable auftrag_bereits_erfuellt umbenennen",
        task_files=["x.py"],
        diff=diff, bugs=bugs,
    )
    assert ok is True


def test_type_ignore_task_feld_bleibt_high(monkeypatch, tmp_path):
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-reflection_erschoepft = True\n"
        "+reflection_erschoepft = False  # type: ignore[attr-defined]\n"
    )
    bugs = [{
        "file": "x.py", "line": 1, "severity": "high",
        "description": "type: ignore auf reflection_erschoepft hinzugefügt",
    }]
    ok = _run(
        monkeypatch, tmp_path,
        task_desc="Fix type-ignore auf reflection_erschoepft in x.py",
        task_files=["x.py"],
        diff=diff, bugs=bugs,
    )
    assert ok is False
