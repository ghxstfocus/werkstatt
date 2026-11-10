"""Tests fuer das FastAPI-Backend (OP-074)."""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any

import pytest


def _fake_popen(aufrufe: list[list[str]], pid: int = 4242) -> Any:
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
        return _FakeProzess(list(argv))

    return _popen


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
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

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
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()
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
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()
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
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()

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
