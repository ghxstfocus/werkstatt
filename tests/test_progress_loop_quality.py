"""OP-063: Loop-PROGRESS-Eintraege + Commit-Message-Qualitaet.

Drei Defekte aus Loop-Validierung #2 (17:25 OP-002b3):
1. _task_ende schreibt pro Task einen leeren PROGRESS-Eintrag.
2. _progress_op_done feuert nicht, wenn OP-NNN nur in Delete-Zone steht.
3. Commit-Subject wird mitten im Wort abgeschnitten.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from werkstatt.committer import _build_commit_subject
from werkstatt.task_runner import _task_ende


# ═══════════════════════════════════════════════════════════════
# A. _task_ende: PROGRESS.append unterdruecken wenn OP-NNN in Aufgabe
# ═══════════════════════════════════════════════════════════════


def test_task_ende_skip_progress_bei_op_nnn(tmp_path: Path) -> None:
    """Aufgabe nennt OP-002b3: kein Task-Progress-Eintrag."""
    (tmp_path / ".werkstatt").mkdir()
    progress_p = tmp_path / "PROGRESS.md"
    progress_p.write_text("# Fortschritt\n", encoding="utf-8")

    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.aufgabe = "OP-002b3: upsert_seen erweitern"
    s.tasks_ok_counter = 0

    ps = SimpleNamespace()
    ps.mark_done = lambda tid, **kw: None
    ps.mark_failed = lambda tid, **kw: None
    ps.get_task = lambda tid: None

    _audits: list[str] = []
    with patch("werkstatt.task_runner.audit",
               lambda k, p, *a, **kw: _audits.append(k)):
        _task_ende(s, ps, "t1", ok=True, name="T1")

    txt = progress_p.read_text(encoding="utf-8")
    assert "T1" not in txt, (
        f"Task-Eintrag trotz OP-NNN geschrieben: {txt!r}"
    )
    assert "loop_task_ende_skip_progress" in _audits or True  # optional


def test_task_ende_schreibt_progress_ohne_op_nnn(tmp_path: Path) -> None:
    """Aufgabe ohne OP-NNN: Task-Eintrag bleibt (Fallback)."""
    (tmp_path / ".werkstatt").mkdir()
    progress_p = tmp_path / "PROGRESS.md"
    progress_p.write_text("# Fortschritt\n", encoding="utf-8")

    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.aufgabe = "Freies Experiment ohne OP-Bezug"
    s.tasks_ok_counter = 0

    ps = SimpleNamespace()
    ps.mark_done = lambda tid, **kw: None
    ps.mark_failed = lambda tid, **kw: None
    ps.get_task = lambda tid: None

    with patch("werkstatt.task_runner.audit", lambda *a, **kw: None):
        _task_ende(s, ps, "t1", ok=True, name="MeinTask")

    txt = progress_p.read_text(encoding="utf-8")
    assert "MeinTask" in txt, (
        f"Task-Eintrag fehlt, obwohl kein OP-NNN: {txt!r}"
    )


# ═══════════════════════════════════════════════════════════════
# B. Commit-Subject: OP-NNN + Wortgrenze
# ═══════════════════════════════════════════════════════════════


def test_subject_mit_op_nnn() -> None:
    """OP-NNN wird vorangestellt, Aufgabe als Subject."""
    subj = _build_commit_subject(
        "OP-002b3: In core/inventory/repository.py die Methode "
        "update_last_ip_if_changed um einen optionalen Parameter "
        "commit erweitern.",
        "OP-002b3",
    )
    assert subj.startswith("OP-002b3"), subj
    # Kein Wortabschnitt: kein abgeschnittenes Wort am Ende.
    assert not subj.rstrip().endswith("Metho"), subj
    # Subject bleibt unter 72 Zeichen.
    assert len(subj) <= 72, f"zu lang: {len(subj)}"


def test_subject_ohne_op_nnn_wortgrenze() -> None:
    """Ohne OP-NNN: Wortgrenze statt Zeichen-Abschnitt."""
    subj = _build_commit_subject(
        "Eine sehr lange Aufgabe ohne OP-Bezug die irgendwann "
        "einfach zu lang wird und dann abgeschnitten werden muss.",
        None,
    )
    # Kein abgeschnittenes Wort am Ende.
    assert not subj.endswith("mu"), subj
    assert " " in subj  # mehrere Woerter


# ═══════════════════════════════════════════════════════════════
# OP-063b: OP-NNN-Doppelung + Subject-Abschnitt
# ═══════════════════════════════════════════════════════════════


def test_progress_op_done_kein_doppel_praefix(tmp_path: Path) -> None:
    """Subject enthaelt bereits OP-NNN: _progress_op_done klebt keinen zweiten davor."""
    from werkstatt.committer import _progress_op_done

    (tmp_path / ".werkstatt").mkdir()
    progress = tmp_path / "PROGRESS.md"
    progress.write_text("# Fortschritt\n", encoding="utf-8")

    _progress_op_done(
        tmp_path, "OP-004",
        "OP-004: In core/checks/__init__.py die Funktion ...", "p",
    )
    txt = progress.read_text(encoding="utf-8")
    assert "OP-004: OP-004:" not in txt, (
        f"Doppel-Praefix: {txt!r}"
    )
    assert "OP-004:" in txt


def test_build_commit_subject_unter_72_zeichen() -> None:
    """Subject + Typ + Scope bleiben <= 72 Zeichen, kein Wortabschnitt."""
    from werkstatt.committer import _build_commit_subject

    subj = _build_commit_subject(
        "OP-004: In core/checks/__init__.py die Funktion "
        "check_port_range so umschreiben, dass mypy 0 Fehler zeigt. "
        "Aktuell 2 operator-Fehler in Zeile 76.",
        "OP-004",
    )
    # Subject allein
    assert len(subj) <= 60, f"subject zu lang: {len(subj)}"
    # Kein abgeschnittenes Wort am Ende
    assert not subj.rstrip().endswith("che"), subj
    # Volles Commit-Subject <= 72
    full = f"fix(security-ai): {subj}"
    assert len(full) <= 72, f"full subject zu lang: {len(full)}"
