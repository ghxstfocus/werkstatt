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
