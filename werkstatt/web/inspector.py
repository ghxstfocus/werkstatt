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

# OP-305: Basis fuer Multi-Projekt-Pfade (testbar via monkeypatch)
_PROJECTS_BASE = Path("/opt")

__all__ = ["aggregate_status", "aggregate_timeline", "aggregate_tokens",
           "aggregate_tokens_per_rolle", "parse_ops"]

# OP-389b-Fix: OP-Suffixe (a/b/c) MUESSEN erkannt werden. Dieselbe
# Konvention wie in parse_ops() Zeile 77 (blockiert_von-Regex) —
# Inkonsistenz innerhalb derselben Datei. Ohne diese Erweiterung
# findet parse_ops() keine Sub-OPs, /start bricht mit leerer Aufgabe
# ab, Loop crasht mit State-Contract-Verletzung (Live 2026-11-09
# 18:58: 13 Events in 1.6s, dann loop_failed).
_OPS_RE = re.compile(r"^### (OP-\d+[a-z]?):\s*(.+?)\s*$", re.MULTILINE)
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
        # STATUS.md-Header sagt: nur offene, loop-faehige OPs.
        # done-OPs gehoeren nach PROGRESS.md (separater OP).
        if status in ("done", "erledigt", "closed"):
            continue
        # STATUS.md-Header: nur offene, loop-faehige OPs.
        # done-OPs gehoeren nach PROGRESS.md (separater OP).
        if status in ("done", "erledigt", "closed"):
            continue
        # OP-303: blockiert_von extrahieren (nur IDs, nicht Freitext)
        bv_match = re.search(
            r"\*\*Blockiert von:\*\*\s*([^\n]+)", block
        )
        blockiert_von = ""
        if bv_match:
            roh = bv_match.group(1).strip()
            ids = re.findall(r"OP-\d+[a-z]?", roh)
            blockiert_von = ", ".join(ids) if ids else ""

        ergebnis.append({
            "id": op_id,
            "titel": titel,
            "status": status,
            "blockiert_von": blockiert_von,
        })
    return ergebnis


def _letzter_run_id(
    es: EventStore, projekt: str = "werkstatt",
) -> str | None:
    """OP-306c: Liefert letzten run_id NUR fuer `projekt`."""
    try:
        with sqlite3.connect(es.db_pfad) as c:
            row = c.execute(
                "SELECT run_id FROM events WHERE project=? "
                "AND run_id IS NOT NULL AND run_id != '' "
                "ORDER BY seq DESC LIMIT 1",
                (projekt,),
            ).fetchone()
        return str(row[0]) if row else None
    except (sqlite3.Error, OSError):
        return None


def _frische_projektion() -> None:
    """OP-381e: SQLite vor UI-Reads aktualisieren.

    Hintergrund: audit._maybe_flush triggert Projector.tail() erst
    nach _FLUSH_INTERVAL (100) Events. Bei kurzen Runs (< 100 Events)
    bleibt SQLite hinter JSONL. UI-Renders lesen SQLite und sehen
    nichts — Read-Through macht jeden UI-Read aktuell (idempotent).

    Fail-soft: bei Fehler wird der Read mit alten Daten ausgefuehrt.
    """
    try:
        from werkstatt.projection import Projector
        Projector().tail()
    except Exception:  # noqa: BLE001
        pass


def aggregate_status(projekt: str) -> dict[str, Any]:
    """Liefert Tasks/Verify/Drift/Phase fuer die Status-Leiste."""
    _frische_projektion()
    es = EventStore()
    run_id = _letzter_run_id(es, projekt)
    aus: dict[str, Any] = {
        "run_id": run_id,
        "tasks": {"started": 0, "done": 0},
        "verify": None,
        "drift": None,
        "phase": None,
        "unverified": False,
    }
    if run_id is None:
        return aus
    try:
        with sqlite3.connect(es.db_pfad) as c:
            started = c.execute(
                "SELECT COUNT(*) FROM events "
                "WHERE run_id=? AND kind='task_started' AND project=?",
                (run_id, projekt),
            ).fetchone()[0]
            done = c.execute(
                "SELECT COUNT(*) FROM events "
                "WHERE run_id=? AND kind='task_done' AND project=?",
                (run_id, projekt),
            ).fetchone()[0]
            v = c.execute(
                "SELECT payload FROM events "
                "WHERE run_id=? AND kind LIKE 'verify_%' AND project=? "
                "ORDER BY seq DESC LIMIT 1",
                (run_id, projekt),
            ).fetchone()
            ph = c.execute(
                "SELECT phase FROM events "
                "WHERE run_id=? AND phase IS NOT NULL AND project=? "
                "ORDER BY seq DESC LIMIT 1",
                (run_id, projekt),
            ).fetchone()
            unverified = c.execute(
                "SELECT 1 FROM events WHERE run_id=? AND project=? "
                "AND origin_verified=0 LIMIT 1",
                (run_id, projekt),
            ).fetchone()
        aus["tasks"] = {"started": int(started), "done": int(done)}
        aus["unverified"] = unverified is not None
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
        # Verify aus JSONL-Audit (verify_*) — ueber die letzten 3 Dateien
        if aus["verify"] is None:
            audit_dir = werkstatt_home() / "audit-logs"
            if audit_dir.exists():
                kand = sorted(audit_dir.glob("agent-pipeline-*.jsonl"))[-3:]
                for kandidat in reversed(kand):
                    if aus["verify"] is not None:
                        break
                    try:
                        with kandidat.open(encoding="utf-8", errors="replace") as f:
                            zeilen = f.readlines()[-5000:]
                    except OSError:
                        continue
                    for z in reversed(zeilen):
                        z = z.strip()
                        if not z:
                            continue
                        try:
                            obj = json.loads(z)
                        except json.JSONDecodeError:
                            continue
                        # JSONL is a global stream. A fallback result is only
                        # trustworthy when both project and current run match;
                        # legacy events without provenance remain unknown.
                        if obj.get("project") != projekt or obj.get("run_id") != run_id:
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


def aggregate_palette(projekt: str, q: str) -> dict[str, list[dict]]:
    """OP-302: Server-Filter fuer Command Palette.

    Liefert 4 Kategorien von Treffern. Nur bei nicht-leerem q.
    Bei leerem q: Aktions-Hints (was man tun kann).
    """
    q_low = (q or "").strip().lower()
    ops: list[dict] = []
    sessions: list[dict] = []
    runs: list[dict] = []
    actions: list[dict] = []

    # Aktionen: fixe Liste, immer verfuegbar
    AKTIONEN: list[dict[str, Any]] = [
        {"typ": "action", "titel": "Loop mit naechster OP starten",
         "action": "start_loop", "shortcut": ""},
        {"typ": "action", "titel": "Loop stoppen",
         "action": "stop_loop", "shortcut": ""},
        {"typ": "nav", "titel": "Audit oeffnen",
         "action": "open_tab", "params": {"tab": "audit"}, "shortcut": ""},
        {"typ": "nav", "titel": "Loop-Log oeffnen",
         "action": "open_tab", "params": {"tab": "terminal"}, "shortcut": ""},
        {"typ": "nav", "titel": "Diff oeffnen",
         "action": "open_tab", "params": {"tab": "diff"}, "shortcut": ""},
        {"typ": "nav", "titel": "Verify oeffnen",
         "action": "open_tab", "params": {"tab": "verify"}, "shortcut": ""},
        {"typ": "nav", "titel": "Dateien oeffnen",
         "action": "open_tab", "params": {"tab": "files"}, "shortcut": ""},
        {"typ": "nav", "titel": "Projekt hinzufuegen",
         "action": "new_project", "shortcut": ""},
    ]

    # OPs durchsuchen — projekt-spezifischer Pfad (OP-305)
    for op in parse_ops(_PROJECTS_BASE / projekt):
        titel = op.get("titel", "")
        oid = op.get("id", "")
        if not q_low or q_low in oid.lower() or q_low in titel.lower():
            ops.append({
                "typ": "op",
                "titel": f"{oid}: {titel}",
                "untertitel": f"blockiert von: {op.get('blockiert_von') or '—'}",
                "action": "start_op",
                "params": {"op_id": oid},
            })

    # Aktionen durchsuchen
    for a in AKTIONEN:
        if not q_low or q_low in a["titel"].lower():
            actions.append(a)

    # Sessions durchsuchen (nur bei q >= 2 Zeichen)
    if q_low and len(q_low) >= 2:
        try:
            from werkstatt.chat_session import list_sessions
            for sid in list_sessions(projekt)[:30]:
                if q_low in sid.lower():
                    sessions.append({
                        "typ": "session",
                        "titel": f"Session {sid[:8]}",
                        "untertitel": sid,
                        "action": "open_session",
                        "params": {"session_id": sid},
                    })
        except Exception:  # noqa: BLE001
            pass

    # Runs durchsuchen (nur bei q >= 4 Zeichen — sonst zu viele)
    if q_low and len(q_low) >= 4:
        try:
            es = EventStore()
            with sqlite3.connect(es.db_pfad) as c:
                for rid, ts, kind in c.execute(
                    "SELECT DISTINCT run_id, ts, kind FROM events "
                    "WHERE project=? AND run_id LIKE ? "
                    "ORDER BY seq DESC LIMIT 10",
                    (projekt, f"%{q_low}%"),
                ):
                    if rid:
                        runs.append({
                            "typ": "run",
                            "titel": rid,
                            "untertitel": kind + " " + str(ts)[:16],
                            "action": "open_run",
                            "params": {"run_id": rid},
                        })
        except sqlite3.Error:
            pass

    return {
        "ops": ops[:15],
        "actions": actions[:10],
        "sessions": sessions[:8],
        "runs": runs[:8],
    }


