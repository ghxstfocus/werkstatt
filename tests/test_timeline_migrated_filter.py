"""OP-381f: aggregate_timeline ignoriert -migrated-*-Dateien.

Live-Bug 2026-11-09: aggregate_timeline nutzte
sorted(glob('agent-pipeline-*.jsonl'))[-1]. Alphabetisch letzte
Datei ist 'agent-pipeline-migrated-2026-11-08.jsonl' (weil 'm' > '2'),
eine statische DB-Dump-Datei aus OP-323. Die echte Tagesdatei wurde
nie gelesen — Timeline zeigte nur alte gate_open/answered aus
Oktober-Runs.

Fix: -migrated-Filter wie in Projector._jsonl_files().

Test-Isolation: inspector.werkstatt_home patchen (NICHT
paths.werkstatt_home — inspector bindet den Namen via
"from werkstatt.paths import werkstatt_home" lokal).
"""
from __future__ import annotations

import json

import pytest

from werkstatt import audit as _audit
from werkstatt import paths as _paths
from werkstatt.web import inspector


@pytest.fixture
def projektion(monkeypatch, tmp_path):
    """Patcht alle werkstatt_home-Bindings, die inspector/audit nutzen."""
    monkeypatch.setattr(_paths, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    # WICHTIG: inspector bindet werkstatt_home lokal via from-import
    monkeypatch.setattr(inspector, "werkstatt_home", lambda: tmp_path)
    yield tmp_path


def test_migrated_datei_wird_ignoriert(projektion, tmp_path):
    """Echte Tagesdatei + migrated-Datei -> Timeline liest nur echte."""
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)

    # Echte Tagesdatei: eigener run_id, enthaelt 'builder_patches_erstellt',
    # enthaelt KEIN 'gate_open' (der echte 191006-Run hat zwar ein Plan-Gate,
    # aber der Test isoliert: migrated darf NICHT reingezogen werden).
    echte_events = [
        {"kind": "loop_phase", "phase": "vorbereitung",
         "run_id": "run-echt", "project": "werkstatt",
         "timestamp": "2026-11-09T19:10:00+00:00"},
        {"kind": "explorer_result", "run_id": "run-echt",
         "project": "werkstatt",
         "timestamp": "2026-11-09T19:10:05+00:00"},
        {"kind": "builder_patches_erstellt", "run_id": "run-echt",
         "project": "werkstatt",
         "timestamp": "2026-11-09T19:15:00+00:00"},
    ]
    (d / "agent-pipeline-2026-11-09.jsonl").write_text(
        "\n".join(json.dumps(e) for e in echte_events) + "\n"
    )

    # Migrated-Datei: enthaelt 'gate_open' mit anderem run_id.
    # Wenn der Filter fehlt, wuerde sorted()[-1] diese Datei waehlen.
    alte_events = [
        {"kind": "loop_phase", "phase": "vorbereitung",
         "run_id": "run-alt", "project": "werkstatt",
         "timestamp": "2026-10-01T10:00:00+00:00"},
        {"kind": "gate_open", "gate_id": "g-alt-1", "run_id": "run-alt",
         "project": "werkstatt",
         "timestamp": "2026-10-01T10:00:01+00:00"},
    ]
    (d / "agent-pipeline-migrated-2026-11-08.jsonl").write_text(
        "\n".join(json.dumps(e) for e in alte_events) + "\n"
    )

    knoten = inspector.aggregate_timeline("werkstatt")
    alle_kinds = []
    for k in knoten:
        for c in k.get("children") or []:
            alle_kinds.append(c.get("kind"))

    assert "builder_patches_erstellt" in alle_kinds, (
        f"Timeline liest migrated statt echter Datei. "
        f"Kinds: {alle_kinds}, Knoten: {[k.get('label') for k in knoten]}"
    )
    assert "gate_open" not in alle_kinds, (
        f"gate_open aus migrated-Datei (run-alt) darf NICHT erscheinen. "
        f"Kinds: {alle_kinds}"
    )
