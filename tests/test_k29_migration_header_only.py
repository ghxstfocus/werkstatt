"""K29: K17c prueft nur ## data/migrations/-Header, nicht Fliesstext."""
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
    assert res.returncode == 0, f"rc={res.returncode} stderr={res.stderr}"
    return json.loads(res.stdout)


def _mk_migrations(tmp_path: Path, nums: list) -> Path:
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    for n in nums:
        (mdir / f"{n}_x.sql").write_text("-- noop\n")
    return mdir


def _basis_payload(prosa: str, project_dir: str, task_files: list) -> dict:
    return {
        "tasks": [{"id": "t1", "action": "create", "task_files": task_files}],
        "phasen": [],
        "project_dir": project_dir,
        "architect_prosa": prosa,
    }


def test_fliesstext_referenz_wird_nicht_als_kollision_erkannt(tmp_path: Path):
    """K29: 'folgt Muster von 0008_x.sql' ist keine Kollision."""
    _mk_migrations(tmp_path, ["0008", "0017"])
    prosa = (
        "Die Migration folgt exakt dem Muster von "
        "`data/migrations/0008_search_run.sql`. "
        "## data/migrations/0019_neu.sql\n"
        "Neue Permission anlegen."
    )
    # Task-File muss auch neu sein, sonst K27/K20-Greift.
    payload = _basis_payload(
        prosa, str(tmp_path),
        ["data/migrations/0019_neu.sql"],
    )
    out = _run_hook(payload)
    assert out["allow"] is True, f"unerwartet rejected: {out}"


def test_header_kollision_wird_erkannt(tmp_path: Path):
    """K29: Header '## data/migrations/0017_*' kollidiert."""
    _mk_migrations(tmp_path, ["0017"])
    prosa = (
        "## data/migrations/0017_neu.sql\n"
        "Permission anlegen."
    )
    payload = _basis_payload(
        prosa, str(tmp_path),
        ["data/migrations/0017_neu.sql"],
    )
    out = _run_hook(payload)
    assert out["allow"] is False
    assert "MIGRATIONS_KOLLISION" in out["reason"]
