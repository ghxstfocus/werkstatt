"""Tests fuer das FastAPI-Backend (OP-074)."""

import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any

import pytest


def _fake_popen(
    aufrufe: list[list[str]],
    pid: int = 4242,
    kwargs_log: list[dict[str, Any]] | None = None,
) -> Any:
    """Fabrik fuer einen Fake-Popen, der argv protokolliert."""

    class _FakeProzess:
        def __init__(self, argv: list[str]) -> None:
            self.argv = argv
            self.pid = pid
            self.returncode: int | None = None
            self.terminated = False
            self.killed = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: int | None = None) -> int:
            self.returncode = 0
            return self.returncode

    def _popen(argv: list[str], *args: Any, **kwargs: Any) -> _FakeProzess:
        aufrufe.append(list(argv))
        if kwargs_log is not None:
            kwargs_log.append(dict(kwargs))
        return _FakeProzess(list(argv))

    return _popen


class _NullEventStore:
    def append(self, *args: Any, **kwargs: Any) -> None:
        return None


def _reset_loop_registry(app_modul: Any) -> None:
    for log_handle in app_modul._LOOP_LOG_HANDLES.values():
        log_handle.close()
    app_modul._LOOP_LOG_HANDLES.clear()
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_RUN_IDS.clear()
    app_modul._PAUSIERTE_LOOPS.clear()


def test_loop_subprozess_start_stop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    # OP-305: /start pruefen wir mit _PROJECTS_BASE = tmp_path
    # (Path("/opt") wuerde auf echte Verzeichnisse schauen)
    demo_dir = tmp_path / "demo" / "docs"
    demo_dir.mkdir(parents=True)
    (demo_dir / "STATUS.md").write_text(
        "### OP-999: Test\n- **Status:** open\n- **Blockiert von:** —\n"
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)

    aufrufe: list[list[str]] = []
    popen_kwargs: list[dict[str, Any]] = []
    gruppensignale: list[tuple[int, int]] = []
    if app_modul.os.name == "posix":
        monkeypatch.setattr(
            app_modul.os, "killpg",
            lambda pgid, sig: gruppensignale.append((pgid, sig)),
        )
    _reset_loop_registry(app_modul)
    monkeypatch.setattr(
        app_modul.subprocess, "Popen",
        _fake_popen(aufrufe, kwargs_log=popen_kwargs),
    )
    monkeypatch.setattr(app_modul, "EventStore", _NullEventStore)

    client = TestClient(app_modul.app)

    antwort = client.post(
        "/api/projects/demo/start", json={"op_id": "OP-999"},
    )
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["gestartet"] is True
    assert daten["pid"] == 4242
    assert aufrufe[0][:5] == [
        sys.executable,
        "-m",
        "werkstatt.loop",
        "--project",
        "demo",
    ]
    assert "--headless" in aufrufe[0]
    assert "--run-id" in aufrufe[0]
    assert "--aufgabe" in aufrufe[0]
    task_idx = aufrufe[0].index("--aufgabe")
    assert "### OP-999: Test" in aufrufe[0][task_idx + 1]
    run_id_idx = aufrufe[0].index("--run-id")
    assert aufrufe[0][run_id_idx + 1].startswith("demo-")
    assert daten["run_id"] == aufrufe[0][run_id_idx + 1]
    assert popen_kwargs[0]["start_new_session"] is (app_modul.os.name == "posix")
    assert "demo" in app_modul._LAUFENDE_LOOPS

    zweite = client.post("/api/projects/demo/start")
    assert zweite.status_code == 200
    assert zweite.json()["gestartet"] is False
    assert len(aufrufe) == 1

    stop = client.post("/api/projects/demo/stop")
    assert stop.status_code == 200
    stop_daten = stop.json()
    assert stop_daten["gestoppt"] is True
    assert stop_daten["returncode"] == 0
    if app_modul.os.name == "posix":
        assert gruppensignale == [(daten["pid"], signal.SIGTERM)]
    assert "demo" not in app_modul._LAUFENDE_LOOPS


