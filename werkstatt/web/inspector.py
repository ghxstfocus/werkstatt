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




# ============================================================
# OP-298: Gate-Context, Plan-Diff, Handoffs, Evidence-Links
# ============================================================

def _pick(payload: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = payload.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _payload_von(ev: dict[str, Any]) -> dict[str, Any]:
    """Robuste Payload-Extraktion mit mypy-kompatibler Typ-Garantie."""
    raw = ev.get("payload")
    if isinstance(raw, dict):
        return dict(raw)
    return dict(ev)


def _audit_events(run_id: str | None = None) -> list[dict[str, Any]]:
    """Liest die aktuelle JSONL-Audit-Datei, optional auf run_id gefiltert."""
    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return []
    kand = sorted(audit_dir.glob("agent-pipeline-*.jsonl"))
    if not kand:
        return []
    events: list[dict[str, Any]] = []
    try:
        with kand[-1].open(encoding="utf-8", errors="replace") as f:
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
    if run_id:
        return [e for e in events if str(e.get("run_id", "")) == run_id]
    # Default: letzter Run
    letzte = None
    for ev in reversed(events):
        rid = ev.get("run_id")
        if rid:
            letzte = str(rid)
            break
    if letzte:
        events = [e for e in events if str(e.get("run_id", "")) == letzte]
    return events


def _render_log_pfad() -> Path | None:
    """Neueste logs/loop-render-*.log Datei."""
    for kand in sorted(Path.cwd().glob("logs/loop-render-*.log"), reverse=True):
        return kand
    return None


def _extract_plan_text(payload: dict[str, Any]) -> str:
    """Sucht Plan-Text. Erst im Payload, dann im Render-Log."""
    # 1) Aus Payload
    for key in ("plan", "prosa", "architect_prosa", "plan_text", "inhalt",
                "aufgabe", "architect", "text"):
        v = payload.get(key)
        if isinstance(v, str) and len(v) > 20:
            return v
    # 2) Aus .phase.yaml (aufgabe-Feld)
    for pfad in (
        Path.cwd() / ".werkstatt" / "werkstatt.phase.yaml",
        Path.cwd() / ".phase.yaml",
    ):
        if pfad.exists():
            try:
                txt = pfad.read_text(encoding="utf-8", errors="replace")
                import re as _re
                m = _re.search(r'^aufgabe:\s*"?([^"\n]*(?:\\\n[^"\n]*)*)"?',
                               txt, re.MULTILINE)
                if m and m.group(1):
                    return m.group(1).replace("\\n", "\n").replace("\\", "")[:12000]
            except OSError:
                pass
    # 3) Aus Render-Log (falls vorhanden, aeltere Runs)
    log = _render_log_pfad()
    if log:
        try:
            return log.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            return ""
    return ""



def _extract_scout_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Explorer-/Scout-Daten aus den echten Feldern."""
    befehle = payload.get("befehle") or payload.get("suchbegriffe") or []
    dateien = payload.get("key_files") or payload.get("dateien") or []
    findings = payload.get("findings") or []
    return {
        "befehle": befehle if isinstance(befehle, list) else [],
        "findings": findings if isinstance(findings, list) else [],
        "dateien": dateien if isinstance(dateien, list) else [],
        "counts": {
            k: payload.get(k)
            for k in ("findings_len", "n_key_files", "dateien_gesamt", "diagnostics_befuellt")
            if payload.get(k) is not None
        },
    }



def _lese_phase_yaml_aufgabe(projekt: str) -> str:
    """Liest die `aufgabe:` aus .werkstatt/<projekt>.phase.yaml via yaml.safe_load."""
    py = werkstatt_home() / ".werkstatt" / f"{projekt}.phase.yaml"
    if not py.exists():
        return ""
    try:
        import yaml  # type: ignore[import-untyped]
        with py.open(encoding="utf-8", errors="replace") as f:
            data = yaml.safe_load(f)
    except (OSError, ImportError):
        return ""
    except Exception:  # noqa: BLE001 -- yaml.YAMLError + Varianten
        return ""
    if not isinstance(data, dict):
        return ""
    aufgabe = data.get("aufgabe")
    if not isinstance(aufgabe, str):
        return ""
    return aufgabe[:12000]



def aggregate_gate_context(
    projekt: str, run_id: str | None = None
) -> dict[str, Any]:
    """Alles was der Mensch braucht um ein Gate informiert zu entscheiden."""
    events = _audit_events(run_id)
    letzte_run_id = (
        str(events[-1].get("run_id") or run_id or "")
        if events else (run_id or "")
    )

    plan: dict[str, Any] | None = None
    scout_acc: dict[str, Any] = {"befehle": [], "findings": [], "dateien": [], "counts": {}}
    scout_ts = ""
    verify: dict[str, Any] | None = None
    reviewer: dict[str, Any] | None = None
    historie: list[dict[str, str]] = []

    for ev in events:
        kind = str(ev.get("kind", ""))
        ts = str(ev.get("ts", ""))
        payload = _payload_von(ev)
        if kind == "loop_plan_shown":
            txt = str(payload.get("plan_text") or "")
            if txt:
                plan_laenge = len(plan["text"]) if plan is not None else 0
                if len(txt) > plan_laenge:
                    plan = {"text": txt, "ts": ts, "kind": kind}
        elif kind.startswith("architect_") or kind == "loop_plan_gate_approved":
            txt = _extract_plan_text(payload)
            if txt:
                plan_laenge = len(plan["text"]) if plan is not None else 0
                if len(txt) > plan_laenge:
                    plan = {"text": txt, "ts": ts, "kind": kind}
        if kind.startswith(("explorer_", "scout_")):
            d = _extract_scout_data(payload)
            for k in ("befehle", "findings", "dateien"):
                for item in d.get(k, []):
                    if item not in scout_acc[k]:
                        scout_acc[k].append(item)
            for k, v in d.get("counts", {}).items():
                scout_acc["counts"][k] = v
            scout_ts = scout_ts or ts
        if kind.startswith(("loop_verify_", "verify_")):
            ok = kind.endswith(("_ok", "_passed"))
            bad = kind.endswith(("_failed", "_fail", "_error"))
            verify = {
                "status": "ok" if ok else ("error" if bad else "skipped"),
                "kind": kind, "ts": ts,
                "detail": str(_pick(payload, "fehler", "grund", "stage", "name") or "")[:120],
            }
        if kind == "reviewer_result":
            v = _pick(payload, "verdict", "ok", "status")
            reviewer = {"verdict": str(v), "ts": ts, "kind": kind}
        if kind.startswith(("loop_human_gate_", "loop_plan_gate_")) and kind != "loop_plan_gate_approved":
            historie.append({"kind": kind, "ts": ts})

    # Plan-Fallback aus phase.yaml
    if plan is None:
        aufgabe = _lese_phase_yaml_aufgabe(projekt)
        if aufgabe:
            plan = {"text": aufgabe, "ts": "", "kind": "phase_yaml"}

    scout = None
    if any(scout_acc[k] for k in ("befehle", "findings", "dateien")):
        scout = {**scout_acc, "ts": scout_ts, "kind": "explorer_merged"}

    # Offene Gates
    offene: list[dict[str, Any]] = []
    if letzte_run_id:
        try:
            es = EventStore()
            opens = es.query(letzte_run_id, kind="gate_open")
            beantwortet = {
                (e.get("payload") or {}).get("gate_id")
                for e in es.query(letzte_run_id, kind="gate_answered")
            }
            for ev in opens:
                pa = ev.get("payload") or {}
                if pa.get("gate_id") not in beantwortet:
                    offene.append({
                        "gate_id": pa.get("gate_id"),
                        "prompt": pa.get("prompt"),
                        "optionen": pa.get("optionen", "jna"),
                    })
        except Exception:  # noqa: S110
            pass

    # Empfehlung
    empfehlung = "prüfen"
    grund_teile: list[str] = []
    if verify and verify.get("status") == "ok":
        grund_teile.append("Verify gruen")
    elif verify and verify.get("status") == "error":
        grund_teile.append("Verify rot")
    if reviewer:
        v = (reviewer.get("verdict") or "").lower()
        if v in ("approved", "true", "ok"):
            grund_teile.append("Reviewer approved")
        elif v in ("rejected", "false", "error"):
            grund_teile.append("Reviewer rejected")
    if historie:
        ablehnungen = sum(1 for h in historie if "rejected" in h["kind"])
        if ablehnungen >= 2:
            grund_teile.append(f"{ablehnungen}x zuvor abgelehnt")
    if grund_teile and all("gruen" in g or "approved" in g for g in grund_teile):
        empfehlung = "j"
    if any("rot" in g or "rejected" in g for g in grund_teile):
        empfehlung = "n"

    return {
        "run_id": letzte_run_id,
        "plan": plan,
        "scout": scout,
        "verify": verify,
        "reviewer": reviewer,
        "offene_gates": offene,
        "historie": historie[-10:],
        "empfehlung": empfehlung,
        "empfehlung_grund": ", ".join(grund_teile) or "keine Bewertung möglich",
    }



def aggregate_plan_versions(
    projekt: str, run_id: str | None = None
) -> list[dict[str, Any]]:
    """Plan-Versionen — heute nur 1 (Loop auditiert keinen Plan-Text)."""
    aufgabe = _lese_phase_yaml_aufgabe(projekt)
    if not aufgabe:
        return []
    return [{"version": 1, "ts": "", "text": aufgabe, "trigger": "initial"}]



def aggregate_handoffs(
    projekt: str, run_id: str | None = None
) -> list[dict[str, Any]]:
    """Rollen-Kette mit Übergaben (Explorer -> Scout -> Architect -> ...)."""
    events = _audit_events(run_id)
    ROLLEN = [
        ("explorer", "Explorer"),
        ("scout", "Scout"),
        ("architect", "Architect"),
        ("planner", "Planner"),
        ("builder", "Builder"),
        ("reviewer", "Reviewer"),
        ("reflection", "Reflection"),
        ("verify", "Verify"),
    ]

    # Pro Rolle: erster ts + letzter ts + Anzahl Events + Zusammenfassung
    rolle_stats: dict[str, dict[str, Any]] = {}
    for ev in events:
        kind = str(ev.get("kind", ""))
        ts = str(ev.get("ts", ""))
        payload = _payload_von(ev)
        for prefix, label in ROLLEN:
            if kind.startswith(prefix):
                if label not in rolle_stats:
                    rolle_stats[label] = {
                        "rolle": label,
                        "start": ts, "ende": ts,
                        "anzahl": 0, "beispiele": [],
                    }
                s = rolle_stats[label]
                s["anzahl"] += 1
                s["ende"] = ts
                if len(s["beispiele"]) < 3:
                    txt = str(_pick(payload, "text", "grund", "verdict", "stage") or kind)[:80]
                    s["beispiele"].append(txt)
                break

    # Reihenfolge aus ROLLEN beibehalten
    handoffs: list[dict[str, Any]] = []
    vorherige = None
    for _, label in ROLLEN:
        if label in rolle_stats:
            st = rolle_stats[label]
            handoffs.append({
                "rolle": label,
                "start": st["start"],
                "ende": st["ende"],
                "anzahl": st["anzahl"],
                "beispiele": st["beispiele"],
                "von": vorherige,
            })
            vorherige = label
    return handoffs


def aggregate_evidence_links(
    projekt: str, run_id: str | None = None
) -> list[dict[str, Any]]:
    """Explorer-Belege: key_files + Zahlen + Befehle.

    Plan-Text-Matching ist nicht moeglich (Loop auditiert den Plan
    nicht), daher zeigen wir die tatsaechlichen Explorer-Spuren.
    """
    events = _audit_events(run_id)
    links: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ev in events:
        kind = str(ev.get("kind", ""))
        ts = str(ev.get("ts", ""))
        payload = _payload_von(ev)

        if kind == "explorer_result":
            for f in (payload.get("key_files") or []):
                f_str = str(f)
                if f_str and f_str not in seen:
                    seen.add(f_str)
                    links.append({
                        "quelle": "Explorer",
                        "typ": "datei",
                        "text": f"Schluessel-Datei: {f_str}",
                        "ts": ts,
                    })
            fl = payload.get("findings_len")
            if fl:
                links.append({
                    "quelle": "Explorer",
                    "typ": "zahl",
                    "text": f"{fl} Findings identifiziert",
                    "ts": ts,
                })
        elif kind == "explorer_messung":
            for b in (payload.get("befehle") or [])[:5]:
                b_str = str(b)[:100]
                key = "cmd:" + b_str
                if key not in seen:
                    seen.add(key)
                    links.append({
                        "quelle": "Explorer",
                        "typ": "befehl",
                        "text": f"Befehl: {b_str}",
                        "ts": ts,
                    })
            dg = payload.get("dateien_gesamt")
            if dg:
                links.append({
                    "quelle": "Explorer",
                    "typ": "zahl",
                    "text": f"{dg} Dateien gescannt",
                    "ts": ts,
                })
        elif kind == "explorer_messung_findings":
            nk = payload.get("n_key_files")
            if nk:
                links.append({
                    "quelle": "Explorer",
                    "typ": "zahl",
                    "text": f"{nk} Key-Files identifiziert",
                    "ts": ts,
                })
            diag = payload.get("diagnostics_befuellt")
            if diag:
                links.append({
                    "quelle": "Explorer",
                    "typ": "zahl",
                    "text": f"Diagnostics: {diag}",
                    "ts": ts,
                })

    return links[:40]



