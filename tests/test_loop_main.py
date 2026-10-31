"""Spec: main() — CLI-Einstieg, Config-Fehler, Loop-Anbindung, Rollback.

Nicht dupliziert:
- --dry-run              -> test_loop.py:136
- _k13_rc                -> test_k13_rc.py (6)
- run_pipeline_loop-E2E  -> test_loop.py (23 Referenzen)

main() ruft ZWEI Config-Lader:
- werkstatt.loop.load_project_config (Zeile 46)
- werkstatt.orchestrator.load_project_config (Zeile 66)
Beide muessen gepatcht werden, sonst killt der zweite den Test
mit sys.exit(1) bei fehlender projects/<pn>.yaml.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import loop
from werkstatt.state import RunState


# =====================================================================
# Fixtures
# =====================================================================

def _audit_events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _kind(tmp_path: Path, kind: str) -> list[dict]:
    return [e for e in _audit_events(tmp_path) if e.get("kind") == kind]


def _silence_renderer():
    return patch.multiple(
        "werkstatt.loop_renderer",
        header=lambda *a, **kw: None,
        step=lambda *a, **kw: None,
        footer=lambda *a, **kw: None,
    )


def _base_config(tmp_path: Path) -> dict:
    return {
        "project_dir": str(tmp_path),
        "venv_python": "python3",
        "docs": {},
    }


@contextlib.contextmanager
def _patch_main_config(tmp_path: Path, cfg: dict | None = None):
    """Patcht BEIDE Config-Lader + load_docs + load_env.

    main() ruft:
    - loop.load_project_config (Zeile 46)
    - orchestrator.load_project_config + load_docs (Zeile 65-68)
    Fehlt der zweite Patch -> orchestrator killt mit SystemExit(1).
    """
    c = cfg if cfg is not None else _base_config(tmp_path)
    with patch("werkstatt.loop.load_project_config", return_value=c), \
         patch("werkstatt.orchestrator.load_project_config",
               return_value=c), \
         patch("werkstatt.orchestrator.load_docs", return_value={}), \
         patch("werkstatt.loop.load_env", return_value=None):
        yield c


# =====================================================================
# A. argparse
# =====================================================================

def test_main_help():
    with _silence_renderer():
        with pytest.raises(SystemExit) as exc:
            loop.main(["--help"])
    assert exc.value.code == 0


def test_main_ohne_project():
    with _silence_renderer():
        with pytest.raises(SystemExit) as exc:
            loop.main([])
    assert exc.value.code == 2


# =====================================================================
# B. Config-Fehler
# =====================================================================

def test_main_project_dir_fehlt(tmp_path):
    """load_project_config liefert {} -> rc=1."""
    with _silence_renderer(), \
         patch("werkstatt.loop.load_env", return_value=None), \
         patch("werkstatt.loop.load_project_config", return_value={}):
        assert loop.main(["--project", "p", "--aufgabe", "a"]) == 1


def test_main_ohne_api_key(tmp_path, monkeypatch):
    """DEEPSEEK_API_KEY fehlt -> rc=1."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with _silence_renderer(), _patch_main_config(tmp_path):
        assert loop.main(["--project", "p", "--aufgabe", "a"]) == 1


# =====================================================================
# C. Loop-Aufruf + K13
# =====================================================================

def _loop_runner(tasks_ok: int, rc: int, aufrufe: list | None = None):
    def _fake(project, aufgabe, state_ref, **kw):
        if aufrufe is not None:
            aufrufe.append({"project": project, "aufgabe": aufgabe,
                            "state_ref": state_ref, "kw": kw})
        state_ref[0].tasks_ok_counter = tasks_ok
        return rc
    return _fake


def test_main_ruft_run_pipeline_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    aufrufe: list = []
    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop",
               _loop_runner(1, 0, aufrufe)), \
         patch("werkstatt.loop._git_head", return_value="abc"), \
         patch("werkstatt.loop._git_dirty", return_value=False):
        rc = loop.main(["--project", "p", "--aufgabe", "aufgabe-x"])
    assert rc == 0
    assert len(aufrufe) == 1
    a = aufrufe[0]
    assert a["project"] == "p"
    assert a["aufgabe"] == "aufgabe-x"
    assert isinstance(a["state_ref"], list)
    assert isinstance(a["state_ref"][0], RunState)


def test_main_k13_rc_nach_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop",
               _loop_runner(3, 0)), \
         patch("werkstatt.loop._git_head", return_value="abc"), \
         patch("werkstatt.loop._git_dirty", return_value=False):
        assert loop.main(["--project", "p", "--aufgabe", "a"]) == 0