def test_start_verwirft_blockierte_op(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "### OP-001: Voraussetzung\n- **Status:** open\n- **Blockiert von:** —\n\n"
        "### OP-002: Folgearbeit\n- **Status:** open\n- **Blockiert von:** OP-001\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    client = TestClient(app_modul.app)
    antwort = client.post(
        "/api/projects/demo/start", json={"op_id": "OP-002"},
    )

    assert antwort.status_code == 409
    assert "blockiert" in antwort.json()["detail"]
    assert aufrufe == []


def test_start_verwirft_leere_aufgabe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# keine OP\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    client = TestClient(app_modul.app)
    antwort = client.post("/api/projects/demo/start")

    assert antwort.status_code == 422
    assert aufrufe == []



def test_parallele_starts_starten_nur_einen_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# start concurrent test\n")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    if app_modul.os.name == "posix":
        monkeypatch.setattr(app_modul.os, "killpg", lambda *_: None)

    entered = Event()
    release = Event()
    aufrufe: list[list[str]] = []
    normal = _fake_popen(aufrufe)

    def langsamer_popen(argv: list[str], *args: Any, **kwargs: Any) -> Any:
        entered.set()
        if not release.wait(timeout=5):
            raise AssertionError("test did not release Popen")
        return normal(argv, *args, **kwargs)

    monkeypatch.setattr(app_modul.subprocess, "Popen", langsamer_popen)
    client = TestClient(app_modul.app)

    with ThreadPoolExecutor(max_workers=2) as pool:
        erster = pool.submit(
            client.post, "/api/projects/demo/start",
            json={"aufgabe": "concurrency test"},
        )
        assert entered.wait(timeout=2)
        zweiter = pool.submit(
            client.post, "/api/projects/demo/start",
            json={"aufgabe": "concurrency test"},
        )
        release.set()
        antworten = [erster.result(timeout=5), zweiter.result(timeout=5)]

    assert all(antwort.status_code == 200 for antwort in antworten)
    assert sum(bool(antwort.json()["gestartet"]) for antwort in antworten) == 1
    assert len(aufrufe) == 1
    assert client.post("/api/projects/demo/stop").status_code == 200


def test_pause_resume_loop_control(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import os

    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    if os.name != "posix":
        pytest.skip("Pause/Resume nutzt POSIX-Signale")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# pause/resume test\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    app_modul._LOOP_RUN_IDS.clear()
    app_modul._PAUSIERTE_LOOPS.clear()

    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    signale: list[tuple[int, int]] = []
    monkeypatch.setattr(
        app_modul.os, "killpg",
        lambda pgid, sig: signale.append((pgid, sig)),
    )
    audit_events: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    class _FakeEventStore:
        def append(self, *args: Any, **kwargs: Any) -> None:
            audit_events.append((args, kwargs))

    monkeypatch.setattr(app_modul, "EventStore", _FakeEventStore)

    client = TestClient(app_modul.app)
    gestartet = client.post(
        "/api/projects/demo/start", json={"aufgabe": "pause test"},
    )
    assert gestartet.status_code == 200
    pid = gestartet.json()["pid"]

    pause = client.post("/api/projects/demo/pause")
    assert pause.status_code == 200
    assert pause.json()["pausiert"] is True
    assert pause.json()["audit_event"] is True
    assert signale == [(pid, signal.SIGSTOP)]
    assert client.get("/api/projects/demo/loop").json()["state"] == "paused"

    resume = client.post("/api/projects/demo/resume")
    assert resume.status_code == 200
    assert resume.json()["fortgesetzt"] is True
    assert resume.json()["audit_event"] is True
    assert signale[-1] == (pid, signal.SIGCONT)
    assert client.get("/api/projects/demo/loop").json()["state"] == "running"

    stop = client.post("/api/projects/demo/stop")
    assert stop.status_code == 200
    assert stop.json()["gestoppt"] is True
    assert stop.json()["audit_event"] is True
    assert signale[-1] == (pid, signal.SIGTERM)
    assert [event[0][1] for event in audit_events] == [
        "web_loop_paused", "web_loop_resumed", "web_loop_stopped",
    ]
    assert "demo" not in app_modul._LAUFENDE_LOOPS


def test_stop_eskaliert_an_prozessgruppe_nach_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import os

    if os.name != "posix":
        pytest.skip("Prozessgruppen-Stop nutzt POSIX-Signale")
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# process group timeout\\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)

    class _TimeoutProzess:
        pid = 4242
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def wait(self, timeout: int | None = None) -> int:
            if self.returncode is None:
                raise app_modul.subprocess.TimeoutExpired("loop", timeout)
            return self.returncode

    process = _TimeoutProzess()
    monkeypatch.setattr(
        app_modul.subprocess, "Popen",
        lambda *args, **kwargs: process,
    )
    signale: list[tuple[int, int]] = []

    def _killpg(pgid: int, sig: int) -> None:
        signale.append((pgid, sig))
        if sig == signal.SIGKILL:
            process.returncode = -signal.SIGKILL

    monkeypatch.setattr(app_modul.os, "killpg", _killpg)
    monkeypatch.setattr(app_modul, "EventStore", _NullEventStore)

    client = TestClient(app_modul.app)
    start = client.post(
        "/api/projects/demo/start", json={"aufgabe": "timeout test"},
    )
    assert start.status_code == 200
    stop = client.post("/api/projects/demo/stop")

    assert stop.status_code == 200
    assert signale == [
        (process.pid, signal.SIGTERM),
        (process.pid, signal.SIGKILL),
    ]
    assert stop.json()["returncode"] == -signal.SIGKILL
