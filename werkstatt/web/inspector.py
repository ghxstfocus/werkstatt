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
import time
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


def _run_aktiv(es: EventStore, run_id: str, schwelle_s: int = 120) -> bool:
    """True wenn der letzte Event des Runs juenger als schwelle_s ist."""
    from datetime import UTC, datetime

    try:
        with sqlite3.connect(es.db_pfad) as c:
            row = c.execute(
                "SELECT ts FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if not row or not row[0]:
            return False
        ts = datetime.fromisoformat(str(row[0]))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return (datetime.now(UTC) - ts).total_seconds() < schwelle_s
    except (sqlite3.Error, ValueError, OSError):
        return False


_TL_LABELS: dict[str, str] = {
    "explorer_messung": "Explorer: Messung",
    "explorer_messung_findings": "Explorer: Befunde",
    "explorer_result": "Explorer: Ergebnis",
    "loop_explorer_ok": "Explorer: abgeschlossen",
    "loop_explorer_leer": "Explorer: leer",
    "loop_explorer_ergaenzt": "Explorer: ergaenzt",
    "loop_explorer_suchbegriffe": "Explorer: Suchbegriffe",
    "loop_skills_geladen": "Skills geladen",
    "builder_import_context": "Builder: Import-Kontext",
    "builder_file_context": "Builder: Datei-Kontext",
    "builder_patches_erstellt": "Builder: Patches erstellt",
    "builder_keine_patches_gold": "Builder: keine Patches",
    "builder_patch_bereits_erfuellt": "Builder: bereits erfuellt",
    "loop_task_start": "Task startet",
    "loop_task_ok": "Task erfolgreich",
    "loop_task_failed": "Task fehlgeschlagen",
    "loop_patch_applied": "Patch angewendet",
    "loop_patch_updated": "Patch aktualisiert",
    "loop_patch_created": "Patch erstellt",
    "loop_patch_fallback_used": "Patch-Fallback",
    "loop_patch_delete_blocked": "Patch-Loeschung blockiert",
    "reviewer_result": "Reviewer: Ergebnis",
    "reviewer_phase_rejected": "Reviewer: Phase abgelehnt",
    "reviewer_phase_approved": "Reviewer: Phase freigegeben",
    "phase_end_review": "Phase-Review",
    "loop_verify_ok": "Verify: OK",
    "loop_verify_failed": "Verify: Fehler",
    "loop_verify_stage_skipped": "Verify: Stage uebersprungen",
    "verify_stage_ohne_hart_flag": "Verify: Stage ohne Hart-Flag",
    "loop_reflection_runde": "Reflection Runde",
    "loop_reflection_kein_patch": "Reflection: kein Patch",
    "loop_reflection_patch_applied": "Reflection: Patch angewendet",
    "loop_phase_reflection_runde": "Reflection Runde",
    "loop_phase_reflection_approved": "Reflection: freigegeben",
    "loop_phase_reflection_erschoepft": "Reflection: erschoepft",
    "loop_phase_reflection_verify_failed": "Reflection: verify failed",
    "loop_phase_reflection_builder_failed": "Reflection: builder failed",
    "loop_phase_reflection_keine_bugs": "Reflection: keine Bugs",
    "loop_erfolg": "Loop erfolgreich",
    "loop_rollback": "Loop Rollback",
    "loop_dirty_tree": "Dirty Tree erkannt",
    "loop_gate_failed": "Gate fehlgeschlagen",
    "loop_hook_blocked": "Hook blockiert",
    "loop_plan_gate_approved": "Plan-Gate: freigegeben",
    "loop_plan_gate_rejected": "Plan-Gate: abgelehnt",
    "loop_human_gate_approved": "Human-Gate: freigegeben",
    "loop_human_gate_rejected": "Human-Gate: abgelehnt",
    "loop_human_gate_committed": "Human-Gate: committed",
    "llm_call": "LLM-Aufruf",
    "llm_usage": "LLM-Token",
    "llm_timeout_read": "LLM-Timeout (read)",
    "llm_timeout_gesamt": "LLM-Timeout (gesamt)",
    "command_executed": "Befehl ausgefuehrt",
    "command_rejected": "Befehl abgelehnt",
}

_TL_SKIP: frozenset[str] = frozenset({
    "heartbeat", "spinner", "log_line", "progress", "summary",
})

_TL_PHASEN_NAMEN: dict[str, str] = {
    # Laengere Keys zuerst — sonst matcht "plan" auch "planner"
    "plan_gate": "Plan-Gate",
    "human_gate": "Human-Gate",
    "end_review": "Phase-Review",
    "reflection": "Reflection",
    "explorer": "Explorer",
    "architect": "Architect",
    "planner": "Planner",
    "builder": "Builder",
    "reviewer": "Reviewer",
    "verify": "Verify",
    "plan": "Plan",
    "build": "Build",
    "review": "Review",
    "reflect": "Reflection",
    "explore": "Explorer",
}


def _tl_status(kind: str, payload: dict[str, Any]) -> str:
    if any(w in kind for w in ("failed", "error", "abgelehnt", "erschoepft",
                                 "rollback", "blocked")):
        return "error"
    if any(w in kind for w in ("_ok", "erfolg", "approved", "committed")):
        return "ok"
    if any(w in kind for w in ("start", "_phase", "runde")):
        return "running"
    if payload.get("ok") is True:
        return "ok"
    if payload.get("ok") is False:
        return "error"
    return "running"


def _tl_label(kind: str, payload: dict[str, Any]) -> str:
    if kind == "loop_phase":
        pname = str(payload.get("phase") or payload.get("name") or "phase")
        low = pname.lower()
        # Laengste Keys zuerst probieren (plan_gate vor plan)
        for key, label in sorted(
            _TL_PHASEN_NAMEN.items(), key=lambda kv: -len(kv[0])
        ):
            if key == low or key in low:
                return label
        return pname
    return _TL_LABELS.get(kind, kind)


def _tl_detail(kind: str, payload: dict[str, Any]) -> str:
    """Kurze, menschenlesbare Zusatz-Info pro Event (1 Zeile)."""
    if kind == "loop_task_start":
        return str(payload.get("text", ""))
    if kind in ("loop_task_ok", "loop_task_failed"):
        parts: list[str] = []
        e = payload.get("elapsed_s")
        if isinstance(e, (int, float)):
            parts.append(f"{e:.2f}s")
        g = payload.get("grund") or payload.get("reason")
        if g:
            parts.append(str(g)[:80])
        return " ".join(parts)
    if kind in ("loop_verify_failed", "verify_fehler"):
        f = payload.get("fehler") or payload.get("errors") or ""
        return str(f)[:120]
    if kind == "loop_verify_ok":
        stage = payload.get("stage") or payload.get("name") or ""
        return str(stage)[:60] if stage else ""
    if kind == "builder_patches_erstellt":
        pat = payload.get("patches") or []
        dateien = sorted({
            str(p.get("file", "")) for p in pat if isinstance(p, dict)
        } - {""})
        head = f"{len(pat)} Patch(es)"
        if dateien:
            head += ": " + ", ".join(dateien[:3])
            if len(dateien) > 3:
                head += f" +{len(dateien) - 3}"
        return head
    if kind == "builder_file_context":
        n = payload.get("anzahl") or payload.get("count")
        if n is None and isinstance(payload.get("files"), list):
            n = len(payload["files"])
        return f"{n} Datei(en)" if n else ""
    if kind == "builder_import_context":
        n = payload.get("anzahl") or payload.get("count")
        if n is None and isinstance(payload.get("imports"), list):
            n = len(payload["imports"])
        return f"{n} Imports" if n else ""
    if kind in ("loop_patch_updated", "loop_patch_applied", "loop_patch_created"):
        f = payload.get("file") or payload.get("path") or ""
        return str(f) if f else ""
    if kind == "reviewer_result":
        v = payload.get("verdict") if payload.get("verdict") is not None else payload.get("ok")
        return f"verdict={v}" if v is not None else ""
    if kind == "loop_skills_geladen":
        n = payload.get("anzahl")
        if n is None and isinstance(payload.get("skills"), list):
            n = len(payload["skills"])
        return f"{n} Skills" if n else ""
    if kind == "llm_usage":
        return (
            f"prompt={payload.get('prompt_tokens', 0)} "
            f"completion={payload.get('completion_tokens', 0)}"
        )
    if kind in ("loop_reflection_runde", "loop_phase_reflection_runde"):
        return f"Runde {payload.get('runde', '?')}"
    if kind == "loop_human_gate_committed":
        return str(payload.get("info", ""))[:100]
    if kind == "verify_stage_ohne_hart_flag":
        return "nur weiche Stufe aktiv"
    return ""


def _tl_menschliche_phase(pname: str) -> str:
    low = pname.lower()
    for key, label in _TL_PHASEN_NAMEN.items():
        if key in low:
            return label
    return pname or "Phase"


def aggregate_timeline(
    projekt: str, run_id: str | None = None, limit: int = 200,
) -> list[dict[str, Any]]:
    """Phasen-Knoten aus JSONL-Audit (menschlich lesbar).

    Die JSONL-Audit-Datei traegt die Phasen-Events (loop_phase,
    explorer_*, builder_*, verify_*, reviewer_*) — der Event-Store
    hat nur Task-Events ohne Kontext. Wir gruppieren nach
    loop_phase-Bloecken, mit Prolog-Block fuer alles davor.
    """
    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return []
    kandidaten = sorted(audit_dir.glob("agent-pipeline-*.jsonl"))
    if not kandidaten:
        return []
    datei = kandidaten[-1]

    try:
        mtime = datei.stat().st_mtime
        aktiv = (time.time() - mtime) < 120
    except OSError:
        aktiv = False

    events: list[dict[str, Any]] = []
    try:
        with datei.open(encoding="utf-8", errors="replace") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    obj = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    events.append(obj)
    except OSError:
        return []

    letzte_run_id: str | None = None
    for ev in reversed(events):
        rid = ev.get("run_id")
        if rid:
            letzte_run_id = str(rid)
            break
    ziel_run = run_id or letzte_run_id
    if ziel_run:
        events = [e for e in events if str(e.get("run_id", "")) == ziel_run]

    knoten: list[dict[str, Any]] = []
    aktuell: dict[str, Any] | None = None
    prolog: list[dict[str, Any]] = []

    def _flush() -> None:
        nonlocal aktuell
        if aktuell is not None:
            knoten.append(aktuell)
            aktuell = None

    for ev in events:
        kind = str(ev.get("kind", ""))
        if not kind or kind in _TL_SKIP:
            continue
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            payload = ev
        label = _tl_label(kind, payload)
        status = _tl_status(kind, payload)
        ts = str(ev.get("ts", ""))
        detail = _tl_detail(kind, payload)

        if kind == "loop_phase":
            _flush()
            pname = str(payload.get("phase") or payload.get("name") or "phase")
            aktuell = {
                "id": f"phase-{len(knoten)}-{pname}",
                "label": _tl_menschliche_phase(pname),
                "kind": "phase",
                "status": "running" if aktiv else "ok",
                "start_ts": ts,
                "end_ts": None if aktiv else ts,
                "phase": pname,
                "children": [],
            }
        else:
            detail_text = label
            if detail:
                detail_text += " - " + detail
            child = {
                "ts": ts,
                "kind": kind,
                "detail": detail_text,
                "status": status,
            }
            if aktuell is not None:
                aktuell["children"].append(child)
                aktuell["end_ts"] = ts
                if status == "error":
                    aktuell["status"] = "error"
            else:
                prolog.append(child)

    _flush()

    # Leere Phasen filtern (0 Kinder und <2s Dauer)
    def _pha_to_ts(ts: str) -> float:
        from datetime import datetime as _dt
        try:
            return _dt.fromisoformat(ts).timestamp()
        except (ValueError, TypeError):
            return 0.0

    knoten = [
        k for k in knoten
        if k.get("children") or (
            k.get("start_ts") and k.get("end_ts")
            and abs(_pha_to_ts(k["end_ts"]) - _pha_to_ts(k["start_ts"])) > 2
        )
    ]

    if prolog:
        knoten.insert(0, {
            "id": "phase-prolog",
            "label": "Vorbereitung",
            "kind": "phase",
            "status": "ok",
            "start_ts": prolog[0]["ts"],
            "end_ts": prolog[-1]["ts"],
            "phase": "prolog",
            "children": prolog,
        })

    return knoten[:limit]


