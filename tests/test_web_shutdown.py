"""Webserver shutdown must not wait forever for persistent websocket clients."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


def _install_uvicorn_stub(monkeypatch, run) -> None:
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(run=run))


def test_web_entry_passes_bounded_graceful_shutdown_to_uvicorn(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(app: str, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    _install_uvicorn_stub(monkeypatch, fake_run)
    entry = importlib.reload(importlib.import_module("werkstatt.web.__main__"))
    from werkstatt.web import auth

    monkeypatch.setattr(sys, "argv", ["werkstatt.web", "--host", "0.0.0.0"])
    monkeypatch.setattr(auth, "get_token", lambda: "test-token")

    entry.main()

    assert captured["app"] == "werkstatt.web.app:app"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8001
    assert captured["timeout_graceful_shutdown"] == 10


def test_web_entry_allows_explicit_graceful_shutdown_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}
    _install_uvicorn_stub(
        monkeypatch,
        lambda _app, **kwargs: captured.update(kwargs),
    )
    entry = importlib.reload(importlib.import_module("werkstatt.web.__main__"))
    from werkstatt.web import auth
    monkeypatch.setattr(
        sys,
        "argv",
        ["werkstatt.web", "--timeout-graceful-shutdown", "4"],
    )
    monkeypatch.setattr(auth, "get_token", lambda: "test-token")

    entry.main()

    assert captured["timeout_graceful_shutdown"] == 4