def aggregate_ops_run_status(projekt: str) -> dict[str, dict[str, Any]]:
    """OP-303: Run-Status pro OP aus SQLite-Events.

    Ableitung:
    - pipeline_start mit op_id -> welcher run_id gehoert zu welcher OP
    - loop_erfolg / loop_failed / summary -> Ergebnis
    - heartbeat in letzten 60s -> running (falls kein Terminal-Event)
    """
    import json
    from datetime import UTC, datetime

    es = EventStore()
    aus: dict[str, dict[str, Any]] = {}
    try:
        with sqlite3.connect(es.db_pfad) as c:
            # 1. OP-303: primaer loop_started, fallback pipeline_start (Legacy)
            run_to_op: dict[str, str] = {}
            for _kind in ("loop_started", "pipeline_start"):
                for run_id, payload in c.execute(
                    "SELECT run_id, payload FROM events "
                    "WHERE kind=? AND project=? AND run_id!=''",
                    (_kind, projekt),
                ):
                    try:
                        d = json.loads(payload or "{}")
                    except json.JSONDecodeError:
                        continue
                    oid = d.get("op_id") or ""
                    if oid:
                        run_to_op[run_id] = oid

            # 2. Pro OP: letzter run_id
            op_to_run: dict[str, str] = {}
            for run_id, op_id in run_to_op.items():
                op_to_run[op_id] = run_id  # spaeterer ueberschreibt

            # 3. Status pro run_id ableiten
            for op_id, run_id in op_to_run.items():
                # Terminal-Event?
                term = c.execute(
                    "SELECT kind, ts FROM events WHERE run_id=? AND project=? "
                    "AND kind IN "
                    "('loop_erfolg','loop_failed') ORDER BY seq DESC LIMIT 1",
                    (run_id, projekt)
                ).fetchone()
                # Heartbeat?
                hb = c.execute(
                    "SELECT ts FROM events WHERE run_id=? AND project=? "
                    "AND kind='heartbeat' "
                    "ORDER BY seq DESC LIMIT 1",
                    (run_id, projekt)
                ).fetchone()

                state = "idle"
                ts = ""
                if term:
                    state = "done" if term[0] == "loop_erfolg" else "failed"
                    ts = term[1]
                elif hb:
                    try:
                        ts_hb = datetime.fromisoformat(str(hb[0]))
                        if (datetime.now(UTC) - ts_hb).total_seconds() < 60:
                            state = "running"
                            ts = hb[0]
                    except (ValueError, TypeError):
                        pass
                unverified = c.execute(
                    "SELECT 1 FROM events WHERE run_id=? AND project=? "
                    "AND origin_verified=0 LIMIT 1",
                    (run_id, projekt),
                ).fetchone() is not None
                if unverified and state == "done":
                    state = "unverified"
                aus[op_id] = {
                    "state": state,
                    "run_id": run_id,
                    "ts": ts,
                    "unverified": unverified,
                }
    except sqlite3.Error:
        pass
    return aus


