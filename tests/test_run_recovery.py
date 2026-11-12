"""Fail-closed tests for restarting an idle durable run."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.web.run_recovery import RunRecoveryError, prepare_run_recovery


def _lauf(tmp_path: Path, *, run_id: str = "demo-20261112-abc12345"):
    project_dir = tmp_path / "demo"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "STATUS.md").write_text(
        "### OP-1: Beispiel\n- **Status:** open\n",
        encoding="utf-8",
    )
    state = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    state.init_new(
        "Aufgabe",
        [{"id": "task-1", "name": "Arbeit"}],
        tests=["pytest -q"],
        akzeptanzkriterien=["Ergebnis ist geprueft"],
    )
    state.run_id = run_id
    state.save()

    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", run_id, "Aufgabe")
    context = {
        "schema_version": 1,
        "goal": "Aufgabe",
        "op_id": "OP-1",
        "source": {"kind": "local"},
    }
    registry_record = {
        "state": "idle",
        "run_id": run_id,
        "context": context,
    }
    return project_dir, store, registry_record


def test_prepare_run_recovery_keeps_identity_and_checkpoint(tmp_path: Path) -> None:
    project_dir, store, record = _lauf(tmp_path)

    recovery = prepare_run_recovery(
        "demo", project_dir, record, store=store,
    )

    assert recovery["run_id"] == record["run_id"]
    assert recovery["goal"] == "Aufgabe"
    assert recovery["op_id"] == "OP-1"
    assert recovery["project_dir"] == project_dir.resolve()
    assert recovery["checkpoint"]["tasks"][0]["id"] == "task-1"


@pytest.mark.parametrize("state", ["starting", "running", "missing"])
def test_prepare_run_recovery_requires_idle_registry(
    tmp_path: Path,
    state: str,
) -> None:
    project_dir, store, record = _lauf(tmp_path)
    if state == "missing":
        record = None
    else:
        record["state"] = state

    with pytest.raises(RunRecoveryError):
        prepare_run_recovery("demo", project_dir, record, store=store)


def test_prepare_run_recovery_rejects_checkpoint_from_another_run(
    tmp_path: Path,
) -> None:
    project_dir, store, record = _lauf(tmp_path)
    state = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    assert state.load()
    state.run_id = "other-run"
    state.save()

    with pytest.raises(RunRecoveryError, match="Run-ID"):
        prepare_run_recovery("demo", project_dir, record, store=store)


def test_prepare_run_recovery_rejects_terminal_run_record(
    tmp_path: Path,
) -> None:
    project_dir, store, record = _lauf(tmp_path)
    run = store.get_run_record("demo", record["run_id"])
    assert run is not None
    store.update_run_checkpoint(
        "demo",
        record["run_id"],
        run["checkpoint"],
        expected_version=run["checkpoint_version"],
        status="completed",
    )

    with pytest.raises(RunRecoveryError, match="nicht wiederaufnehmbar"):
        prepare_run_recovery("demo", project_dir, record, store=store)


def test_prepare_run_recovery_uses_matching_fresh_backup(
    tmp_path: Path,
) -> None:
    project_dir, store, record = _lauf(tmp_path)
    state_path = project_dir / ".werkstatt" / "demo.phase.yaml"
    backup_path = state_path.with_suffix(".yaml.fresh-bak")
    state_path.replace(backup_path)
    wrong = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    wrong.init_new(
        "Andere Aufgabe",
        [{"id": "other-task", "name": "Andere Arbeit"}],
        tests=["pytest -q"],
        akzeptanzkriterien=["Anderes Ergebnis"],
    )
    wrong.run_id = "other-run"
    wrong.save()

    recovery = prepare_run_recovery("demo", project_dir, record, store=store)

    assert recovery["checkpoint"]["tasks"][0]["id"] == "task-1"
    assert recovery["project_dir"] == project_dir.resolve()


def test_resume_route_relaunches_same_run_without_fresh_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_module
    from werkstatt.web import run_recovery

    project_dir = tmp_path / "demo"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "STATUS.md").write_text("status", encoding="utf-8")
    run_id = "demo-20261112-abc12345"
    context = {
        "schema_version": 1,
        "goal": "Aufgabe",
        "op_id": None,
        "source": {"kind": "local"},
    }
    registry_record = {"state": "idle", "run_id": run_id, "context": context}
    reserved: list[tuple[str, str, dict[str, Any]]] = []

    class _Registry:
        def read(self, _project: str) -> dict[str, Any]:
            return registry_record

        def reserve(
            self,
            project: str,
            selected_run_id: str,
            *,
            context: dict[str, Any],
        ) -> tuple[bool, dict[str, Any]]:
            reserved.append((project, selected_run_id, context))
            return True, registry_record

        def register(self, _project: str, _run_id: str, _pid: int) -> None:
            return None

    recovery = {
        "run_id": run_id,
        "goal": "Aufgabe",
        "op_id": None,
        "context": context,
        "project_dir": project_dir,
    }
    monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
    monkeypatch.setattr(app_module, "_loop_registry", lambda: _Registry())
    monkeypatch.setattr(app_module, "_loop_prozess", lambda _project: None)
    monkeypatch.setattr(
        run_recovery, "prepare_run_recovery", lambda *_args: recovery,
    )
    app_module._LAUFENDE_LOOPS.clear()
    app_module._LOOP_RUN_IDS.clear()
    app_module._LOOP_LOG_HANDLES.clear()
    app_module._PAUSIERTE_LOOPS.clear()

    argv: list[list[str]] = []

    class _Process:
        pid = 12345

    monkeypatch.setattr(
        app_module.subprocess,
        "Popen",
        lambda args, **_kwargs: (argv.append(list(args)) or _Process()),
    )

    response = TestClient(app_module.app).post("/api/projects/demo/resume")

    assert response.status_code == 200
    assert response.json()["resume"] is True
    assert response.json()["run_id"] == run_id
    assert "--resume" in argv[0]
    assert "--fresh" not in argv[0]
    assert argv[0][argv[0].index("--run-id") + 1] == run_id
    assert reserved == [("demo", run_id, context)]


def test_orphaned_worker_state_blocks_web_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_module

    class _Registry:
        def read(self, _project: str) -> dict[str, Any]:
            return {
                "state": "orphaned",
                "run_id": "run-ambiguous",
                "recovery_issue": "worker_identity_ambiguous",
                "context": {},
            }

    monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
    monkeypatch.setattr(app_module, "_loop_registry", lambda: _Registry())
    monkeypatch.setattr(app_module, "_loop_prozess", lambda _project: None)
    monkeypatch.setattr(
        app_module.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("orphaned run must not spawn"),
    )

    response = TestClient(app_module.app).post(
        "/api/projects/demo/start",
        json={"aufgabe": "Neue Aufgabe"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "loop_worker_identity_ambiguous"

def test_live_worker_after_register_failure_is_kept_orphaned(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_module
    from werkstatt.web import run_recovery

    project_dir = tmp_path / "demo"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "STATUS.md").write_text("status", encoding="utf-8")
    run_id = "demo-20261112-abc12345"
    context = {
        "schema_version": 1,
        "goal": "Aufgabe",
        "op_id": None,
        "source": {"kind": "local"},
    }
    registry_record = {"state": "idle", "run_id": run_id, "context": context}
    states: list[str] = []

    class _Registry:
        def read(self, _project: str) -> dict[str, Any]:
            return registry_record

        def reserve(
            self,
            _project: str,
            _run_id: str,
            *,
            context: dict[str, Any],
        ) -> tuple[bool, None]:
            return True, None

        def register(self, *_args: Any) -> None:
            raise RuntimeError("registry unavailable")

        def set_state(self, _project: str, _run_id: str, state: str) -> bool:
            states.append(state)
            return True

    class _StuckProcess:
        pid = 12345

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> None:
            raise subprocess.TimeoutExpired("worker", timeout)

    def _ignore_signal(*_args: Any) -> None:
        return None

    monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
    monkeypatch.setattr(app_module, "_loop_registry", lambda: _Registry())
    monkeypatch.setattr(app_module, "_loop_prozess", lambda _project: None)
    monkeypatch.setattr(app_module.subprocess, "Popen", lambda *_a, **_k: _StuckProcess())
    monkeypatch.setattr(app_module.os, "killpg", _ignore_signal)
    monkeypatch.setattr(run_recovery, "prepare_run_recovery", lambda *_a: {
        "run_id": run_id,
        "goal": "Aufgabe",
        "op_id": None,
        "context": context,
        "project_dir": project_dir,
    })

    response = TestClient(app_module.app).post("/api/projects/demo/resume")

    assert response.status_code == 500
    assert states == ["orphaned"]


def test_resume_route_recovers_after_real_worker_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A real exited loop worker is detected and resumed from durable state."""
    if not Path("/proc").is_dir():
        pytest.skip("worker identity recovery requires Linux /proc")
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    import os
    import sys
    import time

    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_module
    from werkstatt.web import run_recovery
    from werkstatt.web.loop_registry import LoopProcessRegistry

    project_dir, store, _record = _lauf(tmp_path)
    run_id = "demo-20261112-abc12345"
    context = {
        "schema_version": 1,
        "goal": "Aufgabe",
        "op_id": "OP-1",
        "source": {"kind": "local"},
    }
    registry_path = tmp_path / ".werkstatt" / "web-loop-registry.db"
    registry_before_restart = LoopProcessRegistry(registry_path)
    reserved, conflict = registry_before_restart.reserve(
        "demo", run_id, context=context,
    )
    assert reserved and conflict is None

    fake_root = tmp_path / "worker-runtime"
    fake_package = fake_root / "werkstatt"
    fake_package.mkdir(parents=True)
    (fake_package / "__init__.py").write_text("", encoding="utf-8")
    (fake_package / "loop.py").write_text(
        "import os, time\n"
        "from pathlib import Path\n"
        "Path(os.environ['WERKSTATT_PROBE_READY']).write_text('ready')\n"
        "while True: time.sleep(0.05)\n",
        encoding="utf-8",
    )

    def _wait_ready(process: subprocess.Popen[bytes], ready: Path) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if ready.is_file():
                return
            if process.poll() is not None:
                pytest.fail(f"worker exited early with {process.returncode}")
            time.sleep(0.01)
        pytest.fail("worker did not publish its ready marker")

    env = {
        **os.environ,
        "PYTHONPATH": str(fake_root),
        "WERKSTATT_PROBE_READY": str(tmp_path / "worker-before-restart.ready"),
    }
    worker_args = [
        sys.executable, "-m", "werkstatt.loop",
        "--project", "demo", "--headless", "--run-id", run_id,
    ]
    first_worker = subprocess.Popen(
        worker_args, cwd=tmp_path, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    resumed_worker: subprocess.Popen[bytes] | None = None
    try:
        _wait_ready(first_worker, Path(env["WERKSTATT_PROBE_READY"]))
        registry_before_restart.register("demo", run_id, first_worker.pid)
        first_worker.terminate()
        first_worker.wait(timeout=5)

        # A separate registry instance models a restarted web process.
        registry_after_restart = LoopProcessRegistry(registry_path)
        recovered_record = registry_after_restart.read("demo")
        assert recovered_record is not None
        assert recovered_record["state"] == "idle"
        assert recovered_record["run_id"] == run_id

        monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
        monkeypatch.setattr(
            app_module, "_loop_registry", lambda: registry_after_restart,
        )
        monkeypatch.setattr(app_module, "_loop_prozess", lambda _project: None)
        monkeypatch.setattr(run_recovery, "EventStore", lambda: store)
        app_module._LAUFENDE_LOOPS.clear()
        app_module._LOOP_RUN_IDS.clear()
        app_module._LOOP_LOG_HANDLES.clear()
        app_module._PAUSIERTE_LOOPS.clear()

        real_popen = subprocess.Popen
        launch_env = {
            **env,
            "WERKSTATT_PROBE_READY": str(tmp_path / "worker-after-resume.ready"),
        }

        def _launch(args: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
            nonlocal resumed_worker
            resumed_worker = real_popen(
                args, env=launch_env, cwd=tmp_path,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return resumed_worker

        monkeypatch.setattr(app_module.subprocess, "Popen", _launch)
        response = TestClient(app_module.app).post(
            "/api/projects/demo/resume",
        )

        assert response.status_code == 200, response.text
        assert response.json()["resume"] is True
        assert response.json()["run_id"] == run_id
        assert resumed_worker is not None
        _wait_ready(
            resumed_worker,
            Path(launch_env["WERKSTATT_PROBE_READY"]),
        )
        assert "--resume" in worker_args or response.json()["resume"] is True
        checkpoint = PhaseState("demo", base_dir=project_dir / ".werkstatt")
        assert checkpoint.load()
        assert checkpoint.run_id == run_id
        assert checkpoint.data["tasks"][0]["id"] == "task-1"
        persisted = registry_after_restart.read("demo")
        assert persisted is not None
        assert persisted["run_id"] == run_id
        assert persisted["state"] == "running"
        assert persisted["pid"] == resumed_worker.pid
        assert persisted["context"] == context
    finally:
        for process in (first_worker, resumed_worker):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
