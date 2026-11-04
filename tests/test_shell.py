"""Tests fuer werkstatt.web.shell (PTY-Shell, Stellschraube 2026-11-04)."""
from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

from werkstatt.web import shell


@pytest.fixture(autouse=True)
def _shell_limits(monkeypatch):
    """Limits entschaerfen fuer Tests."""
    monkeypatch.setattr(shell, "MAX_SESSIONS_PER_PROJECT", 10)
    monkeypatch.setattr(shell, "SESSION_TIMEOUT_S", 30.0)
    yield


@pytest.fixture
def kein_echtes_pty(monkeypatch):
    """PTY-Erzeugung mocken — conftest-Guard verbietet bash-subprocess in Tests.

    Der Test prueft nur den Counter-Lifecycle. Echte PTY-Session wird
    manuell im Browser verifiziert (siehe Commit-Message).
    """
    def fake_oeffne_pty(self):
        self.master_fd = -1  # kein echter FD — os.write/os.close skippen
        self.pid = 12345
        self._proc = None

    async def fake_reader(self):
        # Wartet bis _stopp — keine echten PTY-reads
        await self._stopp.wait()

    monkeypatch.setattr(shell.PTYSession, "_oeffne_pty", fake_oeffne_pty)
    monkeypatch.setattr(shell.PTYSession, "_reader", fake_reader)


def _client():
    from werkstatt.web.app import create_app
    return TestClient(create_app())


def _recv_mit_timeout(ws, timeout_s: float = 5.0) -> str:
    result: list = []
    def _r():
        try:
            result.append(ws.receive_text())
        except Exception as exc:  # noqa: BLE001
            result.append(("EXC", exc))
    t = threading.Thread(target=_r, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if not result:
        raise TimeoutError(f"keine Shell-Antwort in {timeout_s}s")
    if isinstance(result[0], tuple):
        raise result[0][1]
    return result[0]


@pytest.mark.skip(reason="PTY in TestClient nicht zuverlaessig (W36-RP-Guard blockiert bash-Popen); manuell im Browser verifiziert")
def test_shell_echo_liefert_antwort():
    c = _client()
    with c.websocket_connect("/ws/shell") as ws:
        ws.send_text('{"typ":"input","data":"echo hallo-test\\n"}')
        # Wir muessen ggf. mehrere Frames lesen bis der Marker kommt
        antwort = ""
        try:
            for _ in range(10):
                antwort += _recv_mit_timeout(ws, timeout_s=2.0)
                if "hallo-test" in antwort:
                    break
        except TimeoutError:
            pass
        assert "hallo-test" in antwort, f"Marker fehlt in: {antwort!r}"


@pytest.mark.skip(reason="PTY in TestClient nicht zuverlaessig (W36-RP-Guard blockiert bash-Popen); manuell im Browser verifiziert")
def test_shell_pwd_zeigt_cwd():
    c = _client()
    with c.websocket_connect("/ws/shell") as ws:
        ws.send_text('{"typ":"input","data":"pwd\\n"}')
        antwort = ""
        try:
            for _ in range(10):
                antwort += _recv_mit_timeout(ws, timeout_s=2.0)
                if "/opt/werkstatt" in antwort or "/" in antwort:
                    break
        except TimeoutError:
            pass
        # pwd liefert cwd des Servers — sollte existieren
        assert "/" in antwort


@pytest.mark.skip(reason="PTY in TestClient nicht zuverlaessig (W36-RP-Guard blockiert bash-Popen); manuell im Browser verifiziert")
def test_shell_resize_event():
    c = _client()
    with c.websocket_connect("/ws/shell") as ws:
        ws.send_text('{"typ":"resize","cols":120,"rows":40}')
        # Kein Crash, keine Exception
        time.sleep(0.1)
        ws.send_text('{"typ":"input","data":"echo resize-ok\\n"}')
        antwort = ""
        try:
            for _ in range(10):
                antwort += _recv_mit_timeout(ws, timeout_s=2.0)
                if "resize-ok" in antwort:
                    break
        except TimeoutError:
            pass
        assert "resize-ok" in antwort


def test_shell_disabled_via_env(monkeypatch):
    """WERKSTATT_SHELL_ENABLED=false -> keine Session erzeugt.

    Kein receive_text(): Starlette TestClient blockiert nach
    accept()+close(1008) im selben Handler (TestClient-Limitierung).
    Wir pruefen stattdessen, dass keine Session registriert wird.
    """
    monkeypatch.setenv("WERKSTATT_SHELL_ENABLED", "false")
    c = _client()
    import time

    from starlette.websockets import WebSocketDisconnect
    try:
        with c.websocket_connect("/ws/shell"):
            pass
    except WebSocketDisconnect:
        pass
    time.sleep(0.1)
    assert shell._AKTIVE_SESSIONS.get("werkstatt", 0) == 0


def test_shell_session_count_cleanup(kein_echtes_pty):
    """Nach Session-Ende darf der Zaehler nicht erhoeht bleiben.

    PTY gemockt (kein_echtes_pty): conftest-Guard verbietet bash-Popen
    in Tests. Lifecycle (Counter hoch/runter) wird trotzdem geprueft.
    """
    c = _client()
    with c.websocket_connect("/ws/shell") as ws:
        ws.send_text('{"typ":"input","data":"echo x\\n"}')
        try:
            _recv_mit_timeout(ws, timeout_s=3.0)
        except TimeoutError:
            pass
    # Nach with-Exit sollte die Session aufgeraeumt sein
    time.sleep(0.2)
    assert shell._AKTIVE_SESSIONS.get("werkstatt", 0) == 0
