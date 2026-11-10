"""Tests fuer POST /start — Volltext-Kontext, --fresh, stderr-Umleitung.

Regress-Barriere fuer drei Bugs (2026-11-10):
- POST /start uebergab nur "OP-XXX: Titel" -> Explorer hatte 0
  Suchbegriffe -> explorer_context=[] -> state_contract_violation.
- POST /start ohne --fresh -> Resume-Pfad lud alte .phase.yaml.
- Popen ohne stderr/stderr-Redirect -> Loop-Crash unsichtbar.
"""
from __future__ import annotations

from typing import Any

import pytest


def _fake_popen(aufrufe: list[list[str]]) -> Any:
    class _FakeProzess:
        def __init__(self) -> None:
            self.pid = 4243
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = 0

        def wait(self, timeout: int | None = None) -> int:
            return 0

    def _popen(argv: list[str], *args: Any, **kwargs: Any) -> _FakeProzess:
        aufrufe.append(list(argv))
        return _FakeProzess()

    return _popen


@pytest.fixture
def client_mit_projekt(monkeypatch, tmp_path):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul
    from werkstatt.web import auth as auth_mod

    monkeypatch.setattr(auth_mod, "_AUTH_DISABLED", True)
    demo_dir = tmp_path / "demo" / "docs"
    demo_dir.mkdir(parents=True)
    (demo_dir / "STATUS.md").write_text(
        "### OP-999: Test-Aufgabe\n"
        "\n"
        "- **Status:** open\n"
        "- **Betroffen:** `werkstatt/web/auth.py`\n"
        "- **Problem:** `require_ws_auth` ist dupliziert.\n"
        "\n"
        "### OP-1000: Naechster\n"
        "- **Status:** open\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()
    client = TestClient(app_modul.create_app())
    yield client, app_modul, tmp_path
    for fh in app_modul._LOOP_LOG_HANDLES.values():
        try:
            fh.close()
        except OSError:
            pass
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_LOG_HANDLES.clear()


def test_start_mit_op_id_uebergibt_volltext(client_mit_projekt, monkeypatch):
    """POST /start mit op_id -> --aufgabe enthaelt den VOLLEN OP-Block."""
    client, app_modul, _ = client_mit_projekt
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    r = client.post("/api/projects/demo/start", json={"op_id": "OP-999"})
    assert r.status_code == 200, r.text
    assert aufrufe, "Popen wurde nicht aufgerufen"
    argv = aufrufe[0]
    idx = argv.index("--aufgabe")
    aufgabe = argv[idx + 1]
    assert "require_ws_auth" in aufgabe, f"Suchbegriff fehlt: {aufgabe[:300]!r}"
    assert "### OP-999" in aufgabe
    assert "### OP-1000" not in aufgabe, "Nachfolge-OP darf nicht mit"


def test_start_fuegt_fresh_hinzu(client_mit_projekt, monkeypatch):
    """POST /start uebergibt --fresh, damit alte .phase.yaml nicht greift."""
    client, app_modul, _ = client_mit_projekt
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    r = client.post("/api/projects/demo/start", json={"op_id": "OP-999"})
    assert r.status_code == 200, r.text
    assert "--fresh" in aufrufe[0], aufrufe[0]


def test_start_legt_log_datei_an(client_mit_projekt, monkeypatch):
    """POST /start leitet stdout/stderr in <project>/.werkstatt/logs/loop-*.log."""
    client, app_modul, tmp_path = client_mit_projekt
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    r = client.post("/api/projects/demo/start", json={"op_id": "OP-999"})
    assert r.status_code == 200, r.text
    log_dir = tmp_path / "demo" / ".werkstatt" / "logs"
    assert log_dir.is_dir(), f"Log-Verzeichnis fehlt: {log_dir}"
    logs = list(log_dir.glob("loop-*.log"))
    assert logs, f"kein Log-File in {log_dir}"


def test_start_ohne_body_verwirft_leere_aufgabe(client_mit_projekt, monkeypatch):
    """Ohne Auftrag darf kein leerer Loop gestartet werden."""
    client, app_modul, _ = client_mit_projekt
    aufrufe: list[list[str]] = []
    monkeypatch.setattr(app_modul.subprocess, "Popen", _fake_popen(aufrufe))

    r = client.post("/api/projects/demo/start")
    assert r.status_code == 422
    assert aufrufe == []