def aggregate_tokens(projekt: str, run_id: str | None = None) -> dict[str, Any]:
    """Token-Verbrauch: Loop (Event-Store) und Chat (Session-Store).

    Loop: llm_usage-Events pro run_id aggregiert.
    Chat: token_usage-Events aller Sessions des Projekts aggregiert.
    """
    _frische_projektion()
    es = EventStore()
    if run_id is None:
        run_id = _letzter_run_id(es, projekt)

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
                    "WHERE run_id=? AND kind='llm_usage' AND project=?",
                    (run_id, projekt),
                ).fetchall()
            for (payload,) in rows:
                try:
                    d = json.loads(payload)
                    if not isinstance(d, dict):
                        continue
                    prompt = int(d.get("prompt_tokens", 0) or 0)
                    completion = int(d.get("completion_tokens", 0) or 0)
                    total = int(d.get("total_tokens", 0) or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                aus["loop"]["prompt"] += prompt
                aus["loop"]["completion"] += completion
                aus["loop"]["total"] += total
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

    aus["by_role"] = aggregate_tokens_per_rolle(projekt, run_id)
    return aus


def aggregate_tokens_per_rolle(
    projekt: str, run_id: str | None = None,
) -> dict[str, dict[str, int]]:
    """Aggregiert Loop-Token pro Rolle, inklusive Spitzenwert je Call."""
    es = EventStore()
    if run_id is None:
        run_id = _letzter_run_id(es, projekt)
    if run_id is None:
        return {}
    try:
        with sqlite3.connect(es.db_pfad) as c:
            rows = c.execute(
                "SELECT payload FROM events "
                "WHERE run_id=? AND kind='llm_usage' AND project=?",
                (run_id, projekt),
            ).fetchall()
    except sqlite3.Error:
        return {}
    aus: dict[str, dict[str, int]] = {}
    for (payload,) in rows:
        try:
            event = json.loads(payload)
            if not isinstance(event, dict):
                continue
            rolle = str(event.get("rolle") or "unbekannt")
            prompt = int(event.get("prompt_tokens", 0) or 0)
            completion = int(event.get("completion_tokens", 0) or 0)
            total = int(event.get("total_tokens", 0) or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        stats = aus.setdefault(rolle, {
            "calls": 0, "prompt": 0, "completion": 0, "total": 0,
            "max_prompt": 0,
        })
        stats["calls"] += 1
        stats["prompt"] += prompt
        stats["completion"] += completion
        stats["total"] += total
        stats["max_prompt"] = max(stats["max_prompt"], prompt)
    return aus


def aggregate_ambient(projekt: str) -> dict[str, Any]:
    """OP-301: Loop-Status, letzter Run, Tokens, offene Gates in einem Call.

    Fallbacks:
    - running: letzter heartbeat < 60s
    - done/failed: neuestes Terminal-Event (loop_erfolg|loop_failed|
      loop_ended) entscheidet. Frueher wurde loop_erfolg priorisiert —
      Bug OP-371, Live 2026-11-08 22:10: ambient zeigte 'done' obwohl
      das letzte Event loop_failed (19:41) war.
    - gates: DISTINCT gate_id ueber open/answered/expired
    """
    _frische_projektion()
    from datetime import UTC, datetime

    es = EventStore()
    run_id = _letzter_run_id(es, projekt)
    aus: dict[str, Any] = {
        "loop_status": "idle",
        "loop_phase": None,
        "last_run": None,
        "tokens": {"loop_total": 0, "chat_total": 0},
        "gates_open": 0,
    }
    if run_id is None:
        return aus

    try:
        with sqlite3.connect(es.db_pfad) as c:
            # 1. Running-Erkennung (OP-381)
            # 1a: Heartbeat <60s -> running
            # 1b: offenes gate_open <60s -> running (Loop wartet am Gate)
            hb = c.execute(
                "SELECT ts FROM events "
                "WHERE kind='heartbeat' AND project=? "
                "ORDER BY seq DESC LIMIT 1",
                (projekt,),
            ).fetchone()
            if hb:
                try:
                    ts_hb = datetime.fromisoformat(str(hb[0]))
                    if (datetime.now(UTC) - ts_hb).total_seconds() < 60:
                        aus["loop_status"] = "running"
                except (ValueError, TypeError):
                    pass
            if aus["loop_status"] != "running":
                go = c.execute(
                    "SELECT seq, ts FROM events "
                    "WHERE kind='gate_open' AND project=? "
                    "ORDER BY seq DESC LIMIT 1",
                    (projekt,),
                ).fetchone()
                if go:
                    # OP-381: Terminal-Event nach gate_open -> Loop tot,
                    # auch wenn das Gate juenger als 300s ist.
                    go_seq, go_ts = go[0], go[1]
                    _term_nach_go = c.execute(
                        "SELECT 1 FROM events "
                        "WHERE kind IN ('loop_erfolg', 'loop_failed', 'loop_ended') "
                        "AND project=? "
                        "AND run_id IS NOT NULL AND run_id != '' "
                        "AND seq > ? LIMIT 1",
                        (projekt, go_seq),
                    ).fetchone()
                    if not _term_nach_go:
                        try:
                            ts_go = datetime.fromisoformat(str(go_ts))
                            if (datetime.now(UTC) - ts_go).total_seconds() < 300:
                                aus["loop_status"] = "running"
                                aus["loop_phase"] = "gate_wait"
                        except (ValueError, TypeError):
                            pass

            # 2. Neuestes Terminal-Event entscheidet (OP-371)
            # Frueher: 3-stufige Kaskade mit loop_erfolg zuerst -> ein
            # spaeteres loop_failed wurde ignoriert (Bug OP-371). Jetzt:
            # eine Query ueber alle 3 Kinds, kind des Neuesten entscheidet.
            if aus["loop_status"] != "running":
                term = c.execute(
                    "SELECT run_id, ts, kind FROM events "
                    "WHERE kind IN ('loop_erfolg', 'loop_failed', 'loop_ended') "
                    "AND project=? "
                    "AND run_id IS NOT NULL AND run_id != '' "
                    "ORDER BY seq DESC LIMIT 1",
                    (projekt,),
                ).fetchone()
                if term:
                    ist_failed = term[2] == "loop_failed"
                    aus["loop_status"] = "failed" if ist_failed else "done"
                    aus["last_run"] = {
                        "run_id": term[0],
                        "ts": term[1],
                        "erfolg": not ist_failed,
                    }

            # 3. Gates: DISTINCT auf allen drei
            opens = {
                r[0] for r in c.execute(
                    "SELECT DISTINCT json_extract(payload, '$.gate_id') "
                    "FROM events WHERE kind='gate_open' AND project=?",
                    (projekt,),
                ) if r[0]
            }
            answered = {
                r[0] for r in c.execute(
                    "SELECT DISTINCT json_extract(payload, '$.gate_id') "
                    "FROM events WHERE kind='gate_answered' AND project=?",
                    (projekt,),
                ) if r[0]
            }
            expired = {
                r[0] for r in c.execute(
                    "SELECT DISTINCT json_extract(payload, '$.gate_id') "
                    "FROM events WHERE kind='gate_expired' AND project=?",
                    (projekt,),
                ) if r[0]
            }
            # OP-381d: Konsistenz mit aggregate_gate_context herstellen.
            # Vorher: ambient zaehlte projektweit (alle Runs), context
            # nur letzte_run_id -> Widerspruch (Live 2026-11-09: 2 vs 0).
            # Alte Zaehlung bleibt als Fallback, falls aggregate_gate_context
            # selbst fehlschlaegt.
            _alt_zaehlung = len(opens - answered - expired)
    except sqlite3.Error:
        _alt_zaehlung = 0

    # OP-381d: Eine Wahrheit. aggregate_gate_context ist die Quelle.
    try:
        _gc = aggregate_gate_context(projekt, run_id=run_id)
        aus["gates_open"] = len(_gc.get("offene_gates") or [])
    except Exception:  # noqa: BLE001
        aus["gates_open"] = _alt_zaehlung

    # 4. Tokens
    try:
        tok = aggregate_tokens(projekt, run_id)
        aus["tokens"] = {
            "loop_total": tok["loop"]["total"],
            "chat_total": tok["chat"]["total"],
        }
    except Exception:  # noqa: BLE001
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
    "chat_job_queued": "Chat-Antwort eingeplant",
    "chat_job_started": "Chat-Pruefung gestartet",
    "chat_job_chunk": "Chat-Antwort",
    "chat_job_tool_call": "Chat-Tool gestartet",
    "chat_job_tool_result": "Chat-Tool abgeschlossen",
    "chat_job_succeeded": "Chat-Antwort fertig",
    "chat_job_failed": "Chat-Antwort fehlgeschlagen",
    "chat_job_cancelled": "Chat-Antwort abgebrochen",
    "chat_job_cancel_requested": "Chat-Abbruch angefordert",
    "chat_job_branch_cleanup_failed": "Chat-Arbeitszweig konnte nicht bereinigt werden",
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
    "loop_criteria_progress": "Akzeptanzkriterien: Fortschritt",
    "loop_chat_job_observed": "Parallelen Chat-Job am Checkpoint erkannt",
    "loop_chat_job_result_observed": "Ergebnis eines parallelen Chat-Jobs erkannt",
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
    "loop_verify_recovery_started": "Abschlussprüfung: gezielte Reparatur gestartet",
    "loop_verify_recovery_error": "Abschlussprüfung: Reparaturfehler",
    "loop_verify_recovered": "Abschlussprüfung nach Reparatur bestanden",
    "loop_verify_recovery_stalled": "Abschlussprüfung: Reparatur noch nicht erfolgreich",
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
    "progress": "Fortschritt",
    "llm_call": "LLM-Aufruf",
    "llm_call_start": "Modellaufruf startet",
    "llm_call_heartbeat": "Modellaufruf läuft",
    "llm_call_end": "Modellaufruf beendet",
    "llm_usage": "LLM-Token",
    "llm_timeout_read": "LLM-Timeout (read)",
    "llm_timeout_gesamt": "LLM-Timeout (gesamt)",
    "command_executed": "Befehl ausgefuehrt",
    "command_rejected": "Befehl abgelehnt",
}

_TL_SKIP: frozenset[str] = frozenset({
    "heartbeat", "spinner", "log_line", "summary",
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
    if kind == "chat_job_succeeded":
        return "ok"
    if kind in ("chat_job_failed",):
        return "error"
    if kind.startswith("chat_job_"):
        return "running" if payload.get("status") == "running" else "info"
    # Info-Events (kein Fehler, nur Hinweis auf Fallback/Start)
    if kind in ("loop_plan_missing", "loop_preflight_fehler",
                "loop_plan_reflection"):
        return "info"
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
    if kind.startswith("chat_job_"):
        event_kind = kind.removeprefix("chat_job_")
        if event_kind == "queued":
            return "Chat-Nachricht eingegangen"
        if event_kind == "started":
            return "Projekt wird geprueft"
        if event_kind == "chunk":
            return str(payload.get("text") or "")[:160]
        if event_kind == "tool_call":
            return f"Tool: {str(payload.get('name') or 'unbekannt')[:80]}"
        if event_kind == "tool_result":
            return f"Ergebnis: {str(payload.get('content') or '')[:120]}"
        if event_kind == "branch_cleanup_failed":
            return "Chat-Job: Sitzungszweig konnte nicht bereinigt werden"
        if event_kind == "succeeded":
            return str(payload.get("answer") or "Antwort fertig")[:160]
        if event_kind == "failed":
            return str(payload.get("error") or "Chat-Antwort fehlgeschlagen")[:160]
        if event_kind in ("cancel_requested", "cancelled"):
            return (
                "Chat-Abbruch angefordert" if event_kind == "cancel_requested"
                else "Chat-Antwort abgebrochen"
            )
        return str(payload.get("text") or event_kind)[:160]
    if kind == "loop_chat_job_observed":
        mode = str(payload.get("mode") or "Chat")
        job_id = str(payload.get("job_id") or "")
        suffix = f" ({job_id[:12]})" if job_id else ""
        return f"Paralleler {mode}-Auftrag am sicheren Punkt erkannt{suffix}"
    if kind == "loop_chat_job_result_observed":
        state = str(payload.get("state") or "unbekannt")
        job_id = str(payload.get("job_id") or "")
        suffix = f" ({job_id[:12]})" if job_id else ""
        answer_hash = payload.get("answer_sha256")
        if answer_hash:
            suffix += f" · Ergebnisbeleg {str(answer_hash)[:12]}"
        return f"Paralleler Chat-Job {state}{suffix}"
    if kind == "loop_criteria_progress":
        covered = payload.get("covered")
        remaining = payload.get("remaining")
        covered_count = len(covered) if isinstance(covered, list) else 0
        remaining_count = len(remaining) if isinstance(remaining, list) else 0
        task = str(payload.get("task_id") or "").strip()
        suffix = f" nach {task}" if task else ""
        if payload.get("tracked") is False:
            summary = f"Zielabgleich ohne explizite Kriterienzuordnung{suffix}"
        else:
            summary = f"{covered_count} erledigt, {remaining_count} offen{suffix}"
        next_step = str(payload.get("next_step") or "").strip()
        if next_step:
            summary += f"; danach: {next_step[:120]}"
        return summary
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
    if kind == "llm_call_end":
        return (
            f"{payload.get('agent', '?')}: "
            f"{payload.get('elapsed_s', 0)}s, "
            f"{payload.get('content_len', 0)} Zeichen"
        )
    if kind in ("llm_call_start", "llm_call_heartbeat"):
        task_name = str(payload.get("task_name") or "").strip()
        task_id = str(payload.get("task_id") or "").strip()
        task = task_name or (f"Task {task_id}" if task_id else "")
        files = payload.get("files")
        if isinstance(files, list):
            file_names = [
                str(path).strip()[:120] for path in files
                if isinstance(path, str) and path.strip()
            ][:2]
        else:
            file_names = []
        context = " · ".join(part for part in [task, ", ".join(file_names)] if part)
        if kind == "llm_call_heartbeat":
            elapsed = payload.get("elapsed_s")
            timing = f" · {elapsed}s" if isinstance(elapsed, (int, float)) else ""
            return (
                f"arbeitet weiter{': ' + context if context else ''}{timing}"
            )
        return f"startet Modellaufruf{': ' + context if context else ''}"
    if kind == "loop_plan_missing":
        auf = str(payload.get("aufgabe", ""))[:80]
        return f"kein initialer Plan — Aufgabe: {auf}" if auf else "kein initialer Plan"
    if kind == "loop_plan_reflection_abgebrochen":
        regel = payload.get("regel", "?")
        fakt = str(payload.get("fakt", ""))[:80]
        return f"regel={regel} — {fakt}" if fakt else f"regel={regel}"
    if kind == "planner_plan_erstellt":
        n = payload.get("tasks", 0)
        pl = payload.get("prosa_len", 0)
        return f"{n} Tasks, {pl} Zeichen Prosa"
    if kind == "planner_architect_ok":
        return f"prosa_len={payload.get('prosa_len', 0)}"
    if kind == "planner_split":
        return f"{payload.get('anzahl', 0)} Tasks"
    if kind == "planner_split_vor_merge":
        return f"{payload.get('anzahl', 0)} Tasks"
    if kind == "planner_scout_ok":
        def _zahl(v):
            if isinstance(v, int):
                return v
            if isinstance(v, (list, tuple, dict)):
                return len(v)
            return 0
        n = _zahl(payload.get("dateien"))
        r = _zahl(payload.get("risiken"))
        return f"{n} Dateien, {r} Risiken"
    if kind == "loop_gate_failed":
        return f"gate={payload.get('gate', '?')}, grund={payload.get('grund', '?')}"
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
    # OP-394: semantische Aktionen fuer loop_phase (statt technischer Kinds)
    if kind == "loop_phase":
        phase = str(payload.get("phase") or payload.get("name") or "").lower()
        if "architect" in phase:
            return "denkt nach"
        if "planner" in phase:
            return "splittet Plan"
        if "explorer" in phase or "explore" in phase:
            return "durchsucht Repo"
        if "scout" in phase:
            return "prüft Auftrag"
        if "builder" in phase or phase == "build":
            return "baut"
        if "reviewer" in phase or phase == "review":
            return "prüft Code"
        if "verify" in phase:
            return "verifiziert"
        if "reflection" in phase or "reflect" in phase:
            return "reflektiert"
        if "plan_gate" in phase:
            return "wartet auf Plan-Freigabe"
        if "human_gate" in phase:
            return "wartet auf Antwort"
        return phase or ""
    # OP-394: Gate-Events sichtbar machen
    if kind == "gate_open":
        prompt = str(payload.get("prompt") or "")[:60].strip()
        return f"öffnet Gate: {prompt}" if prompt else "öffnet Gate"
    if kind == "gate_answered":
        ans = payload.get("answer") or payload.get("antwort") or "?"
        return f"Antwort: {ans}"
    if kind == "loop_plan_shown":
        return "Plan-Gate geöffnet (j/n/a)"
    if kind == "loop_plan_gate_approved":
        return "Plan freigegeben"
    if kind == "loop_plan_gate_rejected":
        return "Plan abgelehnt"
    if kind == "loop_started":
        return "Loop startet"
    if kind == "loop_fresh_reset":
        return "Fresh-Start (alte Phase verworfen)"
    if kind == "summary":
        return "Loop beendet"
    if kind == "loop_human_gate_eof":
        return "⚠️ Human-Gate EOF (stdin geschlossen)"
    return ""


def _tl_menschliche_phase(pname: str) -> str:
    low = pname.lower()
    for key, label in _TL_PHASEN_NAMEN.items():
        if key in low:
            return label
    return pname or "Phase"


# ---------------------------------------------------------------------------
# OP-381h (2026-11-09): Timeline-Rollen — welche Rolle gehoert zu welchem Event?
# Wird im UI als Farbcodierung genutzt (sem-Farben, siehe layout.css).
# ---------------------------------------------------------------------------

_TL_AGENT_ROLLEN: dict[str, str] = {
    "explorer": "explorer",
    "scout": "scout",
    "architect": "architect",
    "planner": "planner",
    "builder": "builder",
    "reviewer": "reviewer",
    "reflection": "reflection",
    "verify": "verify",
    "agent_pipeline": "loop",
}

_TL_KIND_ROLLEN: tuple[tuple[str, str], ...] = (
    # Loop-emittierte Rollen-Events haben "loop_"-Prefix
    # (loop_explorer_*, loop_scout_*, loop_planner_*, loop_architect_*).
    # Die reinen Prefixe (explorer_*, ...) matchen nur Events von
    # den Rollen-Agenten selbst.
    ("loop_explorer_", "explorer"),
    ("loop_scout_", "scout"),
    ("loop_planner_", "planner"),
    ("loop_architect_", "architect"),
    ("loop_builder_", "builder"),
    ("loop_reviewer_", "reviewer"),
    ("loop_reflection_", "reflection"),
    ("loop_verify_", "verify"),
    ("builder_", "builder"),
    ("reviewer_", "reviewer"),
    ("reflection_", "reflection"),
    ("explorer_", "explorer"),
    ("scout_", "scout"),
    ("planner_", "planner"),
    ("architect_", "architect"),
    ("verify_", "verify"),
    ("loop_plan_gate_", "loop"),
    ("loop_human_gate_", "loop"),
    ("loop_plan_", "loop"),
    ("loop_task_", "loop"),
    ("loop_phase", "loop"),
    ("gate_", "loop"),
)


def _tl_rolle(agent: str, kind: str) -> str:
    """Mappt agent-Feld + kind auf semantische Rolle (fuer Farbe im UI).

    Prioritaet:
    1. Agent ist eine ECHTE Rolle (explorer, builder, architect, ...) —
       gewinnt immer (das ist wer den Code ausfuehrt).
    2. Sonst kind-Prefix — der Loop (``agent_pipeline``) emittiert
       Rollen-Events mit kind-Praefix (``loop_explorer_*``,
       ``loop_builder_*``) und meint damit die Rolle im Namen.
    3. Fallback ``loop`` (Loop-interne Events ohne Rollenbezug).

    ``agent_pipeline`` bekommt bewusst KEINEN Vorrang: sonst wuerde
    ``loop_explorer_suchbegriffe`` (agent=agent_pipeline, kind-Prefix
    ``loop_explorer_``) als ``loop`` statt ``explorer`` markiert und
    die Timeline-Farbcodierung wird einfarbig.
    """
    a = (agent or "").lower()
    k = (kind or "").lower()
    if k.startswith("chat_job_"):
        return "chat"
    # Echte Rolle aus agent (Loop-Marker ueberspringen)
    if a and a != "agent_pipeline" and a in _TL_AGENT_ROLLEN:
        return _TL_AGENT_ROLLEN[a]
    # Rollen-Praefix aus kind (Loop-emittierte Events)
    for prefix, rolle in _TL_KIND_ROLLEN:
        if k.startswith(prefix):
            return rolle
    return "loop"


def _tl_aggregate_aktiv(
    run_events: list[dict[str, Any]],
    stale_after_s: int = 300,
    grace_s: int = 0,
) -> dict[str, Any]:
    """Wer arbeitet JETZT am Run?

    Offene Tasks bleiben aktiv, bis ein Task-Abschluss oder ein Run-Ende
    protokolliert ist. Dadurch loeschen Builder-/Verify-Kontext-Events den
    laufenden Task nicht aus der Aktiv-Anzeige. Die Stale-Grenze gilt weiter.
    """
    from datetime import UTC
    from datetime import datetime as _dt

    if not run_events:
        return {}

    terminal_runs = {
        "loop_failed", "loop_erfolg", "loop_ended", "loop_stopped",
        "loop_aborted", "summary",
    }
    task_terminals = {
        "loop_task_ok", "loop_task_failed", "loop_task_blocked",
    }
    latest = run_events[-1]
    latest_kind = str(latest.get("kind", ""))

    # Ein offener Gate-Dialog hat Vorrang vor dem noch nicht abgeschlossenen
    # Task, weil der Run an dieser Stelle tatsaechlich auf den Menschen wartet.
    if latest_kind == "gate_open":
        ts_raw = latest.get("timestamp") or latest.get("ts") or ""
        try:
            ts = _dt.fromisoformat(str(ts_raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            delta_s = (_dt.now(UTC) - ts).total_seconds()
        except (ValueError, TypeError):
            return {}
        if delta_s < 0 or delta_s > stale_after_s:
            return {}
        return {
            "rolle": "loop",
            "aktion": "wartet auf Antwort",
            "seit_s": int(delta_s),
            "kind": latest_kind,
        }

    # Das letzte Task-Start-Event bleibt bis zum passenden terminalen
    # Task-Event offen. Zwischenereignisse wie builder_file_context,
    # verify stages oder LLM heartbeats beschreiben den aktiven Task weiter.
    task_start_index: int | None = None
    for index, event in enumerate(run_events):
        event_kind = str(event.get("kind", ""))
        if event_kind == "loop_task_start":
            task_start_index = index
        elif event_kind in task_terminals:
            task_start_index = None

    if (
        task_start_index is not None
        and latest_kind not in terminal_runs
    ):
        task_start = run_events[task_start_index]
        task_payload = task_start.get("payload")
        if not isinstance(task_payload, dict):
            task_payload = {}
        task_name = str(
            task_payload.get("name") or task_payload.get("text") or "",
        ).strip()

        # Parallel laufende Chat-Jobs duerfen den eigentlichen Loop-Task in
        # der Control-Anzeige nicht verdecken.
        activity = next(
            (
                event for event in reversed(run_events[task_start_index:])
                if not str(event.get("kind", "")).startswith("chat_job_")
            ),
            task_start,
        )
        activity_kind = str(activity.get("kind", ""))
        role = "loop"
        for event in reversed(run_events[task_start_index:]):
            event_kind = str(event.get("kind", ""))
            if event_kind.startswith("chat_job_"):
                continue
            candidate_role = _tl_rolle(
                str(event.get("agent", "")), event_kind,
            )
            if candidate_role != "loop":
                role = candidate_role
                break

        ts_raw = activity.get("timestamp") or activity.get("ts") or ""
        try:
            ts = _dt.fromisoformat(str(ts_raw))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            delta_s = (_dt.now(UTC) - ts).total_seconds()
        except (ValueError, TypeError):
            return {}
        if delta_s < 0 or delta_s > stale_after_s:
            return {}

        verbs = {
            "builder": "baut",
            "reviewer": "prueft den Code",
            "verify": "verifiziert",
            "reflection": "behebt den Befund",
            "explorer": "untersucht das Repository",
            "scout": "prueft den Auftrag",
            "architect": "formt den Plan",
            "planner": "zerlegt den Plan",
        }
        verb = verbs.get(role, "bearbeitet")
        action = f"{verb}: {task_name}" if task_name else f"{verb} den Task"
        # Ein heartbeat enthaelt konkreteren Task-/Dateikontext als der
        # generische Task-Name; diesen behalten wir fuer die Live-Anzeige.
        if activity_kind == "llm_call_heartbeat":
            action = _tl_detail(activity_kind, activity) or action
        progress_kinds = {
            "llm_call", "llm_call_start", "llm_call_heartbeat",
            "loop_task_start",
        }
        visible_kind = (
            activity_kind if (
                activity_kind.endswith("_start")
                or activity_kind in progress_kinds
            ) else "loop_task_start"
        )
        return {
            "rolle": role,
            "aktion": action[:120],
            "seit_s": int(delta_s),
            "kind": visible_kind,
            "activity_kind": activity_kind,
            "task_id": task_payload.get("task_id"),
        }

    letztes = latest
    kind = latest_kind
    agent = str(letztes.get("agent", ""))
    ts_raw = letztes.get("timestamp") or letztes.get("ts") or ""

    ist_aktiv = (
        kind.endswith("_start")
        or kind in (
            "llm_call", "llm_call_start", "llm_call_heartbeat",
            "loop_task_start", "gate_open",
        )
        or (
            kind.startswith("chat_job_")
            and letztes.get("status") == "running"
        )
    )
    if not ist_aktiv:
        # Gerade abgeschlossene Schritte bleiben kurz sichtbar, werden aber
        # nach dem Grace-Fenster korrekt als abgeschlossen dargestellt.
        if grace_s > 0 and (
            kind.endswith(("_ok", "_failed", "_done"))
            or kind in (
                "chat_job_succeeded", "chat_job_failed",
                "chat_job_cancelled", "summary",
            )
        ):
            try:
                ts_g = _dt.fromisoformat(str(ts_raw))
                if ts_g.tzinfo is None:
                    ts_g = ts_g.replace(tzinfo=UTC)
                delta_g = (_dt.now(UTC) - ts_g).total_seconds()
            except (ValueError, TypeError):
                return {}
            if 0 <= delta_g < grace_s:
                return {
                    "rolle": _tl_rolle(agent, kind),
                    "aktion": _tl_detail(kind, letztes) or kind,
                    "seit_s": int(delta_g),
                    "kind": kind,
                    "gerade_fertig": True,
                }
        return {}

    try:
        ts = _dt.fromisoformat(str(ts_raw))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        delta_s = (_dt.now(UTC) - ts).total_seconds()
    except (ValueError, TypeError):
        return {}
    if delta_s < 0 or delta_s > stale_after_s:
        return {}

    payload = letztes.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    aktion = _tl_detail(kind, {**letztes, **payload}) or kind
    return {
        "rolle": _tl_rolle(agent, kind),
        "aktion": str(aktion)[:120],
        "seit_s": int(delta_s),
        "kind": kind,
    }

def aggregate_swimlane(
    projekt: str, run_id: str | None = None,
) -> dict[str, Any]:
    """OP-381i: Swimlane-Wasserfall-Daten fuer den Control-Modus.

    Liefert pro Rolle (explorer, scout, architect, ...) eine Lane mit
    Zeit-Balken. Jeder Balken hat start_ts, end_ts, dauer_s, status,
    kind, detail. Aktiv-Lane wird markiert.

    Gruppierung:
      * _start/_end-Paare (llm_call_start + llm_call_end) -> ein Balken
      * loop_task_start + loop_task_ok/failed -> ein Balken mit Task-ID
      * Einzel-Events -> 0.5s-Balken (Sichtbarkeit vor Genauigkeit)

    Filter: -migrated-*-Dateien (statische Dumps) werden ignoriert.
    Fallback run_id: letzter Run in der aktuellsten Datei.

    Kein UI-Code — Frontend (waterfall.js) folgt im naechsten Block.
    """
    from datetime import datetime as _dt

    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return {"run_id": "", "lanes": [], "zeitspanne": None, "aktiv": {}}

    kandidaten = sorted(
        f for f in audit_dir.glob("agent-pipeline-*.jsonl")
        if "-migrated-" not in f.name
    )
    if not kandidaten:
        return {"run_id": "", "lanes": [], "zeitspanne": None, "aktiv": {}}

    datei = kandidaten[-1]
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
        return {"run_id": "", "lanes": [], "zeitspanne": None, "aktiv": {}}

    # Projektgrenze gilt fuer implizite und explizite Run-IDs.
    events = [
        e for e in events if (e.get("project") or "werkstatt") == projekt
    ]

    # Run-Filter
    if run_id is None:
        for ev in reversed(events):
            rid = ev.get("run_id")
            if rid:
                run_id = str(rid)
                break
    if not run_id:
        return {"run_id": "", "lanes": [], "zeitspanne": None, "aktiv": {}}
    events = [e for e in events if str(e.get("run_id", "")) == run_id]
    if not events:
        return {"run_id": run_id, "lanes": [], "zeitspanne": None, "aktiv": {}}

    # Nach Zeit sortieren
    def _ts_key(e: dict[str, Any]) -> float:
        ts = e.get("timestamp") or e.get("ts") or ""
        try:
            dt = _dt.fromisoformat(str(ts))
            if dt.tzinfo is None:
                from datetime import UTC
                dt = dt.replace(tzinfo=UTC)
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0.0

    events_sorted = sorted(events, key=_ts_key)

    # Start-/End-Paare erkennen: map "gate_id/pseudo-key" -> start-event
    # Wir bauen Balken: jedes Event mit "_start" endet mit passendem "_end";
    # loop_task_start endet mit loop_task_ok/_failed; alles andere = 0.5s.
    lanes: dict[str, list[dict[str, Any]]] = {}

    # Helper
    def _add_balken(rolle: str, balken: dict[str, Any]) -> None:
        if rolle not in lanes:
            lanes[rolle] = []
        lanes[rolle].append(balken)

    def _make_balken(ev: dict[str, Any], ende_ev: dict[str, Any] | None) -> dict[str, Any]:
        rolle = _tl_rolle(
            str(ev.get("agent", "")), str(ev.get("kind", ""))
        )
        ts_start = _ts_key(ev)
        ts_ende = _ts_key(ende_ev) if ende_ev else ts_start + 0.5
        dauer = max(0.0, ts_ende - ts_start)
        kind = str(ev.get("kind", ""))
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        detail = _tl_detail(kind, {**ev, **payload}) or kind
        return {
            "rolle": rolle,
            "kind": kind,
            "start_ts": ev.get("timestamp") or ev.get("ts") or "",
            "end_ts": (ende_ev.get("timestamp") or ende_ev.get("ts") or "")
                      if ende_ev else "",
            "dauer_s": round(dauer, 3),
            "status": _tl_status(kind, {**ev, **payload}),
            "detail": str(detail)[:120],
            "task_id": str(payload.get("task_id", "") or payload.get("id", "")),
            "agent": str(ev.get("agent", "")),
        }

    # Paar-Logik: nimm das naechste "passende" End-Event
    verbraucht: set[int] = set()
    i = 0
    while i < len(events_sorted):
        if i in verbraucht:
            i += 1
            continue
        ev = events_sorted[i]
        kind = str(ev.get("kind", ""))
        ende: dict[str, Any] | None = None

        if kind.endswith("_start"):
            # Suche das naechste *_end / *_ok / *_failed zur gleichen Rolle+Kind-Familie
            basis = kind[:-6]  # "llm_call_start" -> "llm_call"
            for j in range(i + 1, len(events_sorted)):
                if j in verbraucht:
                    continue
                kj = str(events_sorted[j].get("kind", ""))
                if kj in (basis + "_end", basis + "_ok", basis + "_failed"):
                    ende = events_sorted[j]
                    verbraucht.add(j)
                    break
        elif kind == "loop_task_start":
            for j in range(i + 1, len(events_sorted)):
                if j in verbraucht:
                    continue
                kj = str(events_sorted[j].get("kind", ""))
                if kj in ("loop_task_ok", "loop_task_failed", "loop_task_blocked"):
                    ende = events_sorted[j]
                    verbraucht.add(j)
                    break
        elif kind == "loop_phase" and (
            (ev.get("status") if "status" in ev else
             (ev.get("payload") or {}).get("status")) == "start"
        ):
            pname = (ev.get("phase")
                     or (ev.get("payload") or {}).get("phase") or "")
            for j in range(i + 1, len(events_sorted)):
                if j in verbraucht:
                    continue
                evj = events_sorted[j]
                kj = str(evj.get("kind", ""))
                pj = (evj.get("phase")
                      or (evj.get("payload") or {}).get("phase") or "")
                if kj == "loop_phase" and pj == pname:
                    ende = evj
                    verbraucht.add(j)
                    break

        balken = _make_balken(ev, ende)
        _add_balken(balken["rolle"], balken)
        i += 1

    # Zeitspanne total
    if events_sorted:
        start_first = _ts_key(events_sorted[0])
        end_last = _ts_key(events_sorted[-1])
        zeitspanne = {
            "start_ts": events_sorted[0].get("timestamp")
                        or events_sorted[0].get("ts") or "",
            "end_ts": events_sorted[-1].get("timestamp")
                      or events_sorted[-1].get("ts") or "",
            "dauer_s": round(max(0.0, end_last - start_first), 3),
        }
    else:
        zeitspanne = None

    # Aktiv-Rolle aus letztem Event
    aktiv = _tl_aggregate_aktiv(events_sorted)

    # Lanes in Rollen-Reihenfolge (ADSK: Explorer zuerst, Loop zuletzt)
    ROLLEN_REIHENFOLGE = [
        "explorer", "scout", "architect", "planner",
        "builder", "verify", "reviewer", "reflection", "loop",
    ]
    lanes_liste: list[dict[str, Any]] = []
    for rolle in ROLLEN_REIHENFOLGE:
        if lanes.get(rolle):
            lanes_liste.append({
                "rolle": rolle,
                "balken": lanes[rolle],
            })
    # Sonstige Rollen (falls neue dazukommen)
    for rolle, balken_liste in lanes.items():
        if rolle not in ROLLEN_REIHENFOLGE and balken_liste:
            lanes_liste.append({"rolle": rolle, "balken": balken_liste})

    return {
        "run_id": run_id,
        "lanes": lanes_liste,
        "zeitspanne": zeitspanne,
        "aktiv": aktiv,
    }


# OP-381j: Naechster-Schritt-Heuristik fuer Live-Feed.
# Aus aktiv.rolle -> wahrscheinliche naechste Rolle.
_NAECHSTER_NACH_ROLLE: dict[str, str] = {
    "explorer": "scout",
    "scout": "architect",
    "architect": "planner",
    "planner": "builder",
    "builder": "verify",
    "verify": "reviewer",
    "reviewer": "loop",       # Phase-Ende oder naechster Task
    "reflection": "builder",  # zurueck in den Builder nach Repair
    "loop": "",               # Loop-intern, kein Vorhersage-Wert
}


def _tl_public_text(value: Any, limit: int = 240) -> str:
    """Normalisiert ausschliesslich explizite, fuer die UI freigegebene Kurztexte."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def aggregate_live_feed(
    projekt: str, run_id: str | None = None, limit: int = 30,
) -> dict[str, Any]:
    """OP-381j: Vertikale Chronologie fuer den Control-Modus.

    Liefert die letzten ``limit`` Events als sequenzielle Steps
    (aufsteigend sortiert — aelteste zuerst, damit das Frontend wie
    ein Log liest). Zusaetzlich:

    - ``aktiv``: {rolle, aktion, seit_s, kind} aus dem aktuell
      laufenden Event (aus _tl_aggregate_aktiv).
    - ``naechster``: {rolle, kind} Heuristik aus aktiv.rolle, oder
      leer wenn nichts laeuft.
    - ``zeitspanne``: {start_ts, end_ts, dauer_s}.

    Unterschied zu aggregate_swimlane:
    - swimlane: aggregiert pro Rolle, Zeit-Balken (Nachanalyse).
    - live_feed: sequenziell, jede Zeile ein Event (Live-Verfolgung).
    """
    from datetime import datetime as _dt

    audit_dir = werkstatt_home() / "audit-logs"
    leer: dict[str, Any] = {
        "run_id": "", "steps": [], "aktiv": {},
        "naechster": {}, "zeitspanne": None,
    }
    if not audit_dir.exists():
        return leer

    kandidaten = sorted(
        f for f in audit_dir.glob("agent-pipeline-*.jsonl")
        if "-migrated-" not in f.name
    )
    if not kandidaten:
        return leer

    datei = kandidaten[-1]
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
        return leer

    # Projektgrenze gilt fuer implizite und explizite Run-IDs.
    events = [
        e for e in events if (e.get("project") or "werkstatt") == projekt
    ]

    # Run-Filter
    if run_id is None:
        for ev in reversed(events):
            rid = ev.get("run_id")
            if rid:
                run_id = str(rid)
                break
    if not run_id:
        return leer
    events = [e for e in events if str(e.get("run_id", "")) == run_id]
    try:
        timeline = EventStore(
            db_pfad=werkstatt_home() / ".werkstatt" / "events.db",
        ).query(run_id, limit=1000, project=projekt)
    except (OSError, sqlite3.Error, ValueError):
        timeline = []
    def _chat_event_key(event: dict[str, Any]) -> tuple[str, str, str] | None:
        kind = str(event.get("kind", ""))
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        job = event.get("job_id") or payload.get("job_id")
        seq = event.get("job_event_seq") or payload.get("job_event_seq")
        if not kind.startswith("chat_job_") or not job or seq is None:
            return None
        return kind, str(job), str(seq)

    chat_keys = {
        key for event in events if (key := _chat_event_key(event)) is not None
    }
    for ev in timeline:
        kind = str(ev.get("kind", ""))
        if not kind.startswith("chat_job_"):
            continue
        event = {
            "run_id": run_id,
            "kind": kind,
            "agent": "chat",
            "timestamp": ev.get("ts") or "",
            "status": ev.get("status"),
            "payload": ev.get("payload") or {},
        }
        key = _chat_event_key(event)
        if key is not None and key in chat_keys:
            continue
        if key is not None:
            chat_keys.add(key)
        events.append(event)
    if not events:
        return {**leer, "run_id": run_id}

    # Nach Zeit sortieren
    def _ts_key(e: dict[str, Any]) -> float:
        ts = e.get("timestamp") or e.get("ts") or ""
        try:
            dt = _dt.fromisoformat(str(ts))
            if dt.tzinfo is None:
                from datetime import UTC
                dt = dt.replace(tzinfo=UTC)
            return dt.timestamp()
        except (ValueError, TypeError):
            return 0.0

    events_sorted = sorted(events, key=_ts_key)

    # Kontext aus den bereits vorhandenen Phasen-/Task-Markern fortschreiben.
    # So bleiben Ergebnisse einer Task zugeordnet, auch wenn das End-Event
    # selbst nur die Task-ID traegt.
    aktuelle_phase = ""
    aktuelle_task_id = ""
    aktuelle_task_name = ""
    for event in events_sorted:
        kind = str(event.get("kind", ""))
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = event
        if kind == "loop_phase":
            aktuelle_phase = _tl_public_text(
                payload.get("phase") or payload.get("name")
                or event.get("phase"), 80,
            )
            aktuelle_task_id = ""
            aktuelle_task_name = ""
        elif kind == "loop_task_start":
            aktuelle_task_id = _tl_public_text(
                payload.get("task_id") or payload.get("id"), 80,
            )
            aktuelle_task_name = _tl_public_text(
                payload.get("name") or payload.get("text"), 160,
            )
        event["_timeline_phase"] = (
            _tl_public_text(payload.get("phase") or event.get("phase"), 80)
            or aktuelle_phase
        )
        event["_timeline_task_id"] = (
            _tl_public_text(payload.get("task_id") or payload.get("id"), 80)
            or aktuelle_task_id
        )
        event["_timeline_task_name"] = (
            _tl_public_text(payload.get("name") or payload.get("text"), 160)
            or aktuelle_task_name
        )
        if kind in ("loop_task_ok", "loop_task_failed"):
            aktuelle_task_id = ""
            aktuelle_task_name = ""

    # Aktiv-Snapshot: letzter 'in progress'-Event
    aktiv_raw = _tl_aggregate_aktiv(events_sorted, grace_s=5)

    # Letzte N Events (aufsteigend) als Steps
    # Aktiv-Event wird NICHT als normaler Step gezaehlt (kommt extra).
    aktiv_ts = ""
    if aktiv_raw and events_sorted and not aktiv_raw.get("gerade_fertig"):
        letzter = events_sorted[-1]
        if (str(letzter.get("kind", "")) == aktiv_raw.get("kind")
                and _tl_rolle(str(letzter.get("agent", "")),
                              str(letzter.get("kind", "")))
                == aktiv_raw.get("rolle")):
            aktiv_ts = str(letzter.get("timestamp") or letzter.get("ts") or "")
    steps_quellen = [
        e for e in events_sorted
        if str(e.get("timestamp") or e.get("ts") or "") != aktiv_ts
    ] if aktiv_ts else events_sorted
    letzte = steps_quellen[-limit:] if len(steps_quellen) > limit else steps_quellen

    steps: list[dict[str, Any]] = []
    for ev in letzte:
        kind = str(ev.get("kind", ""))
        agent = str(ev.get("agent", ""))
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        detail = _tl_detail(kind, {**ev, **payload}) or kind
        step: dict[str, Any] = {
            "ts": ev.get("timestamp") or ev.get("ts") or "",
            "rolle": _tl_rolle(agent, kind),
            "kind": kind,
            "detail": str(detail)[:200],
            "status": _tl_status(kind, {**ev, **payload}),
            "task_id": str(
                payload.get("task_id") or payload.get("id")
                or ev.get("_timeline_task_id") or ""
            ),
            "task_name": str(ev.get("_timeline_task_name") or ""),
            "project": projekt,
            "run_id": run_id,
            "phase": _tl_public_text(
                payload.get("phase") or ev.get("phase")
                or ev.get("_timeline_phase"), 80,
            ),
        }
        # Nur benannte Kurzfelder duerfen in die Timeline. Beliebige Prompt-,
        # Reasoning- oder Rohpayload-Felder werden bewusst nicht weitergereicht.
        for feld in ("result_summary", "decision_summary", "next_step"):
            wert = _tl_public_text(payload.get(feld))
            if wert:
                step[feld] = wert
        evidence = payload.get("evidence")
        if isinstance(evidence, str):
            evidence_items = [evidence]
        elif isinstance(evidence, list):
            evidence_items = evidence
        else:
            evidence_items = []
        beleg_kurz = [
            text for item in evidence_items
            if (text := _tl_public_text(item, 180))
        ][:5]
        if beleg_kurz:
            step["evidence"] = beleg_kurz
        steps.append(step)

    # Naechster-Schritt-Heuristik
    naechster: dict[str, str] = {}
    if aktiv_raw:
        rolle = str(aktiv_raw.get("rolle", ""))
        nxt = _NAECHSTER_NACH_ROLLE.get(rolle, "")
        if nxt:
            naechster = {"rolle": nxt}

    # Zeitspanne
    if events_sorted:
        zeitspanne = {
            "start_ts": events_sorted[0].get("timestamp")
                        or events_sorted[0].get("ts") or "",
            "end_ts": events_sorted[-1].get("timestamp")
                      or events_sorted[-1].get("ts") or "",
            "dauer_s": round(
                max(0.0, _ts_key(events_sorted[-1])
                    - _ts_key(events_sorted[0])), 3,
            ),
        }
    else:
        zeitspanne = None

    return {
        "run_id": run_id,
        "steps": steps,
        "aktiv": aktiv_raw,
        "naechster": naechster,
        "zeitspanne": zeitspanne,
    }


def aggregate_timeline_aktiv(
    projekt: str, run_id: str | None = None,
) -> dict[str, Any]:
    """Endpoint-Helper: liest JSONL, ruft _tl_aggregate_aktiv.

    Doppelt Events lesen (aggregate_timeline liest auch) — der
    Overhead ist ~10ms, das ist billiger als ein Modul-Cache.
    """
    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return {}
    kandidaten = sorted(
        f for f in audit_dir.glob("agent-pipeline-*.jsonl")
        if "-migrated-" not in f.name
    )
    if not kandidaten:
        return {}
    datei = kandidaten[-1]
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
        return {}

    # Projektgrenze gilt auch bei expliziter Run-ID; sie ist kein
    # Berechtigungsnachweis. Legacy-Events ohne Projekt gehoeren zu werkstatt.
    events = [
        e for e in events if (e.get("project") or "werkstatt") == projekt
    ]
    if run_id is None:
        for ev in reversed(events):
            rid = ev.get("run_id")
            if rid:
                run_id = str(rid)
                break
    if run_id:
        events = [e for e in events if str(e.get("run_id", "")) == run_id]
    return _tl_aggregate_aktiv(events)


def aggregate_timeline(
    projekt: str, run_id: str | None = None, limit: int = 200,
) -> list[dict[str, Any]]:
    """Phasen-Knoten aus JSONL-Audit (menschlich lesbar).

    Die JSONL-Audit-Datei traegt die Phasen-Events (loop_phase,
    explorer_*, builder_*, verify_*, reviewer_*) — der Event-Store
    hat nur Task-Events ohne Kontext. Wir gruppieren nach
    loop_phase-Bloecken, mit Prolog-Block fuer alles davor.
    """
    # aggregate_timeline liest JSONL direkt (nicht SQLite) — kein
    # Read-Through noetig, die Datei ist immer aktuell.
    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return []
    # OP-381f: -migrated-*-Dateien sind statische DB-Dumps (aus
    # OP-323), keine fortlaufende Quelle. Ohne diesen Filter waehlt
    # kandidaten[-1] die alphabetisch letzte Datei — das ist
    # `agent-pipeline-migrated-2026-11-08.jsonl` (weil 'm' > '2'),
    # nicht die aktuelle `agent-pipeline-2026-11-09.jsonl`. Live-Bug
    # 2026-11-09: Timeline zeigte nur 4 alte gate_open-Events aus
    # einem Oktober-Run statt 143 Events aus dem 191006-Run.
    # Gleiches Muster wie Projector._jsonl_files() Zeile 85.
    kandidaten = sorted(
        f for f in audit_dir.glob("agent-pipeline-*.jsonl")
        if "-migrated-" not in f.name
    )
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

    # Projektgrenze gilt fuer implizite und explizite Run-IDs.
    # Legacy-Events ohne Projekt gehoeren zu werkstatt.
    events = [
        e for e in events if (e.get("project") or "werkstatt") == projekt
    ]

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
                "agent": str(ev.get("agent", "")),
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

    # OP-381h: Rolle pro Kind anreichern (fuer Farbcodierung im UI).
    for _k in knoten:
        for _ch in _k.get("children") or []:
            if isinstance(_ch, dict) and "rolle" not in _ch:
                _ch["rolle"] = _tl_rolle(
                    str(_ch.get("agent", "")), str(_ch.get("kind", ""))
                )

    return knoten[:limit]




# ---------------------------------------------------------------------------
# OP-306b: Overview-Aggregation (Multi-Projekt-Karten)
# ---------------------------------------------------------------------------

def _scan_projekte() -> list[Path]:
    """Listet Projekt-Verzeichnisse unter _PROJECTS_BASE mit docs/STATUS.md."""
    if not _PROJECTS_BASE.exists():
        return []
    out: list[Path] = []
    for p in sorted(_PROJECTS_BASE.iterdir()):
        if not p.is_dir():
            continue
        if not (p / "docs" / "STATUS.md").exists():
            continue
        out.append(p)
    return out


def _projekt_filter_sql() -> str:
    """Project column is canonical; legacy web stop events carry project in JSON."""
    return (
        "(CASE WHEN kind='web_loop_stopped' "
        "THEN json_extract(payload, '$.project') ELSE project END)=?"
    )


def _sparkline_30d(es: EventStore, projekt: str) -> list[int]:
    """30-Tage-Bucket-Liste eindeutiger Runs (aeltester zuerst)."""
    from datetime import date, timedelta

    buckets: dict[str, int] = {}
    try:
        with sqlite3.connect(es.db_pfad) as c:
            rows = c.execute(
                "SELECT substr(ts, 1, 10), COUNT(*) FROM ("
                "SELECT run_id, MAX(ts) AS ts FROM events "
                "WHERE kind IN ('loop_erfolg', 'loop_failed', 'loop_ended', "
                "'web_loop_stopped') AND " + _projekt_filter_sql() + " "
                "AND ts >= date('now', '-30 days') AND run_id != '' "
                "GROUP BY run_id) GROUP BY substr(ts, 1, 10)",
                (projekt,),
            ).fetchall()
        for tag, n in rows:
            buckets[str(tag)] = int(n)
    except sqlite3.Error:
        pass
    heute = date.today()
    return [
        buckets.get((heute - timedelta(days=i)).isoformat(), 0)
        for i in range(29, -1, -1)
    ]


def _runs_7d(es: EventStore, projekt: str) -> int:
    try:
        with sqlite3.connect(es.db_pfad) as c:
            row = c.execute(
                "SELECT COUNT(DISTINCT run_id) FROM events "
                "WHERE kind IN ('loop_erfolg', 'loop_failed', 'loop_ended', "
                "'web_loop_stopped') AND " + _projekt_filter_sql() + " "
                "AND ts >= date('now', '-7 days') AND run_id != ''",
                (projekt,),
            ).fetchone()
        return int(row[0] or 0) if row else 0
    except sqlite3.Error:
        return 0


def _run_verteilung_30d(es: EventStore, projekt: str) -> dict[str, int]:
    """Deduplicated 30-day run outcomes; an explicit web stop wins."""
    ergebnis = {
        "erfolg": 0, "fehlgeschlagen": 0, "abgebrochen": 0,
        "unverified": 0, "gesamt": 0,
    }
    try:
        with sqlite3.connect(es.db_pfad) as c:
            verification_rows = c.execute(
                "SELECT run_id, MIN(origin_verified) FROM events WHERE "
                + _projekt_filter_sql() + " AND run_id!='' GROUP BY run_id",
                (projekt,),
            ).fetchall()
            verifiziert = {
                str(run_id): bool(value)
                for run_id, value in verification_rows
            }
            rows = c.execute(
                "SELECT run_id, "
                "MAX(CASE WHEN kind='web_loop_stopped' THEN seq ELSE 0 END), "
                "MAX(CASE WHEN kind='loop_failed' THEN seq ELSE 0 END), "
                "MAX(CASE WHEN kind IN ('loop_erfolg', 'loop_ended') "
                "THEN seq ELSE 0 END) "
                "FROM events WHERE " + _projekt_filter_sql() + " "
                "AND ts >= date('now', '-30 days') "
                "AND kind IN ('loop_erfolg', 'loop_failed', 'loop_ended', "
                "'web_loop_stopped') AND run_id != '' "
                "GROUP BY run_id",
                (projekt,),
            ).fetchall()
        for run_id, stopped_seq, failed_seq, success_seq in rows:
            if not verifiziert.get(str(run_id), False):
                ergebnis["unverified"] += 1
                continue
            if stopped_seq:
                ergebnis["abgebrochen"] += 1
            elif failed_seq > success_seq:
                ergebnis["fehlgeschlagen"] += 1
            elif success_seq:
                ergebnis["erfolg"] += 1
        ergebnis["gesamt"] = sum(
            ergebnis[k]
            for k in ("erfolg", "fehlgeschlagen", "abgebrochen", "unverified")
        )
    except sqlite3.Error:
        pass
    return ergebnis


def aggregate_overview() -> dict[str, Any]:
    """OP-306b Etappe 1: Projekt-Liste mit KPI + Sparkline + letzter Run."""
    from datetime import UTC, datetime

    es = EventStore()
    projekte: list[dict[str, Any]] = []
    for p in _scan_projekte():
        name = p.name
        try:
            ops = parse_ops(p)
            ops_offen = sum(
                1 for op in ops
                if str(op.get("status", "")).lower() in ("open", "partial", "")
            )
        except (OSError, ValueError):
            ops_offen = 0

        try:
            ambient = aggregate_ambient(name)
        except (sqlite3.Error, ValueError):
            ambient = {"loop_status": "idle", "last_run": None}

        verteilung = _run_verteilung_30d(es, name)
        spark = _sparkline_30d(es, name)
        runs_7d_total = _runs_7d(es, name)
        bekannte_runs = sum(
            verteilung[k] for k in ("erfolg", "fehlgeschlagen", "abgebrochen")
        )
        quote = (
            round(verteilung["erfolg"] / bekannte_runs, 2)
            if bekannte_runs else None
        )

        status_md = p / "docs" / "STATUS.md"
        try:
            mtime = datetime.fromtimestamp(
                status_md.stat().st_mtime, tz=UTC,
            ).isoformat()
        except OSError:
            mtime = None

        projekte.append({
            "name": name,
            "pfad": str(p),
            "ops_offen": ops_offen,
            "loop_status": ambient.get("loop_status", "idle"),
            "letzter_run": ambient.get("last_run"),
            "runs_30d": spark,
            "runs_30d_total": verteilung["gesamt"],
            "runs_7d_total": runs_7d_total,
            "erfolgsquote_30d": quote,
            "ergebnisse_30d": verteilung,
            "status_md_mtime": mtime,
        })

    top_3 = sorted(
        projekte,
        key=lambda x: (x["runs_7d_total"], x["ops_offen"]),
        reverse=True,
    )[:3]
    top_3_namen = [x["name"] for x in top_3 if x["runs_7d_total"] > 0]

    gesamt = {
            key: sum(p["ergebnisse_30d"][key] for p in projekte)
        for key in (
            "erfolg", "fehlgeschlagen", "abgebrochen", "unverified", "gesamt",
        )
    }
    return {
        "projekte": projekte,
        "top_3": top_3_namen,
        "ergebnisse_30d": gesamt,
        "generated_at": datetime.now(UTC).isoformat(),
    }


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
    """Liest die letzten 3 JSONL-Audit-Dateien, optional auf run_id gefiltert."""
    audit_dir = werkstatt_home() / "audit-logs"
    if not audit_dir.exists():
        return []
    # OP-381 Bug B: *-migrated-*.jsonl sind statische DB-Dumps, keine
    # fortlaufende Quelle. Alphabetisch sortiert kommen sie NACH den
    # Tagesdateien (weil 'm' > '2'), und _audit_events(None) nimmt den
    # letzten run_id aus der kombinierten Liste -> landet in der migrated-
    # Datei statt im aktuellen Run. Filter wie projection.py (a640b19).
    kand = sorted(
        f for f in audit_dir.glob("agent-pipeline-*.jsonl")
        if "-migrated-" not in f.name
    )[-3:]
    if not kand:
        return []
    events: list[dict[str, Any]] = []
    for datei in kand:
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
                        # OP-381: JSONL hat "timestamp", Code liest "ts"
                        if "ts" not in obj and "timestamp" in obj:
                            obj["ts"] = obj["timestamp"]
                        events.append(obj)
        except OSError:
            continue
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
    _frische_projektion()
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
            } | {
                (e.get("payload") or {}).get("gate_id")
                for e in es.query(letzte_run_id, kind="gate_expired")
            }
            for ev in opens:
                pa = ev.get("payload") or {}
                if pa.get("gate_id") not in beantwortet:
                    offene.append({
                        "gate_id": pa.get("gate_id"),
                        "prompt": pa.get("prompt"),
                        "optionen": pa.get("optionen", "jna"),
                        # OP-381c: typ aus Payload, Fallback "jna" (AK n,
                        # rueckwaertskompatibel fuer alte Gates ohne typ)
                        "typ": pa.get("typ", "jna"),
                    })
        except Exception:  # noqa: S110
            pass

    # Gate-Validitaet aus Run-Lifecycle (explizite State-Machine).
    # Wenn der Run ein Terminal-Event hat (loop_ended / loop_failed),
    # sind alle Gates des Runs abgebrochen — egal was EventStore sagt.
    if offene and letzte_run_id:
        _terminal = {"loop_ended", "loop_failed", "loop_crashed"}
        try:
            _run_evs = _audit_events(letzte_run_id)
            if any(e.get("kind") in _terminal for e in _run_evs):
                offene = []
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

    # Diff-Info: was vor dem j/n-Klick geaendert wurde
    diff_stat = ""
    diff_text = ""
    if offene:
        import subprocess as _sp
        basis: Path | None = None
        try:
            basis = (_PROJECTS_BASE / projekt).resolve()
            basis.relative_to(_PROJECTS_BASE.resolve())
        except (OSError, RuntimeError, ValueError):
            basis = None
        if basis is not None and basis.is_dir():
            try:
                diff_stat = _sp.run(
                    ["git", "diff", "--stat", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(basis), check=False,
                ).stdout[:5000]
                diff_text = _sp.run(
                    ["git", "diff", "HEAD"],
                    capture_output=True, text=True, timeout=15,
                    cwd=str(basis), check=False,
                ).stdout[:100_000]
            except (_sp.TimeoutExpired, OSError):
                pass

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
        "diff_stat": diff_stat,
        "diff": diff_text,
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


def aggregate_role_events(
    projekt: str, rolle: str, run_id: str | None = None
) -> dict[str, Any]:
    """Alle Events einer Rolle (explorer/scout/builder/reviewer/verify/reflection).

    Liefert kind + payload + ts, damit der Frontend-Drawer die tatsaechliche
    Arbeit der Rolle zeigt (z.B. Reviewer-Verdict, Builder-Patches).
    """
    _ROLE_PREFIXES: dict[str, tuple[str, ...]] = {
        "explorer": ("explorer_", "loop_explorer_"),
        "scout": ("scout_", "planner_scout_"),
        "planner": ("planner_", "loop_plan_"),
        "architect": ("planner_architect_", "architect_"),
        "builder": ("builder_", "loop_patch_", "loop_builder_"),
        "reviewer": ("reviewer_", "reviewer"),
        "verify": ("verify_", "loop_verify_"),
        "reflection": ("reflection_", "loop_reflection_"),
        "phase_review": ("reviewer_phase_", "loop_phase_review"),
        "llm": ("llm_call_", "llm_usage", "llm_timeout_"),
    }
    prefixe = _ROLE_PREFIXES.get(rolle, (rolle + "_",))
    events = _audit_events(run_id)
    treffer: list[dict[str, Any]] = []
    for ev in events:
        kind = str(ev.get("kind", ""))
        if any(kind.startswith(p) or kind == p.rstrip("_") for p in prefixe):
            payload = _payload_von(ev)
            ts = str(ev.get("ts", "") or ev.get("timestamp", ""))
            treffer.append({
                "kind": kind,
                "ts": ts,
                "payload": payload,
            })
    return {"rolle": rolle, "anzahl": len(treffer), "events": treffer}


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



