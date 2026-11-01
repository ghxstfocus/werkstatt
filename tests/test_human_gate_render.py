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