def test_main_k13_rc_kein_tasks_ok(tmp_path, monkeypatch):
    """run_pipeline_loop 0, tasks_ok=0 -> main 1 (K13)."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop",
               _loop_runner(0, 0)), \
         patch("werkstatt.loop._git_head", return_value="abc"), \
         patch("werkstatt.loop._git_dirty", return_value=False):
        assert loop.main(["--project", "p", "--aufgabe", "a"]) == 1


# =====================================================================
# D. --fresh
# =====================================================================

def test_main_fresh_legt_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    ps_dir = tmp_path / ".werkstatt"
    ps_dir.mkdir()
    (ps_dir / "p.phase.yaml").write_text("tasks: []\n")
    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop", _loop_runner(1, 0)), \
         patch("werkstatt.loop._git_head", return_value="abc"), \
         patch("werkstatt.loop._git_dirty", return_value=False):
        loop.main(["--project", "p", "--aufgabe", "a", "--fresh"])
    baks = list(ps_dir.glob("*.fresh-bak"))
    assert len(baks) == 1
    assert len(_kind(tmp_path, "loop_fresh_reset")) == 1


# =====================================================================
# E. Rollback / Stash-Pop
# =====================================================================

def test_main_rollback_bei_rc_mit_flag(tmp_path, monkeypatch):
    """Fix AA: --rollback explizit -> reset wird aufgerufen."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    reset_calls: list = []

    def _fake_reset(pd, ref):
        reset_calls.append((str(pd), ref))
        return True

    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop", _loop_runner(0, 1)), \
         patch("werkstatt.loop._git_head", return_value="abc123"), \
         patch("werkstatt.loop._git_dirty", return_value=False), \
         patch("werkstatt.loop._git_reset", _fake_reset):
        rc = loop.main(["--project", "p", "--aufgabe", "a",
                        "--rollback"])
    assert rc == 1
    assert len(reset_calls) == 1
    assert reset_calls[0][1] == "abc123"
    assert len(_kind(tmp_path, "loop_rollback")) == 1


def test_main_rollback_bei_rc_ohne_flag(tmp_path, monkeypatch):
    """Fix AA: ohne --rollback bleibt der Tree unveraendert."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    reset_calls: list = []

    def _fake_reset(pd, ref):
        reset_calls.append((str(pd), ref))
        return True

    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop", _loop_runner(0, 1)), \
         patch("werkstatt.loop._git_head", return_value="abc123"), \
         patch("werkstatt.loop._git_dirty", return_value=False), \
         patch("werkstatt.loop._git_reset", _fake_reset):
        rc = loop.main(["--project", "p", "--aufgabe", "a"])
    assert rc == 1
    assert len(reset_calls) == 0, "Rollback ohne --rollback aufgerufen"
    assert len(_kind(tmp_path, "loop_rollback_skipped")) == 1


def test_main_stash_pop_bei_erfolg(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    pop_calls: list = []

    def _fake_pop(pd):
        pop_calls.append(str(pd))
        return True

    with _silence_renderer(), _patch_main_config(tmp_path), \
         patch("werkstatt.loop.run_pipeline_loop", _loop_runner(1, 0)), \
         patch("werkstatt.loop._git_head", return_value="abc"), \
         patch("werkstatt.loop._git_dirty", return_value=True), \
         patch("werkstatt.loop._git_stash", return_value=True), \
         patch("werkstatt.loop._git_stash_pop", _fake_pop):
        rc = loop.main(["--project", "p", "--aufgabe", "a"])
    assert rc == 0
    assert len(pop_calls) == 1
    assert len(_kind(tmp_path, "loop_stash_pop")) == 1


# =====================================================================
# GOLD 2026-10-30: Hook-Block ueberspringt Apply-Loop
# =====================================================================

def test_hook_blocked_ueberspringt_apply_loop(tmp_path, monkeypatch):
    """Bei pre_tool_use deny: keine Patches angewendet, Task failed.

    Regression: Vorher rief 'break' nur aus der Hook-Schleife aus,
    der Apply-Loop wendete dieselben blockierten Patches trotzdem an
    (loop_patch_updated im Audit).
    """
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "a.py").write_text("alte zeile\n")
    s = RunState(
        block_id="t", aufgabe="a", start_ts="x",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="t",
    )

    # Wir koennen den Haupt-Pfad nicht isoliert aufrufen (run_pipeline_loop
    # ist zu gross). Wir testen den Hook-Block ueber die Hilfsfunktion
    # _apply_patches_with_hooks, die denselben Effekt hat: bei deny kein
    # Patch. Das ist die einzige isoliert testbare Stelle.
    with patch("werkstatt.loop._call_hook",
               return_value={"allow": False, "reason": "hook-deny"}):
        n = loop_mod._apply_patches_with_hooks(
            s,
            [{"file": "a.py", "old_string": "alte zeile",
              "new_string": "neue zeile"}],
            phase_label="test",
        )
    assert n == 0
    # Datei unveraendert.
    assert (tmp_path / "a.py").read_text() == "alte zeile\n"
