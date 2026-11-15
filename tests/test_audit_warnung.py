"""Spec: audit() warnt bei unbekanntem Kind, bricht aber nicht."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from werkstatt import audit as audit_mod


def _events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def test_audit_unbekannter_kind_warnt(tmp_path, capsys):
    """Unbekannter Kind wird geschrieben UND warnt auf stderr."""
    audit_mod.audit("voellig_neuer_kind", {"x": 1},
                    tmp_path, "testproj")
    ev = [e for e in _events(tmp_path)
          if e.get("kind") == "voellig_neuer_kind"]
    assert len(ev) == 1
    cap = capsys.readouterr()
    assert "voellig_neuer_kind" in cap.err
    assert "unbekannter kind" in cap.err


def test_audit_bekannter_kind_keine_warnung(tmp_path, capsys):
    """Bekannter Kind: keine Warnung."""
    audit_mod.audit("llm_call", {"x": 1}, tmp_path, "testproj")
    cap = capsys.readouterr()
    assert "unbekannter kind" not in cap.err


def test_audit_unbekannter_kind_schreibt_trotzdem(tmp_path):
    """Fail-safe: Audit bricht nie, schreibt immer."""
    audit_mod.audit("ganz_neuer_kind", {"y": 2},
                    tmp_path, "testproj")
    ev = [e for e in _events(tmp_path)
          if e.get("kind") == "ganz_neuer_kind"]
    assert len(ev) == 1
    assert ev[0]["y"] == 2


# =====================================================================
# GOLD 2026-10-30: Katalog == Code-Kinds
# =====================================================================

def test_katalog_enthaelt_alle_code_kinds():
    """Jeder audit("kind", ...)-Aufruf in werkstatt/*.py muss im
    Katalog stehen. Verhindert kuenftigen Drift automatisch.

    Wenn dieser Test rot wird: neuen Kind in _AUDIT_KINDS_BEKANNT
    in werkstatt/audit.py ergaenzen.
    """
    from tools.audit_drift import finde_code_kinds, finde_katalog

    kinds_im_code = finde_code_kinds()
    katalog = finde_katalog()

    fehlend = sorted(kinds_im_code - katalog)
    assert not fehlend, (
        f"{len(fehlend)} Kinds im Code fehlen im Katalog: {fehlend[:20]}"
    )


def test_katalog_enthaelt_keine_toten_kinds():
    """Jeder Katalog-Eintrag wird von werkstatt/*.py auch gerufen.

    Ein toter Eintrag ist Alt-Last: kein Aufrufer, keine externe
    Quelle. Loeschen, nicht behalten.
    """
    from tools.audit_drift import finde_code_kinds, finde_katalog

    kinds_im_code = finde_code_kinds()
    katalog = finde_katalog()

    tot = sorted(katalog - kinds_im_code)
    assert not tot, (
        f"{len(tot)} tote Katalog-Eintraege (kein Code-Aufruf): {tot[:20]}"
    )


def test_audit_explicit_run_and_event_id_are_replay_stable(tmp_path, monkeypatch):
    from werkstatt import event_store, projection

    monkeypatch.setattr(audit_mod, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(event_store, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    assert audit_mod.audit(
        "web_loop_paused", {"status": "paused"}, tmp_path, "demo",
        run_id="run-explicit", event_id="stable-web-event-1",
    )
    projector = projection.Projector()
    projector.rebuild()
    events = event_store.EventStore(
        db_pfad=tmp_path / ".werkstatt" / "events.db",
    ).query("run-explicit", project="demo")
    assert len(events) == 1
    assert events[0]["kind"] == "web_loop_paused"
    with sqlite3.connect(tmp_path / ".werkstatt" / "events.db") as conn:
        projected_id = conn.execute(
            "SELECT event_id FROM events WHERE run_id=? AND kind=?",
            ("run-explicit", "web_loop_paused"),
        ).fetchone()[0]
    assert projected_id == "stable-web-event-1"
