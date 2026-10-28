"""K17c: planner_gate-Hook lehnt Migrations-Kollision deterministisch ab.

Integration: Reparatur-Runde in loop.py:1298-1303 greift, weil _plan_gate
False liefert und last_planner_info gesetzt ist.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path("/opt/werkstatt/hooks/planner_gate.py")


def _run_hook(payload: dict) -> dict:
    res = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd="/opt/werkstatt",
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert res.returncode == 0, f"Hook rc={res.returncode}: {res.stderr}"
    return json.loads(res.stdout)


def _mk_migrations(tmp_path: Path) -> Path:
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for n in ("0017_guardrail_permissions.sql",
              "0018_guardrail_permissions.sql"):
        (mdir / n).write_text("-- noop\n")
    return mdir


def _basis_payload(prosa: str, project_dir: str) -> dict:
    return {
        "tasks": [
            {"id": "t1", "action": "create",
             "task_files": ["data/migrations/0017_sofortmassnahme.sql"]},
        ],
        "phasen": [],
        "project_dir": project_dir,
        "architect_prosa": prosa,
    }


def test_hook_deny_bei_kollision(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = "## data/migrations/0017_sofortmassnahme.sql\nTabelle."
    out = _run_hook(_basis_payload(prosa, str(tmp_path)))
    assert out["allow"] is False
    assert "MIGRATIONS_KOLLISION" in out["reason"]
    assert out["info"]["regel"] == "MIGRATIONS_KOLLISION"
    assert "0019" in out["info"]["details"]


def test_hook_allow_naechste_frei(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = "## data/migrations/0019_sofortmassnahme.sql\nTabelle."
    # Datei-Name im Task muss gueltig sein (sonst greift TASK_FILE vorher).
    payload = _basis_payload(prosa, str(tmp_path))
    payload["tasks"][0]["task_files"] = ["data/migrations/0019_sofortmassnahme.sql"]
    out = _run_hook(payload)
    assert out["allow"] is True


def test_hook_ignoriert_ohne_pfad_prefix(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = "Nur Text: die Datei 0017_sofortmassnahme.sql waere schoen."
    payload = _basis_payload(prosa, str(tmp_path))
    # Task-File muss gueltig sein, sonst TASK_FILE-Fail.
    payload["tasks"][0]["task_files"] = ["data/migrations/0019_x.sql"]
    out = _run_hook(payload)
    assert out["allow"] is True


def test_hook_ohne_migrations_ordner(tmp_path: Path):
    # Kein data/migrations/ -> keine Kollision, allow.
    prosa = "## data/migrations/0017_x.sql"
    payload = _basis_payload(prosa, str(tmp_path))
    payload["tasks"][0]["task_files"] = ["data/migrations/0017_x.sql"]
    out = _run_hook(payload)
    assert out["allow"] is True


def test_hook_mehrfach_kollision(tmp_path: Path):
    _mk_migrations(tmp_path)
    prosa = (
        "data/migrations/0017_a.sql und "
        "data/migrations/0018_b.sql"
    )
    payload = _basis_payload(prosa, str(tmp_path))
    payload["tasks"][0]["task_files"] = ["data/migrations/0019_c.sql"]
    out = _run_hook(payload)
    assert out["allow"] is False
    assert "0017" in out["info"]["details"] or "0017" in out["reason"]
    assert "0018" in out["info"]["details"] or "0018" in out["reason"]
