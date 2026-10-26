"""K1b/Schritt1: main() persistiert PhaseState am Loop-Ende.

K14-neutral: prüft nur, dass der Wrapper in main() nach
run_pipeline_loop() _ps.save() aufruft — unabhängig davon,
wie run_pipeline_loop intern zerlegt ist.

Hinweis zu PhaseState: mark_failed() schreibt task["failure"]
und ruft update_task()->save() bereits selbst. main() garantiert
zusätzlich, dass nach dem Loop-Ende die Datei existiert.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from werkstatt.phase_state import PhaseState


def test_save_nach_failed_erzeugt_yaml(tmp_path: Path) -> None:
    """Nach mark_failed()+save() existiert YAML mit status=failed+failure."""
    ps = PhaseState("k1b", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1", "name": "x"}])
    ps.mark_failed("t1", failure="boom")
    ps.save()

    path = tmp_path / ".werkstatt" / "k1b.phase.yaml"
    assert path.exists(), "PhaseState-Datei fehlt nach save()"
    data = yaml.safe_load(path.read_text())
    task = data["tasks"][0]
    assert task["status"] == "failed"
    assert task["failure"] == "boom"


def test_save_ist_atomar(tmp_path: Path) -> None:
    """save() nutzt tmp+rename -> keine halbgeschriebene YAML."""
    ps = PhaseState("k1b", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1", "name": "x"}])
    ps.save()
    tmp = tmp_path / ".werkstatt" / "k1b.phase.yaml.tmp"
    assert not tmp.exists(), "tmp-Datei blieb nach save() liegen"


def test_init_new_normalisiert_status_auf_pending(tmp_path: Path) -> None:
    """init_new ignoriert uebergebenen status (dokumentiert)."""
    ps = PhaseState("k1b", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1", "name": "x", "status": "failed"}])
    ps.save()
    data = yaml.safe_load((tmp_path / ".werkstatt" / "k1b.phase.yaml").read_text())
    assert data["tasks"][0]["status"] == "pending"


def test_mark_failed_ruft_save_implizit(tmp_path: Path) -> None:
    """Beweis: mark_failed() persistiert selbst (via update_task->save).

    Wichtig fuer K1b-Diagnose: Persistenz existiert schon auf
    Task-Ebene. main()-save() ist Absicherung fuer Loop-Ende,
    nicht Ersatz fuer fehlende Task-Persistenz.
    """
    ps = PhaseState("k1b", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1", "name": "x"}])
    ps.save()
    path = tmp_path / ".werkstatt" / "k1b.phase.yaml"
    mtime_vor = path.stat().st_mtime_ns

    # Kein expliziter save() — mark_failed() muss selbst persistieren.
    ps.mark_failed("t1", failure="boom")

    data = yaml.safe_load(path.read_text())
    assert data["tasks"][0]["status"] == "failed"
    assert data["tasks"][0]["failure"] == "boom"
    # Datei wurde aktualisiert.
    assert path.stat().st_mtime_ns >= mtime_vor
