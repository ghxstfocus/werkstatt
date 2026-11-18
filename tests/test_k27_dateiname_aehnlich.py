"""Planner gate checks real path conflicts, not fuzzy filename similarity."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "planner_gate.py"


def _run_hook(payload: dict) -> dict:
    res = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        cwd=ROOT,
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert res.returncode == 0, f"rc={res.returncode} stderr={res.stderr}"
    return json.loads(res.stdout)


def test_create_aehnlicher_name_is_not_a_conflict(tmp_path: Path):
    (tmp_path / "apps" / "dashboard" / "templates").mkdir(parents=True)
    (tmp_path / "apps" / "dashboard" / "templates" / "change_detail.html").write_text("x")
    payload = {
        "tasks": [{
            "id": "t1", "action": "create",
            "task_files": ["apps/dashboard/templates/changes_detail.html"],
        }],
        "phasen": [],
        "project_dir": str(tmp_path),
        "architect_prosa": "",
    }
    out = _run_hook(payload)
    assert out["allow"] is True


def test_loop_start_is_not_blocked_by_loop_state(tmp_path: Path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_loop_state.py").write_text("existing test")
    payload = {
        "tasks": [{
            "id": "t1", "action": "create",
            "task_files": ["tests/test_loop_start.py"],
        }],
        "phasen": [],
        "project_dir": str(tmp_path),
        "architect_prosa": "",
    }
    out = _run_hook(payload)
    assert out["allow"] is True


def test_create_voellig_neuer_name_ok(tmp_path: Path):
    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "templates" / "other.html").write_text("x")
    payload = {
        "tasks": [{
            "id": "t1", "action": "create",
            "task_files": ["templates/brandnew.html"],
        }],
        "phasen": [],
        "project_dir": str(tmp_path),
        "architect_prosa": "",
    }
    out = _run_hook(payload)
    assert out["allow"] is True


def test_create_mit_exakter_datei_wird_von_k20_geprueft(tmp_path: Path):
    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "templates" / "exact.html").write_text("x")
    payload = {
        "tasks": [{
            "id": "t1", "action": "create",
            "task_files": ["templates/exact.html"],
        }],
        "phasen": [],
        "project_dir": str(tmp_path),
        "architect_prosa": "",
    }
    out = _run_hook(payload)
    assert out["allow"] is True


def test_update_task_ignoriert(tmp_path: Path):
    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "templates" / "x.html").write_text("x")
    payload = {
        "tasks": [{
            "id": "t1", "action": "update",
            "task_files": ["templates/x.html"],
        }],
        "phasen": [],
        "project_dir": str(tmp_path),
        "architect_prosa": "",
    }
    out = _run_hook(payload)
    assert out["allow"] is True
