"""Multi-Projekt-Gate-Kontext liest den Diff aus dem angefragten Projekt."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from werkstatt.web import inspector


class _GateStore:
    def query(
        self,
        run_id: str,
        kind: str | None = None,
        *,
        project: str | None = None,
    ) -> list[dict[str, Any]]:
        if kind == "gate_open":
            return [{
                "payload": {
                    "gate_id": "gate-1",
                    "prompt": "Plan prüfen",
                    "optionen": "jna",
                },
            }]
        return []


def _prepare(monkeypatch, root: Path) -> list[str]:
    monkeypatch.setattr(inspector, "_PROJECTS_BASE", root)
    monkeypatch.setattr(inspector, "_frische_projektion", lambda: None)
    monkeypatch.setattr(inspector, "_audit_events", lambda _run_id, _project: [])
    monkeypatch.setattr(
        inspector, "_lese_phase_yaml_aufgabe", lambda _projekt: None,
    )
    monkeypatch.setattr(inspector, "EventStore", _GateStore)
    cwds: list[str] = []

    def fake_run(*_args, **kwargs):
        cwds.append(kwargs["cwd"])
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return cwds


def test_gate_context_liest_diff_aus_gewaehltem_projekt(tmp_path, monkeypatch):
    project = tmp_path / "demo"
    project.mkdir()
    cwds = _prepare(monkeypatch, tmp_path)

    context = inspector.aggregate_gate_context("demo", run_id="demo-run")

    assert len(context["offene_gates"]) == 1
    assert cwds == [str(project.resolve()), str(project.resolve())]


def test_gate_context_gibt_keinen_diff_ausserhalb_projektbasis_aus(
    tmp_path, monkeypatch,
):
    outside = tmp_path.parent / "outside-project"
    outside.mkdir()
    cwds = _prepare(monkeypatch, tmp_path)

    context = inspector.aggregate_gate_context("../outside-project", run_id="demo-run")

    assert context["offene_gates"]
    assert cwds == []
