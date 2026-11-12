"""Persistente, transaktionssichere Loop-Prozessregistrierung."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from werkstatt.web.loop_registry import (
    LoopProcessRegistry,
    _find_run_workers,
    _worker_command_matches,
)


def test_reservierung_ist_ueber_registry_instanz_atomisch(tmp_path: Path):
    db = tmp_path / "web-loop-registry.db"
    worker_a = LoopProcessRegistry(db)
    worker_b = LoopProcessRegistry(db)

    reserviert, bestehend = worker_a.reserve("demo", "run-a")
    zweiter_start, konflikt = worker_b.reserve("demo", "run-b")

    assert reserviert is True
    assert bestehend is None
    assert zweiter_start is False
    assert konflikt is not None
    assert konflikt["run_id"] == "run-a"
    assert konflikt["state"] == "starting"
    assert konflikt["context"] == {}


def test_registrierung_pause_und_idle_sind_restartfest(tmp_path: Path):
    registry = LoopProcessRegistry(tmp_path / "registry.db")
    assert registry.reserve("demo", "run-a") == (True, None)

    identity = registry.register("demo", "run-a", os.getpid())
    record = registry.read("demo")
    assert record is not None
    assert record["state"] == "running"
    assert record["run_id"] == "run-a"
    assert record["process_identity"] == identity

    assert registry.set_state("demo", "run-a", "paused") is True
    assert registry.read("demo")["state"] == "paused"
    assert registry.set_state("demo", "run-a", "idle") is True
    idle = registry.read("demo")
    assert idle is not None
    assert idle["state"] == "idle"
    assert idle["pid"] is None


def test_startkontext_bleibt_nach_restart_und_idle_erhalten(tmp_path: Path) -> None:
    db = tmp_path / "registry.db"
    first_worker = LoopProcessRegistry(db)
    second_worker = LoopProcessRegistry(db)
    context = {
        "schema_version": 1,
        "goal": "OP-397: Run-Kontext persistent machen",
        "op_id": "OP-397",
        "source": {"kind": "local", "base_sha": "abc123"},
    }

    assert first_worker.reserve("demo", "run-context", context=context) == (
        True, None,
    )
    duplicate, existing = second_worker.reserve(
        "demo", "run-duplicate", context={"goal": "must not replace"},
    )

    assert duplicate is False
    assert existing is not None
    assert existing["context"] == context
    assert second_worker.register("demo", "run-context", os.getpid())
    assert second_worker.set_state("demo", "run-context", "idle") is True
    recovered = first_worker.read("demo")
    assert recovered is not None
    assert recovered["context"] == context


def test_abgelaufene_startreservierung_wird_freigegeben(tmp_path: Path):
    registry = LoopProcessRegistry(tmp_path / "registry.db")
    assert registry.reserve("demo", "run-stale") == (True, None)
    with registry._connect() as conn:
        conn.execute(
            "UPDATE loop_processes SET updated_at=0 WHERE project='demo'"
        )
        conn.commit()

    record = registry.read("demo")
    assert record is not None
    assert record["state"] == "idle"
    assert record["run_id"] == "run-stale"



def test_control_transition_is_compare_and_set_across_registry_instances(
    tmp_path: Path,
) -> None:
    db = tmp_path / "registry.db"
    worker_a = LoopProcessRegistry(db)
    worker_b = LoopProcessRegistry(db)
    assert worker_a.reserve("demo", "run-a") == (True, None)
    worker_a.register("demo", "run-a", os.getpid())

    assert worker_a.transition("demo", "run-a", "running", "pausing") is True
    assert worker_b.read("demo")["state"] == "pausing"
    assert worker_b.transition("demo", "run-a", "running", "pausing") is False
    assert worker_b.transition("demo", "run-a", "pausing", "paused") is True
    assert worker_a.read("demo")["state"] == "paused"

    assert worker_a.transition("demo", "run-a", "paused", "stopping") is True
    assert worker_b.reserve("demo", "run-b")[0] is False
    assert worker_b.transition("demo", "run-a", "stopping", "idle") is True
    assert worker_a.read("demo")["state"] == "idle"


def test_abandoned_control_transition_recovers_from_kernel_state(
    tmp_path: Path,
) -> None:
    db = tmp_path / "registry.db"
    registry = LoopProcessRegistry(db)
    assert registry.reserve("demo", "run-a") == (True, None)
    registry.register("demo", "run-a", os.getpid())
    assert registry.transition("demo", "run-a", "running", "pausing") is True

    with registry._connect() as conn:
        conn.execute(
            "UPDATE loop_processes SET updated_at=0 WHERE project='demo'"
        )
        conn.commit()

    record = registry.read("demo")
    assert record is not None
    assert record["state"] == "running"



def test_stop_claim_excludes_overlap_and_reclaims_stale_stop(tmp_path: Path):
    db = tmp_path / "registry.db"
    worker_a = LoopProcessRegistry(db)
    worker_b = LoopProcessRegistry(db)
    assert worker_a.reserve("demo", "run-a") == (True, None)
    worker_a.register("demo", "run-a", os.getpid())

    assert worker_a.claim_stop("demo", "run-a") is True
    assert worker_b.read("demo")["state"] == "stopping"
    assert worker_b.claim_stop("demo", "run-a") is False

    with worker_a._connect() as conn:
        conn.execute(
            "UPDATE loop_processes SET updated_at=0 WHERE project='demo'"
        )
        conn.commit()

    assert worker_b.claim_stop("demo", "run-a") is True
    assert worker_a.claim_stop("demo", "run-a") is False


def _start_process_with_loop_identity(
    project: str,
    run_id: str,
    tmp_path: Path,
) -> subprocess.Popen:
    module_root = tmp_path / f"worker-stub-{run_id}"
    package = module_root / "werkstatt"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "loop.py").write_text(
        "import time\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(module_root), env.get("PYTHONPATH", "")) if part
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "werkstatt.loop",
            "--project",
            project,
            "--headless",
            "--run-id",
            run_id,
        ],
        cwd=module_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _stop_process(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def test_abgelaufener_start_reattacht_einen_laufenden_worker(tmp_path: Path):
    if not Path("/proc").is_dir():
        pytest.skip("Prozessidentitaetssuche erfordert Linux /proc")
    registry = LoopProcessRegistry(tmp_path / "registry.db")
    run_id = "run-orphan-live"
    process = _start_process_with_loop_identity("demo", run_id, tmp_path)
    try:
        assert registry.reserve("demo", run_id) == (True, None)
        with registry._connect() as conn:
            conn.execute(
                "UPDATE loop_processes SET updated_at=0 WHERE project='demo'",
            )
            conn.commit()

        recovered = registry.read("demo")

        assert recovered is not None
        assert recovered["state"] == "running"
        assert recovered["pid"] == process.pid
        assert recovered["process_identity"]
        assert recovered["run_id"] == run_id
    finally:
        _stop_process(process)


def test_ambiguous_start_fails_closed_then_recovers_after_one_worker_exits(
    tmp_path: Path,
):
    if not Path("/proc").is_dir():
        pytest.skip("Prozessidentitaetssuche erfordert Linux /proc")
    registry = LoopProcessRegistry(tmp_path / "registry.db")
    run_id = "run-orphan-ambiguous"
    first = _start_process_with_loop_identity("demo", run_id, tmp_path)
    second = _start_process_with_loop_identity("demo", run_id, tmp_path)
    try:
        assert registry.reserve("demo", run_id) == (True, None)
        with registry._connect() as conn:
            conn.execute(
                "UPDATE loop_processes SET updated_at=0 WHERE project='demo'",
            )
            conn.commit()

        ambiguous = registry.read("demo")
        assert ambiguous is not None
        assert ambiguous["state"] == "orphaned"
        assert ambiguous["recovery_issue"] == "worker_identity_ambiguous"
        assert registry.reserve("demo", "run-new") == (False, ambiguous)

        _stop_process(first)
        first = None
        recovered = registry.read("demo")
        assert recovered is not None
        assert recovered["state"] == "running"
        assert recovered["pid"] == second.pid
    finally:
        if first is not None:
            _stop_process(first)
        _stop_process(second)

def test_worker_match_requires_real_module_invocation() -> None:
    real_argv = [
        sys.executable, "-m", "werkstatt.loop",
        "--project", "demo", "--run-id", "run-exact",
    ]
    forged_script_argv = [
        sys.executable, "-c", "import time; time.sleep(30)",
        "-m", "werkstatt.loop",
        "--project", "demo", "--run-id", "run-exact",
    ]

    assert _worker_command_matches(real_argv, "demo", "run-exact")
    assert not _worker_command_matches(forged_script_argv, "demo", "run-exact")


def test_worker_discovery_ignores_processes_owned_by_other_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not Path("/proc").is_dir():
        pytest.skip("Prozessidentitaetssuche erfordert Linux /proc")
    from werkstatt.web import loop_registry

    run_id = "run-foreign-owner"
    process = _start_process_with_loop_identity("demo", run_id, tmp_path)
    try:
        actual_uid = os.geteuid()
        monkeypatch.setattr(loop_registry.os, "geteuid", lambda: actual_uid + 1)

        workers, complete = _find_run_workers("demo", run_id)

        assert complete
        assert process.pid not in [pid for pid, _identity in workers]
    finally:
        _stop_process(process)
