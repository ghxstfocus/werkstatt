"""Tests fuer das FastAPI-Backend (OP-074)."""

import os
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



def test_start_verwirft_op_mit_unbekanntem_blocker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "### OP-002: Arbeit mit unbekannter Voraussetzung\n"
        "- **Status:** open\n"
        "- **Blockiert von:** OP-999\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_002.py\n",
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
    assert "Unbekannte oder widerspruechliche Blocker" in antwort.json()["detail"]
    assert aufrufe == []


def test_start_verwirft_op_mit_doppelter_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    op = (
        "### OP-002: Doppelte Aufgabe\n"
        "- **Status:** open\n"
        "- **Blockiert von:** —\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_002.py\n"
    )
    (docs_dir / "STATUS.md").write_text(op + "\n" + op, encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    client = TestClient(app_modul.app)

    antwort = client.post(
        "/api/projects/demo/start", json={"op_id": "OP-002"},
    )

    assert antwort.status_code == 409
    assert "OP-ID kommt mehrfach" in antwort.json()["detail"]
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
    audit_events: list[tuple[Any, ...]] = []

    def _capture_audit(project: str, run_id: str, kind: str, status: str, payload: dict[str, Any]) -> bool:
        audit_events.append((project, run_id, kind, status, payload))
        return True

    monkeypatch.setattr(app_modul, "_audit_web_loop_event", _capture_audit)

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
    assert [event[2] for event in audit_events] == [
        "web_loop_paused", "web_loop_resumed", "web_loop_stopped",
    ]
    assert [event[0] for event in audit_events] == ["demo"] * 3
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


def test_loop_status_recovery_nach_server_neustart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul
    from werkstatt.web.loop_registry import LoopProcessRegistry

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("## Open\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)

    registry = LoopProcessRegistry(
        tmp_path / ".werkstatt" / "web-loop-registry.db",
    )
    assert registry.reserve("demo", "run-after-restart") == (True, None)
    registry.register("demo", "run-after-restart", os.getpid())

    # Simulate a fresh web worker: only the durable process record remains.
    _reset_loop_registry(app_modul)
    monkeypatch.setattr(
        app_modul.subprocess, "Popen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("duplicate start")),
    )
    client = TestClient(app_modul.app)

    state = client.get("/api/projects/demo/loop")
    assert state.status_code == 200
    assert state.json()["state"] == "running"
    assert state.json()["run_id"] == "run-after-restart"

    start = client.post(
        "/api/projects/demo/start", json={"aufgabe": "must not start twice"},
    )
    assert start.status_code == 200
    assert start.json()["gestartet"] is False
    assert start.json()["grund"] == "laeuft_bereits"



def test_idle_loop_state_does_not_expose_stale_run_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul
    from werkstatt.web.loop_registry import LoopProcessRegistry

    (tmp_path / "demo" / "docs").mkdir(parents=True)
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    registry = LoopProcessRegistry(tmp_path / ".werkstatt" / "web-loop-registry.db")
    assert registry.reserve("demo", "run-stale") == (True, None)

    client = TestClient(app_modul.app)
    starting = client.get("/api/projects/demo/loop").json()
    assert starting["state"] == "starting"
    assert starting["run_id"] == "run-stale"

    assert registry.set_state("demo", "run-stale", "idle") is True
    idle = client.get("/api/projects/demo/loop").json()
    assert idle == {"state": "idle", "pid": None, "run_id": None}


def test_start_waehlt_einzige_pruefbare_offene_op(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "### OP-101: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Blockiert von:** —\n"
        "- **Akzeptanzkriterien:** Verhalten ist belegt.\n"
        "- **Tests:** pytest -q tests/test_feature.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    audit_events: list[tuple[Any, ...]] = []

    def _capture_audit(project: str, run_id: str, kind: str, status: str, payload: dict[str, Any]) -> bool:
        audit_events.append((project, run_id, kind, status, payload))
        return True

    monkeypatch.setattr(app_modul, "_audit_web_loop_event", _capture_audit)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    client = TestClient(app_modul.app)

    antwort = client.post("/api/projects/demo/start")

    assert antwort.status_code == 200
    assert antwort.json()["op_id"] == "OP-101"
    assert audit_events[0][0] == "demo"
    assert audit_events[0][2] == "web_op_selected"
    assert audit_events[0][4]["op_id"] == "OP-101"
    assert antwort.json()["auswahl"]["id"] == "OP-101"
    assert "### OP-101:" in antwort.json()["aufgabe"]
    assert aufrufe


def test_start_fragt_bei_mehreren_pruefbaren_ops_nach(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    one = (
        "### OP-101: Erstes Thema\n- **Status:** open\n"
        "- **Blockiert von:** —\n"
        "- **Akzeptanzkriterien:** Prüfergebnis A.\n"
        "- **Tests:** pytest -q tests/test_a.py\n"
    )
    two = one.replace("OP-101: Erstes Thema", "OP-102: Zweites Thema").replace(
        "Prüfergebnis A", "Prüfergebnis B"
    ).replace("test_a.py", "test_b.py")
    (docs_dir / "STATUS.md").write_text(one + "\n" + two, encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    monkeypatch.setattr(app_modul, "EventStore", _NullEventStore)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    client = TestClient(app_modul.app)

    antwort = client.post("/api/projects/demo/start")

    assert antwort.status_code == 409
    detail = antwort.json()["detail"]
    assert detail["code"] == "autonomy_selection_required"
    assert [item["id"] for item in detail["kandidaten"]] == ["OP-101", "OP-102"]
    assert aufrufe == []


def test_explicit_op_start_respects_phase_three_dogfooding_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "### OP-101: Phase-3-Aufgabe\n"
        "- **Status:** open\n"
        "- **Phase:** Phase-3 (Memory)\n"
        "- **Blockiert von:** —\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_101.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    client = TestClient(app_modul.app)

    antwort = client.post("/api/projects/demo/start", json={"op_id": "OP-101"})

    assert antwort.status_code == 409
    assert "Phase-3 gesperrt" in antwort.json()["detail"]
    assert aufrufe == []


def test_direct_task_precedes_invalid_op_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# no OP needed\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    client = TestClient(app_modul.app)

    antwort = client.post(
        "/api/projects/demo/start",
        json={"op_id": "not-an-op", "aufgabe": "Direkter Auftrag"},
    )

    assert antwort.status_code == 200
    assert antwort.json()["op_id"] is None
    assert antwort.json()["aufgabe"] == "Direkter Auftrag"
    assert aufrufe[0][aufrufe[0].index("--aufgabe") + 1] == "Direkter Auftrag"



def test_autonomous_start_resolves_dependency_completed_in_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "### OP-322: Arbeit nach erledigtem OP\n"
        "- **Status:** open\n"
        "- **Blockiert von:** OP-201\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_322.py\n",
        encoding="utf-8",
    )
    (tmp_path / "demo" / "PROGRESS.md").write_text(
        "### 2026-11-07 — OP-201 abgeschlossen: Paket-Registrierung\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    if app_modul.os.name == "posix":
        monkeypatch.setattr(app_modul.os, "killpg", lambda *_: None)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    monkeypatch.setattr(app_modul, "EventStore", _NullEventStore)

    client = TestClient(app_modul.app)
    antwort = client.post("/api/projects/demo/start")

    assert antwort.status_code == 200
    assert antwort.json()["gestartet"] is True
    task_idx = aufrufe[0].index("--aufgabe")
    assert "### OP-322: Arbeit nach erledigtem OP" in aufrufe[0][task_idx + 1]
    assert client.post("/api/projects/demo/stop").status_code == 200



def test_autonomous_start_uses_status_done_ledger_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text(
        "## Erledigt (Auto-Log)\n"
        "- 2026-11-09 | OP-381c | done | Gate-Modal fertig.\n\n"
        "### OP-322: Arbeit nach erledigtem Gate-Modal\n"
        "- **Status:** open\n"
        "- **Blockiert von:** OP-381c\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_322.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)
    if app_modul.os.name == "posix":
        monkeypatch.setattr(app_modul.os, "killpg", lambda *_: None)
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    monkeypatch.setattr(app_modul, "EventStore", _NullEventStore)

    client = TestClient(app_modul.app)
    antwort = client.post("/api/projects/demo/start")

    assert antwort.status_code == 200
    assert antwort.json()["op_id"] == "OP-322"
    assert client.post("/api/projects/demo/stop").status_code == 200

def test_live_worker_reconciles_pause_from_shared_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Ein Web-Worker sieht Pause/Resume-Aenderungen eines anderen Workers."""
    if os.name != "posix":
        pytest.skip("Pause/Resume nutzt POSIX-Signale")
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    docs_dir = tmp_path / "demo" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "STATUS.md").write_text("# shared worker test\n", encoding="utf-8")
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    _reset_loop_registry(app_modul)

    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))
    signale: list[tuple[int, int]] = []
    monkeypatch.setattr(
        app_modul.os, "killpg",
        lambda pgid, sig: signale.append((pgid, sig)),
    )
    monkeypatch.setattr(app_modul, "_audit_web_loop_event", lambda *_args: True)

    client = TestClient(app_modul.app)
    gestartet = client.post(
        "/api/projects/demo/start", json={"aufgabe": "shared state test"},
    )
    assert gestartet.status_code == 200
    pid = gestartet.json()["pid"]
    run_id = gestartet.json()["run_id"]

    # Simuliere die persistierte Pause durch einen anderen ASGI-Worker.
    registry = app_modul._loop_registry()
    assert registry.set_state("demo", run_id, "paused") is True
    app_modul._PAUSIERTE_LOOPS.clear()

    state = client.get("/api/projects/demo/loop")
    assert state.status_code == 200
    assert state.json() == {
        "state": "paused", "pid": pid, "run_id": run_id,
    }

    resume = client.post("/api/projects/demo/resume")
    assert resume.status_code == 200
    assert resume.json()["fortgesetzt"] is True
    assert resume.json().get("bereits_laufend") is not True
    assert signale == [(pid, signal.SIGCONT)]
    assert registry.read("demo")["state"] == "running"

    stop = client.post("/api/projects/demo/stop")
    assert stop.status_code == 200
    assert stop.json()["gestoppt"] is True

