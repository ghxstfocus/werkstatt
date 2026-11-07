"""Inspector-Aggregatoren fuer das Web-UI (OP-233).

Drei Funktionen, je eine Datenquelle:
  parse_ops      -- offene + erledigte OPs aus docs/STATUS.md
  aggregate_status -- Tasks/Verify/Drift/Phase aus Event-Store
  aggregate_timeline -- Phasen-Knoten aus Event-Store + JSONL-Audit
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from werkstatt.event_store import EventStore
from werkstatt.paths import werkstatt_home

__all__ = ["aggregate_status", "aggregate_timeline", "aggregate_tokens", "parse_ops"]

_OPS_RE = re.compile(r"^### (OP-\d+):\s*(.+?)\s*$", re.MULTILINE)
_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(\S+)", re.IGNORECASE)

_PHASEN_PREFIXE = (
    "explorer_", "scout_", "architect_", "planner_",
    "builder_", "reviewer_", "reflection_",
    "verify_", "loop_plan_gate_", "loop_human_gate_",
)
_PHASEN_LABELS = {
    "explorer_": "Explorer",
    "scout_": "Scout",
    "architect_": "Architect",
    "planner_": "Planner",
    "builder_": "Builder",
    "reviewer_": "Reviewer",
    "reflection_": "Reflection",
    "verify_": "Verify",
    "loop_plan_gate_": "Plan-Gate",
    "loop_human_gate_": "Human-Gate",
}


def parse_ops(projekt_dir: Path | None = None) -> list[dict[str, str]]:
    """Listet OPs aus docs/STATUS.md (Reihenfolge wie im Dokument)."""
    basis = Path(projekt_dir) if projekt_dir else Path("/opt/werkstatt")
    pfad = basis / "docs" / "STATUS.md"
    if not pfad.exists():
        return []
    text = pfad.read_text(encoding="utf-8")
    treffer = list(_OPS_RE.finditer(text))
    ergebnis: list[dict[str, str]] = []
    for i, m in enumerate(treffer):
        op_id, titel = m.group(1), m.group(2).strip()
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        block = text[m.end():ende]
        sm = _STATUS_RE.search(block)
        status = sm.group(1).lower() if sm else "?"
        ergebnis.append({
            "id": op_id,
            "titel": titel,
            "status": status,
        })
    return ergebnis


def _letzter_run_id(es: EventStore) -> str | None:
    try:
        with sqlite3.connect(es.db_pfad) as c:
            row = c.execute(
                "SELECT run_id FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        return str(row[0]) if row else None
    except (sqlite3.Error, OSError):
        return None


def aggregate_status(projekt: str) -> dict[str, Any]:
    """Liefert Tasks/Verify/Drift/Phase fuer die Status-Leiste."""
    es = EventStore()
    run_id = _letzter_run_id(es)
    aus: dict[str, Any] = {
        "run_id": run_id,
        "tasks": {"started": 0, "done": 0},
        "verify": None,
        "drift": None,
        "phase": None,
    }
    if run_id is None:
        return aus
    try:
        with sqlite3.connect(es.db_pfad) as c:
            started = c.execute(
                "SELECT COUNT(*) FROM events "
                "WHERE run_id=? AND kind='task_started'",
                (run_id,),
            ).fetchone()[0]
            done = c.execute(
                "SELECT COUNT(*) FROM events "
                "WHERE run_id=? AND kind='task_done'",
                (run_id,),
            ).fetchone()[0]
            v = c.execute(
                "SELECT payload FROM events "
                "WHERE run_id=? AND kind LIKE 'verify_%' "
                "ORDER BY seq DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            ph = c.execute(
                "SELECT phase FROM events "
                "WHERE run_id=? AND phase IS NOT NULL "
                "ORDER BY seq DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        aus["tasks"] = {"started": int(started), "done": int(done)}
        if v:
            try:
                aus["verify"] = json.loads(v[0])
            except json.JSONDecodeError:
                aus["verify"] = {"raw": v[0]}
        if ph:
            aus["phase"] = ph[0]
        if aus["phase"] is None:
            py = werkstatt_home() / ".werkstatt" / f"{projekt}.phase.yaml"
            if py.exists():
                try:
                    text = py.read_text(encoding="utf-8")
                    mm = re.search(r"^phase_id:\s*(\S+)", text, re.MULTILINE)
                    if mm:
                        aus["phase"] = mm.group(1)
                    else:
                        mm = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
                        if mm:
                            aus["phase"] = mm.group(1)
                except OSError:
                    pass
        # Verify aus JSONL-Audit (verify_*)
        if aus["verify"] is None:
            audit_dir = werkstatt_home() / "audit-logs"
            if audit_dir.exists():
                kand = sorted(audit_dir.glob("agent-pipeline-*.jsonl"))
                if kand:
                    try:
                        with kand[-1].open(encoding="utf-8", errors="replace") as f:
                            zeilen = f.readlines()[-2000:]
                        for z in reversed(zeilen):
                            z = z.strip()
                            if not z:
                                continue
                            try:
                                obj = json.loads(z)
                            except json.JSONDecodeError:
                                continue
                            k = str(obj.get("kind", ""))
                            if k.startswith("verify_"):
                                ok_val = k.endswith(("_ok", "_passed"))
                                bad = k.endswith(("_fail", "_failed", "_error"))
                                aus["verify"] = {
                                    "ok": True if ok_val else (False if bad else None),
                                    "kind": k,
                                    "ts": obj.get("ts"),
                                }
                                break
                    except OSError:
                        pass

        # Drift: aus .werkstatt/quality_gate.log (letzter Eintrag)
        qg = werkstatt_home() / ".werkstatt" / "quality_gate.log"
        if qg.exists():
            try:
                letzte = qg.read_text(encoding="utf-8").strip().split("\n")[-1]
                aus["drift"] = json.loads(letzte)
            except (OSError, json.JSONDecodeError):
                pass
        if aus["drift"] is None:
            aus["drift"] = {"status": "ungemessen", "hinweis": "python3 -m tools.quality_gate --hook"}
    except sqlite3.Error:
        pass
    return aus


def aggregate_tokens(projekt: str, run_id: str | None = None) -> dict[str, Any]:
    """Token-Verbrauch: Loop (Event-Store) und Chat (Session-Store).

    Loop: llm_usage-Events pro run_id aggregiert.
    Chat: token_usage-Events aller Sessions des Projekts aggregiert.
    """
    es = EventStore()
    if run_id is None:
        run_id = _letzter_run_id(es)

    aus: dict[str, Any] = {
        "loop": {"run_id": run_id, "prompt": 0, "completion": 0, "total": 0, "calls": 0},
        "chat": {"prompt": 0, "completion": 0, "total": 0, "calls": 0, "sessions": 0},
    }

    # --- Loop ---
    if run_id is not None:
        try:
            with sqlite3.connect(es.db_pfad) as c:
                rows = c.execute(
                    "SELECT payload FROM events "
                    "WHERE run_id=? AND kind='llm_usage'",
                    (run_id,),
                ).fetchall()
            for (payload,) in rows:
                try:
                    d = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                aus["loop"]["prompt"] += int(d.get("prompt_tokens", 0) or 0)
                aus["loop"]["completion"] += int(d.get("completion_tokens", 0) or 0)
                aus["loop"]["total"] += int(d.get("total_tokens", 0) or 0)
                aus["loop"]["calls"] += 1
        except sqlite3.Error:
            pass

    # --- Chat ---
    try:
        from werkstatt.chat_session import ChatSession, list_sessions
        sessions = list_sessions(projekt)
        aus["chat"]["sessions"] = len(sessions)
        for sid in sessions:
            try:
                events = ChatSession(projekt, sid).load()
            except Exception:  # noqa: S112
                continue
            for ev in events:
                if ev.get("kind") != "token_usage":
                    continue
                payload = ev.get("payload") or {}
                aus["chat"]["prompt"] += int(payload.get("prompt_tokens", 0) or 0)
                aus["chat"]["completion"] += int(payload.get("completion_tokens", 0) or 0)
                aus["chat"]["total"] += int(payload.get("total_tokens", 0) or 0)
                aus["chat"]["calls"] += 1
    except Exception:
        pass

    return aus


def _phasen_label(kind: str) -> str | None:
    for prefix, label in _PHASEN_LABELS.items():
        if kind.startswith(prefix):
            return label
    return None


def _lese_audit_jsonl(pfad: Path) -> list[dict[str, Any]]:
    """Liest eine JSONL-Datei, filtert auf Phasen-Kinds."""
    if not pfad.exists():
        return []
    ergebnis: list[dict[str, Any]] = []
    try:
        with pfad.open(encoding="utf-8", errors="replace") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    obj = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                kind = str(obj.get("kind", ""))
                label = _phasen_label(kind)
                if label is None:
                    continue
                ergebnis.append({
                    "kind": kind,
                    "label": label,
                    "ts": obj.get("ts", ""),
                    "payload": obj,
                })
    except OSError:
        pass
    return ergebnis


def aggregate_timeline(
    projekt: str,
    run_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Phasen-Knoten fuer die Timeline.

    Quellen: Event-Store (task_started/task_done) + neueste
    JSONL-Audit-Datei (explorer_*, builder_*, reviewer_*, ...).
    """
    es = EventStore()
    if run_id is None:
        run_id = _letzter_run_id(es)
    if run_id is None:
        return []

    knoten: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(es.db_pfad) as c:
            rows = c.execute(
                "SELECT seq, kind, phase, status, payload, ts FROM events "
                "WHERE run_id=? AND kind IN ('task_started','task_done') "
                "ORDER BY seq ASC LIMIT ?",
                (run_id, limit),
            ).fetchall()
    except sqlite3.Error:
        rows = []

    task_offen: dict[str, dict[str, Any]] = {}
    for seq, kind, phase, status, payload, ts in rows:
        try:
            p = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            p = {}
        name = str(p.get("name") or p.get("task") or f"Task {seq}")
        if kind == "task_started":
            key = f"seq-{seq}"
            knoten.append({
                "id": key,
                "label": name,
                "kind": "task",
                "status": "running",
                "start_ts": ts,
                "end_ts": None,
                "phase": phase,
                "children": [],
            })
            task_offen[name] = knoten[-1]
        elif kind == "task_done":
            ziel = task_offen.pop(name, None)
            if ziel is not None:
                ziel["end_ts"] = ts
                ziel["status"] = "ok" if p.get("ok", True) else "error"
            else:
                knoten.append({
                    "id": f"seq-{seq}",
                    "label": name,
                    "kind": "task",
                    "status": "ok" if p.get("ok", True) else "error",
                    "start_ts": None,
                    "end_ts": ts,
                    "phase": phase,
                    "children": [],
                })

    # JSONL-Audit neueste Datei
    audit_dir = werkstatt_home() / "audit-logs"
    if audit_dir.exists():
        kandidaten = sorted(audit_dir.glob("agent-pipeline-*.jsonl"))
        if kandidaten:
            jsonl = _lese_audit_jsonl(kandidaten[-1])
            gruppen: dict[str, dict[str, Any]] = {}
            for ev in jsonl:
                schluessel = ev["label"]
                if schluessel not in gruppen:
                    gruppen[schluessel] = {
                        "id": f"phase-{schluessel.lower()}",
                        "label": schluessel,
                        "kind": "phase",
                        "status": "ok",
                        "start_ts": ev["ts"],
                        "end_ts": ev["ts"],
                        "children": [],
                    }
                g = gruppen[schluessel]
                g["end_ts"] = ev["ts"]
                g["children"].append({
                    "kind": ev["kind"],
                    "ts": ev["ts"],
                    "detail": ev["payload"].get("status") or ev["payload"].get("result"),
                })
                if "fehler" in ev["kind"] or "error" in ev["kind"]:
                    g["status"] = "error"
            knoten.extend(gruppen.values())

    return knoten[:limit]
