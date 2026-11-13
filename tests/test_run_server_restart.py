"""HTTP integration: a separate web server can reattach to a live loop worker."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.web.loop_registry import LoopProcessRegistry


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(url: str) -> dict:
    with urlopen(Request(url), timeout=1) as response:
        return json.loads(response.read())


def _wait_for_server(
    process: subprocess.Popen[bytes],
    url: str,
    log_path: Path,
) -> dict:
    deadline = time.monotonic() + 10
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(
                f"Webserver exited with {process.returncode}: "
                f"{log_path.read_text(encoding='utf-8', errors='replace')}"
            )
        try:
            return _request_json(url)
        except (OSError, URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.05)
    pytest.fail(f"Webserver did not become ready: {last_error}")


def _start_webserver(
    *,
    repo_root: Path,
    overlay_root: Path,
    project_base: Path,
    state_home: Path,
    port: int,
    log_path: Path,
) -> subprocess.Popen[bytes]:
    script = (
        "import os, sys\n"
        "sys.path.insert(0, os.environ['WERKSTATT_TEST_OVERLAY'])\n"
        "from pathlib import Path\n"
        "from werkstatt.web import app as web\n"
        "from werkstatt.web.auth import set_auth_disabled\n"
        "web._PROJECTS_BASE = Path(os.environ['WERKSTATT_TEST_PROJECTS_BASE'])\n"
        "set_auth_disabled(True)\n"
        "import uvicorn\n"
        f"uvicorn.run(web.app, host='127.0.0.1', port={port}, "
        "log_level='error')\n"
    )
    env = {
        **os.environ,
        "WERKSTATT_HOME": str(state_home),
        "WERKSTATT_TEST_OVERLAY": str(overlay_root),
        "WERKSTATT_TEST_PROJECTS_BASE": str(project_base),
        "WERKSTATT_REAL_PACKAGE": str(repo_root / "werkstatt"),
        "PYTHONPATH": os.pathsep.join((str(overlay_root), str(repo_root))),
    }
    with log_path.open("wb") as log:
        return subprocess.Popen(
            [sys.executable, "-c", script],
            cwd=repo_root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def test_http_server_restart_reattaches_to_the_same_worker(tmp_path: Path) -> None:
    """Restart two independent web processes while the exact loop worker survives."""
    if not Path("/proc").is_dir():
        pytest.skip("worker identity recovery requires Linux /proc")
    pytest.importorskip("uvicorn")

    repo_root = Path(__file__).resolve().parents[1]
    project_base = tmp_path / "projects"
    project_dir = project_base / "demo"
    (project_dir / "docs").mkdir(parents=True)
    (project_dir / "docs" / "STATUS.md").write_text(
        "### OP-1: Beispiel\n- **Status:** open\n",
        encoding="utf-8",
    )
    run_id = "demo-20261113-e2e001"
    goal = "Recovery nach echtem Webserver-Neustart"
    state = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    state.init_new(
        goal,
        [{"id": "task-1", "name": "Worker-Recovery pruefen"}],
        tests=["pytest -q"],
        akzeptanzkriterien=["Der gleiche Worker bleibt steuerbar"],
    )
    state.run_id = run_id
    state.save()

    state_home = tmp_path / "werkstatt-home"
    EventStore(state_home / ".werkstatt" / "events.db").create_run_record(
        "demo", run_id, goal,
    )
    registry_path = project_base / ".werkstatt" / "web-loop-registry.db"
    registry = LoopProcessRegistry(registry_path)
    context = {
        "schema_version": 1,
        "goal": goal,
        "op_id": "OP-1",
        "source": {"kind": "local"},
    }
    reserved, conflict = registry.reserve("demo", run_id, context=context)
    assert reserved and conflict is None

    overlay_root = tmp_path / "module-overlay"
    stub_package = overlay_root / "werkstatt"
    stub_package.mkdir(parents=True)
    (stub_package / "__init__.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "__path__ = [str(Path(__file__).parent), "
        "os.environ['WERKSTATT_REAL_PACKAGE']]\n",
        encoding="utf-8",
    )
    (stub_package / "loop.py").write_text(
        "import os, time\n"
        "from pathlib import Path\n"
        "Path(os.environ['WERKSTATT_PROBE_READY']).write_text('ready')\n"
        "while True: time.sleep(0.05)\n",
        encoding="utf-8",
    )
    worker_env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(overlay_root), str(repo_root))),
        "WERKSTATT_REAL_PACKAGE": str(repo_root / "werkstatt"),
        "WERKSTATT_PROBE_READY": str(tmp_path / "worker.ready"),
    }
    worker = subprocess.Popen(
        [
            sys.executable, "-m", "werkstatt.loop",
            "--project", "demo", "--headless", "--run-id", run_id,
        ],
        cwd=project_dir,
        env=worker_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    servers: list[subprocess.Popen[bytes]] = []
    try:
        deadline = time.monotonic() + 8
        ready = Path(worker_env["WERKSTATT_PROBE_READY"])
        while time.monotonic() < deadline and not ready.is_file():
            if worker.poll() is not None:
                pytest.fail(f"Probe worker exited early: {worker.returncode}")
            time.sleep(0.02)
        assert ready.is_file(), "Probe worker did not start"
        registry.register("demo", run_id, worker.pid)

        # First web process adopts the worker from the persistent registry.
        port_one = _free_port()
        log_one = tmp_path / "webserver-one.log"
        server_one = _start_webserver(
            repo_root=repo_root,
            overlay_root=overlay_root,
            project_base=project_base,
            state_home=state_home,
            port=port_one,
            log_path=log_one,
        )
        servers.append(server_one)
        first_state = _wait_for_server(
            server_one, f"http://127.0.0.1:{port_one}/api/projects/demo/loop",
            log_one,
        )
        assert first_state["state"] == "running"
        assert first_state["pid"] == worker.pid
        assert first_state["run_id"] == run_id
        assert first_state["run_context"] == context

        # Stop only the webserver; its independently launched loop worker survives.
        server_one.terminate()
        server_one.wait(timeout=8)
        assert worker.poll() is None

        # A fresh webserver process must recover the same PID and run context.
        port_two = _free_port()
        log_two = tmp_path / "webserver-two.log"
        server_two = _start_webserver(
            repo_root=repo_root,
            overlay_root=overlay_root,
            project_base=project_base,
            state_home=state_home,
            port=port_two,
            log_path=log_two,
        )
        servers.append(server_two)
        second_state = _wait_for_server(
            server_two, f"http://127.0.0.1:{port_two}/api/projects/demo/loop",
            log_two,
        )
        assert second_state == first_state
        assert worker.poll() is None
    finally:
        for server in servers:
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=8)
        if worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=8)
