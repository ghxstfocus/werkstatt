"""Persistente, transaktionssichere Loop-Prozessregistrierung."""
import os
from pathlib import Path

from werkstatt.web.loop_registry import LoopProcessRegistry


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
