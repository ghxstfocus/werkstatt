"""OP-062b: Human-Gate zeigt Scout/Architect-Plan, Reviewer-Bugs, Reflexionen.

Live-Beleg 15:16 OP-002b3: Human-Gate zeigte nur Task-Status + Diff-Stat.
Der Mensch am Gate sah nicht:
- Architect-Plan (state.architect_prosa)
- Reviewer-Bugs aus dem Task-Reviewer (4x bei t2)
- Reflexions-Runden (2 Runden bei t2)
- Phase-End-Review-Bugs (3x rejected)

Diese Informationen stehen im Audit-Log, aber nicht im Render.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.gates import _human_gate_body
from werkstatt.state import RunState


def _mk_state(tmp_path: Path) -> RunState:
    (tmp_path / ".werkstatt").mkdir(parents=True, exist_ok=True)
    s = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    return s


def test_human_gate_body_zeigt_architect_plan(tmp_path: Path) -> None:
    """Architect-Prosa landet im Human-Gate-Body."""
    s = _mk_state(tmp_path)
    s.architect_prosa = (
        "## 1. Was ist das Problem?\n"
        "Der Ist-Zustand von core/inventory/repository.py pflegt "
        "devices.last_ip bereits.\n"
    )
    body = _human_gate_body(s)
    assert "Architect-Plan" in body or "Architect" in body, (
        f"Kein Architect-Block; body={body[:500]!r}"
    )
    assert "core/inventory/repository.py" in body


def test_human_gate_body_marker_als_plan_quelle(tmp_path: Path) -> None:
    """Scout-Marker statt Prosa: klar als Scout-Plan kennzeichnen."""
    s = _mk_state(tmp_path)
    s.architect_prosa = "[atomarer Plan vom Scout]"
    body = _human_gate_body(s)
    assert "Scout" in body, (
        f"Scout-Marker nicht erkannt; body={body[:500]!r}"
    )


def test_human_gate_body_zeigt_reviewer_bugs(tmp_path: Path) -> None:
    """Letzte Reviewer-Bugs mit severity, file, description."""
    s = _mk_state(tmp_path)
    s.reviewer_bugs_history = [
        [
            {"severity": "high",
             "file": "core/inventory/repository.py",
             "description": "INSERT-Pfad schreibt device_history, Task sagt kein History"},
            {"severity": "medium",
             "file": "core/inventory/repository.py",
             "description": "try/except deckt nicht device_seen-INSERT"},
        ],
    ]
    body = _human_gate_body(s)
    assert "Reviewer" in body or "Bugs" in body, (
        f"Kein Reviewer-Bugs-Block; body={body[:500]!r}"
    )
    assert "INSERT-Pfad" in body, (
        f"Bug-description fehlt; body={body[:500]!r}"
    )
    assert "core/inventory/repository.py" in body


def test_human_gate_body_zeigt_reflexionen(tmp_path: Path) -> None:
    """Reflexions-Runden: Runde, patches_applied, offene bugs."""
    s = _mk_state(tmp_path)
    s.reflection_history = [
        {"runde": 1, "patches_applied": 2,
         "verify_errors": [],
         "reviewer_bugs": [{"severity": "high"}]},
        {"runde": 2, "patches_applied": 0,
         "verify_errors": [],
         "reviewer_bugs": [{"severity": "high"}]},
    ]
    body = _human_gate_body(s)
    assert "Reflexion" in body or "Runde" in body, (
        f"Kein Reflexions-Block; body={body[:500]!r}"
    )
    assert "2 Patches" in body or "patches" in body.lower()


def test_human_gate_body_leer_wenn_state_leer(tmp_path: Path) -> None:
    """Ohne State-Infos: leerer String (kein Placeholder-Muell)."""
    s = _mk_state(tmp_path)
    body = _human_gate_body(s)
    assert body == "" or not body.strip(), (
        f"Leerer State ergibt muell-Text: {body!r}"
    )


# ═══════════════════════════════════════════════════════════════
# OP-062c: Bug-Sync, task_id-Prefix, Hunk-Summary, Runner-Fix
# ═══════════════════════════════════════════════════════════════


def test_human_gate_body_markiert_behobene_bugs(tmp_path: Path) -> None:
    """Letzter Reviewer-Call grün (state.reviewer_bugs leer), aber
    History gefüllt -> Bugs als 'vermutlich behoben' markieren."""
    s = _mk_state(tmp_path)
    s.reviewer_bugs = []  # letzter Call approvte
    s.reviewer_bugs_history = [
        [
            {"severity": "high",
             "file": "core/inventory/repository.py",
             "description": "Diff entfernt Guards 'if not ip'"},
        ],
    ]
    body = _human_gate_body(s)
    # Bug-Beschreibung soll sichtbar sein, aber klar als behoben.
    assert "if not ip" in body
    _lower = body.lower()
    assert (
        "vermutlich behoben" in _lower
        or "letzter call gruen" in _lower
        or "behoben" in _lower
    ), f"Bug nicht als behoben markiert; body={body[:600]!r}"


def test_human_gate_body_reflexion_mit_task_id(tmp_path: Path) -> None:
    """Reflexions-Eintrag mit task_id zeigt 't2 Runde 1' statt 'Runde 1'."""
    s = _mk_state(tmp_path)
    s.reflection_history = [
        {"runde": 1, "patches_applied": 2, "task_id": "t2",
         "verify_errors": [], "reviewer_bugs": []},
        {"runde": 2, "patches_applied": 0, "task_id": "t2",
         "verify_errors": [], "reviewer_bugs": [{"severity": "high"}]},
        {"runde": 1, "patches_applied": 1, "task_id": "t3",
         "verify_errors": [], "reviewer_bugs": []},
    ]
    body = _human_gate_body(s)
    assert "t2 Runde 1" in body or "t2: Runde 1" in body, (
        f"task_id-Prefix fehlt; body={body[:600]!r}"
    )
    assert "t3 Runde 1" in body or "t3: Runde 1" in body


def test_diff_hunk_summary_zeigt_kontext() -> None:
    """_diff_hunk_summary liefert pro Datei Hunk-Header (kompakt)."""
    from werkstatt.gates import _diff_hunk_summary

    diff = (
        "diff --git a/foo.py b/foo.py\n"
        "index abc..def 100644\n"
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -10,5 +10,7 @@ def bar():\n"
        " context\n"
        "+neu\n"
        " context\n"
        "@@ -20,3 +22,4 @@ def baz():\n"
        " context\n"
        "+neu2\n"
        "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
        "index 111..222 100644\n"
        "--- a/tests/test_foo.py\n"
        "+++ b/tests/test_foo.py\n"
        "@@ -1,2 +1,3 @@\n"
        " import foo\n"
        "+import bar\n"
    )
    summary = _diff_hunk_summary(diff)
    assert "foo.py" in summary
    assert "bar()" in summary or "@@" in summary
    assert "baz()" in summary or "@@" in summary
    # Kein Roh-Diff: keine '+neu'-Zeilen, keine 'context'-Zeilen
    assert "+neu\n" not in summary
    assert "context\n" not in summary


def test_phase_end_approved_setzt_reviewer_bugs_leer(
    tmp_path: Path, monkeypatch,
) -> None:
    """Nach erfolgreichem Phase-End-Review: alte Bugs wegräumen.

    Sonst zeigt das Human-Gate HIGH-Bugs, die laengst behoben sind.
    """
    from werkstatt.reviewer import run_phase_end_review

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("x = 1\n")
    s = _mk_state(tmp_path)
    s.api_key = "dummy"
    s.tasks = [{"id": "t1", "task_files": ["core/x.py"], "status": "done"}]
    s.reviewer_bugs = [
        {"severity": "high", "file": "core/x.py",
         "description": "alter Bug aus frueherer Runde"},
    ]

    # LLM-Antwort: approved, keine Bugs.
    def _fake_ask(*args, **kwargs):
        from werkstatt.agent import LLMReply
        return LLMReply(
            ok=True, error="",
            content='{"approved": true, "bugs": [], "summary": "ok"}',
        )

    monkeypatch.setattr("werkstatt.reviewer.ask_llm", _fake_ask)
    monkeypatch.setattr(
        "werkstatt.reviewer._get_git_diff",
        lambda pd, task_files=None: "+ x = 2\n",
    )
    monkeypatch.setattr(
        "werkstatt.reviewer.audit", lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        "werkstatt.reviewer._verifiziere_reviewer_bugs",
        lambda bugs, pd, pn: bugs,
    )

    rc = run_phase_end_review(s)
    assert rc is True
    assert s.reviewer_bugs == [], (
        f"state.reviewer_bugs nicht geleert: {s.reviewer_bugs}"
    )
