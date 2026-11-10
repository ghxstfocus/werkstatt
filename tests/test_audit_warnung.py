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
    import re
    from pathlib import Path

    from werkstatt.audit import _AUDIT_KINDS_BEKANNT

    kinds_im_code: set[str] = set()
    pat_audit = re.compile(r'\baudit(?:_safe)?\(\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_store = re.compile(r'append\([^)]*?kind\s*=\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_web = re.compile(r'_audit_web_loop_event\(\s*[^,]+,\s*[^,]+,\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_control = re.compile(r'_audit_loop_control\(\s*[^,]+,\s*[^,]+,\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_chat_job = re.compile(r'["\'](chat_job_[a-z_]+)["\']')
    for f in Path("werkstatt").rglob("*.py"):
        src = f.read_text(encoding="utf-8", errors="replace")
        for pat in (pat_audit, pat_store, pat_web, pat_control, pat_chat_job):
            if pat is pat_chat_job and f.name == "audit.py":
                continue
            for m in pat.finditer(src):
                kinds_im_code.add(m.group(1))

    fehlend = sorted(kinds_im_code - _AUDIT_KINDS_BEKANNT)
    assert not fehlend, (
        f"{len(fehlend)} Kinds im Code fehlen im Katalog: {fehlend[:20]}"
    )


def test_katalog_enthaelt_keine_toten_kinds():
    """Jeder Katalog-Eintrag wird von werkstatt/*.py auch gerufen.

    Ein toter Eintrag ist Alt-Last: kein Aufrufer, keine externe
    Quelle. Loeschen, nicht behalten.
    """
    import re
    from pathlib import Path

    from werkstatt.audit import _AUDIT_KINDS_BEKANNT

    kinds_im_code: set[str] = set()
    pat_audit = re.compile(r'\baudit(?:_safe)?\(\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_store = re.compile(r'append\([^)]*?kind\s*=\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_web = re.compile(r'_audit_web_loop_event\(\s*[^,]+,\s*[^,]+,\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_control = re.compile(r'_audit_loop_control\(\s*[^,]+,\s*[^,]+,\s*["\']([a-z_][a-z0-9_]*)["\']')
    pat_chat_job = re.compile(r'["\'](chat_job_[a-z_]+)["\']')
    for f in Path("werkstatt").rglob("*.py"):
        src = f.read_text(encoding="utf-8", errors="replace")
        for pat in (pat_audit, pat_store, pat_web, pat_control, pat_chat_job):
            if pat is pat_chat_job and f.name == "audit.py":
                continue
            for m in pat.finditer(src):
                kinds_im_code.add(m.group(1))

    tot = sorted(_AUDIT_KINDS_BEKANNT - kinds_im_code)
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
