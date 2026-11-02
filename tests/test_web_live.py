import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from werkstatt.web import terminal_proxy
from werkstatt.web.app import create_app


def _ws_receive_json_mit_timeout(ws, timeout_s: float = 3.0):
    """receive_json mit Timeout.

    TestClient/Starlette hat kein nativens WS-Timeout; ohne Wrapper
    blockiert receive_json() unendlich, wenn keine Nachricht kommt
    (siehe OP-082 test_ws_terminal und heutiger OP-083-Lauf).
    """
    import threading

    result: list = []
    def _recv() -> None:
        try:
            result.append(("ok", ws.receive_json()))
        except Exception as exc:  # noqa: BLE001
            result.append(("err", exc))

    t = threading.Thread(target=_recv, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if not result:
        raise TimeoutError(f"keine WS-Nachricht in {timeout_s}s")
    kind, payload = result[0]
    if kind == "err":
        raise payload
    return payload


@pytest.fixture
def audit_verzeichnis(tmp_path, monkeypatch):
    verzeichnis = tmp_path / "audit-logs"
    verzeichnis.mkdir()
    log = verzeichnis / "agent-pipeline-test.jsonl"
    log.write_text("")
    monkeypatch.setattr(
        terminal_proxy, "_audit_log_verzeichnis", lambda project: verzeichnis
    )
    monkeypatch.setattr(terminal_proxy, "_POLL_INTERVALL_S", 0.02)
    return verzeichnis, log


def test_ws_empfaengt_neue_zeile(audit_verzeichnis):
    verzeichnis, log = audit_verzeichnis
    client = TestClient(create_app())

    with client.websocket_connect("/ws/terminal/testprojekt") as ws:
        with log.open("a") as f:
            f.write(json.dumps({"typ": "test_event", "text": "hallo"}) + "\n")
        daten = _ws_receive_json_mit_timeout(ws, timeout_s=3.0)

    assert daten["typ"] == "audit"
    assert daten["event"]["typ"] == "test_event"
    assert daten["event"]["text"] == "hallo"


def test_tab_wechsel_schliesst_vorherige_ws(audit_verzeichnis):
    verzeichnis, log = audit_verzeichnis
    client = TestClient(create_app())

    with client.websocket_connect("/ws/terminal/testprojekt") as ws_a:
        assert terminal_proxy._AKTIVE_VERBINDUNGEN.get("testprojekt", 0) == 1

    assert terminal_proxy._AKTIVE_VERBINDUNGEN.get("testprojekt", 0) == 0

    with client.websocket_connect("/ws/terminal/testprojekt") as ws_b:
        assert terminal_proxy._AKTIVE_VERBINDUNGEN.get("testprojekt", 0) == 1

    quelle = Path("static/tabs.js").read_text(encoding="utf-8")
    assert quelle.index("// OP-083: erst schliessen") < quelle.index(
        "// OP-083: dann oeffnen"
    )
