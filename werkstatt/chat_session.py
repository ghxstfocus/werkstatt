"""Chat-Session-Store (OP-230, SQLite, pro Projekt).

Append-only Event-Store fuer Chat-Historie. Die LLM-Historie wird
aus Events rekonstruiert (derive_messages), damit Sessions fork-faehig
sind: ein Fork ist eine neue Session, die die Events bis zu einem
bestimmten seq kopiert.

Abgrenzung zu werkstatt/event_store.py:
  event_store.py   -- Loop-Audit, global, ein events.db
  chat_session.py  -- Chat-Historie, pro Projekt eine DB
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from werkstatt.paths import werkstatt_home

__all__ = [
    "ChatSession",
    "derive_messages",
    "fork",
    "list_session_summaries",
    "list_sessions",
]


def _db_pfad(project: str) -> Path:
    """Projekt-DB-Pfad (SOLL §5: SQLite pro Projekt)."""
    return werkstatt_home() / ".werkstatt" / project / "chat-sessions.db"


class ChatSession:
    """Append-only Chat-Session auf SQLite (pro Projekt)."""

    def __init__(
        self,
        project: str,
        session_id: str,
        db_pfad: Path | None = None,
    ) -> None:
        self.project = project
        self.session_id = session_id
        self.db_pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
        self.db_pfad.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_pfad, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
                "session_id TEXT NOT NULL, "
                "ts TEXT NOT NULL, "
                "kind TEXT NOT NULL, "
                "payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_seq "
                "ON events(session_id, seq)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chat_snapshots ("
                "target_session_id TEXT PRIMARY KEY,"
                "parent_session_id TEXT NOT NULL,source_seq INTEGER NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chat_job_turns ("
                "session_id TEXT NOT NULL,job_id TEXT NOT NULL,"
                "PRIMARY KEY(session_id,job_id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS idempotent_events ("
                "session_id TEXT NOT NULL,event_key TEXT NOT NULL,seq INTEGER NOT NULL,"
                "PRIMARY KEY(session_id,event_key))"
            )
            conn.commit()

    def append(
        self, kind: str, payload: dict[str, Any] | None = None
    ) -> int:
        """Fuegt ein Event an und liefert die vergebene seq."""
        ts = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO events (session_id, ts, kind, payload) "
                "VALUES (?, ?, ?, ?)",
                (self.session_id, ts, kind, payload_json),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def append_once(
        self, event_key: str, kind: str, payload: dict[str, Any] | None = None,
    ) -> int:
        """Append an event once per session, even across concurrent retries."""
        if not event_key or len(event_key) > 512:
            raise ValueError("event_key must contain 1-512 characters")
        ts = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT seq FROM idempotent_events "
                "WHERE session_id=? AND event_key=?",
                (self.session_id, event_key),
            ).fetchone()
            if row is not None:
                conn.commit()
                return int(row[0])
            cur = conn.execute(
                "INSERT INTO events (session_id, ts, kind, payload) "
                "VALUES (?, ?, ?, ?)",
                (self.session_id, ts, kind, payload_json),
            )
            seq = int(cur.lastrowid or 0)
            conn.execute(
                "INSERT INTO idempotent_events(session_id,event_key,seq) "
                "VALUES(?,?,?)",
                (self.session_id, event_key, seq),
            )
            conn.commit()
            return seq

    def resolve_loop_action(
        self,
        proposal_id: str,
        decision: str,
    ) -> tuple[dict[str, Any], str, dict[str, Any] | None] | None:
        """Atomically decide a session-bound loop-action proposal once."""
        if decision not in {"confirm", "reject"}:
            raise ValueError("decision must be confirm or reject")
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT kind, payload FROM events WHERE session_id=? "
                "ORDER BY seq ASC",
                (self.session_id,),
            ).fetchall()
            proposal: dict[str, Any] | None = None
            status = "pending"
            result: dict[str, Any] | None = None
            for kind, raw_payload in rows:
                try:
                    payload = json.loads(raw_payload)
                except (json.JSONDecodeError, TypeError):
                    continue
                if payload.get("proposal_id") != proposal_id:
                    continue
                if kind == "loop_action_proposed":
                    proposal = payload
                elif kind == "loop_action_confirmed":
                    status = "confirmed"
                elif kind == "loop_action_rejected":
                    status = "rejected"
                    result = payload
                elif kind == "loop_action_expired":
                    status = "expired"
                    result = payload
                elif kind == "loop_action_completed":
                    status = "completed"
                    result = payload.get("result") or {}
                elif kind == "loop_action_failed":
                    status = "failed"
                    result = payload
                elif kind == "loop_action_not_started":
                    status = "not_started"
                    result = payload.get("result") or payload
                elif kind == "loop_action_queued":
                    status = "queued"
                    result = payload.get("result") or payload
            if proposal is None:
                conn.commit()
                return None
            if status != "pending":
                conn.commit()
                return proposal, status, result
            expires_at = proposal.get("expires_at")
            if isinstance(expires_at, str):
                try:
                    expired = datetime.fromisoformat(expires_at) <= datetime.now(UTC)
                except ValueError:
                    expired = True
            else:
                expired = True
            if expired:
                status = "expired"
                payload = {"proposal_id": proposal_id, "status": status}
            elif decision == "reject":
                status = "rejected"
                payload = {"proposal_id": proposal_id, "status": status}
            else:
                status = "confirmed"
                payload = {
                    "proposal_id": proposal_id,
                    "status": status,
                    "action": proposal.get("action"),
                }
            conn.execute(
                "INSERT INTO events (session_id, ts, kind, payload) "
                "VALUES (?, ?, ?, ?)",
                (
                    self.session_id,
                    datetime.now(UTC).isoformat(),
                    f"loop_action_{status}",
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            conn.commit()
            return proposal, "claimed" if status == "confirmed" else status, result

    def load(self) -> list[dict[str, Any]]:
        """Liefert alle Events der Session, aufsteigend nach seq."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT seq, session_id, ts, kind, payload "
                "FROM events WHERE session_id = ? ORDER BY seq ASC",
                (self.session_id,),
            ).fetchall()
        ergebnis: list[dict[str, Any]] = []
        for seq, sid, ts, kind, payload in rows:
            try:
                payload_obj = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                payload_obj = {}
            ergebnis.append({
                "seq": seq,
                "session_id": sid,
                "ts": ts,
                "kind": kind,
                "payload": payload_obj,
            })
        return ergebnis

    def read_history_page(
        self, *, before_seq: int | None = None, limit: int = 10,
    ) -> dict[str, Any]:
        """Read a bounded page of prior user-visible turns by sequence."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        if before_seq is not None and (
            isinstance(before_seq, bool)
            or not isinstance(before_seq, int)
            or before_seq < 1
        ):
            raise ValueError("before_seq must be a positive integer")
        with closing(self._connect()) as conn:
            if before_seq is None:
                rows = conn.execute(
                    "SELECT seq,ts,kind,payload FROM events "
                    "WHERE session_id=? AND kind IN ('user','assistant','job_turn','job_queued','job_status') "
                    "ORDER BY seq DESC LIMIT ?",
                    (self.session_id, limit + 1),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT seq,ts,kind,payload FROM events "
                    "WHERE session_id=? AND seq<? "
                    "AND kind IN ('user','assistant','job_turn','job_queued','job_status') "
                    "ORDER BY seq DESC LIMIT ?",
                    (self.session_id, before_seq, limit + 1),
                ).fetchall()
        has_more = len(rows) > limit
        selected = rows[:limit]
        events: list[dict[str, Any]] = []
        for seq, ts, kind, raw_payload in selected:
            try:
                payload = json.loads(raw_payload)
            except (json.JSONDecodeError, TypeError):
                payload = {}
            events.append({
                "seq": int(seq),
                "ts": str(ts),
                "kind": str(kind),
                "payload": payload if isinstance(payload, dict) else {},
            })
        return {
            "events": events,
            "has_more": has_more,
            "next_before_seq": int(selected[-1][0]) if has_more else None,
        }

    def read_history_event(self, seq: int) -> dict[str, Any] | None:
        """Read one event by sequence, scoped to this session."""
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
            raise ValueError("seq must be a positive integer")
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT seq,ts,kind,payload FROM events "
                "WHERE session_id=? AND seq=?",
                (self.session_id, seq),
            ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row[3])
        except (json.JSONDecodeError, TypeError):
            payload = {}
        return {
            "seq": int(row[0]),
            "ts": str(row[1]),
            "kind": str(row[2]),
            "payload": payload if isinstance(payload, dict) else {},
        }

    def max_seq(self) -> int:
        """Hoechste gespeicherte Event-Sequenz dieser Session."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq),0) FROM events WHERE session_id=?",
                (self.session_id,),
            ).fetchone()
        return int(row[0]) if row else 0

    def snapshot_to(
        self, target_session_id: str, *, at_seq: int | None = None,
    ) -> ChatSession:
        """Kopiert einen unveraenderlichen Kontext-Snapshot idempotent."""
        if target_session_id == self.session_id:
            raise ValueError("Snapshot-Ziel muss eine eigene Session sein")
        target = ChatSession(self.project, target_session_id, db_pfad=self.db_pfad)
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT 1 FROM chat_snapshots WHERE target_session_id=?",
                (target_session_id,),
            ).fetchone()
            if existing is None:
                cutoff = self.max_seq() if at_seq is None else max(0, at_seq)
                rows = conn.execute(
                    "SELECT ts,kind,payload FROM events "
                    "WHERE session_id=? AND seq<=? ORDER BY seq",
                    (self.session_id, cutoff),
                ).fetchall()
                for ts, kind, payload in rows:
                    conn.execute(
                        "INSERT INTO events(session_id,ts,kind,payload) "
                        "VALUES(?,?,?,?)",
                        (target_session_id, ts, kind, payload),
                    )
                conn.execute(
                    "INSERT INTO chat_snapshots("
                    "target_session_id,parent_session_id,source_seq) "
                    "VALUES(?,?,?)",
                    (target_session_id, self.session_id, cutoff),
                )
            conn.commit()
        return target

    def delete_snapshot(self, target_session_id: str) -> bool:
        """Entfernt nur einen von dieser Session verwalteten Job-Branch."""
        if target_session_id == self.session_id:
            raise ValueError("Eltern-Session darf nicht als Snapshot geloescht werden")
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            snapshot = conn.execute(
                "SELECT 1 FROM chat_snapshots WHERE target_session_id=? "
                "AND parent_session_id=?",
                (target_session_id, self.session_id),
            ).fetchone()
            if snapshot is None:
                conn.commit()
                return False
            conn.execute("DELETE FROM events WHERE session_id=?", (target_session_id,))
            conn.execute(
                "DELETE FROM chat_job_turns WHERE session_id=?",
                (target_session_id,),
            )
            conn.execute(
                "DELETE FROM chat_snapshots WHERE target_session_id=?",
                (target_session_id,),
            )
            conn.commit()
        return True

    def append_job_turn(
        self, job_id: str, user_text: str, assistant_text: str,
    ) -> bool:
        """Fuegt ein erfolgreiches Job-Turn-Paar genau einmal zur Session hinzu."""
        ts = datetime.now(UTC).isoformat()
        payload = json.dumps(
            {"job_id": job_id, "user_text": user_text,
             "assistant_text": assistant_text},
            ensure_ascii=False,
        )
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            inserted = conn.execute(
                "INSERT OR IGNORE INTO chat_job_turns(session_id,job_id) "
                "VALUES(?,?)",
                (self.session_id, job_id),
            )
            if inserted.rowcount:
                conn.execute(
                    "INSERT INTO events(session_id,ts,kind,payload) "
                    "VALUES(?,?,?,?)",
                    (self.session_id, ts, "job_turn", payload),
                )
            conn.commit()
        return bool(inserted.rowcount)

    def append_job_prompt(self, job_id: str, user_text: str) -> int:
        """Persist a submitted background-chat prompt before dispatch."""
        if not job_id or len(job_id) > 128:
            raise ValueError("job_id must contain 1-128 characters")
        event_key = f"chat-job-prompt:{job_id}"
        ts = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT seq FROM idempotent_events "
                "WHERE session_id=? AND event_key=?",
                (self.session_id, event_key),
            ).fetchone()
            if existing is not None:
                row = conn.execute(
                    "SELECT payload FROM events WHERE session_id=? AND seq=?",
                    (self.session_id, int(existing[0])),
                ).fetchone()
                payload = json.loads(row[0]) if row is not None else {}
                context_seq = payload.get("context_seq")
                conn.commit()
                if isinstance(context_seq, int) and not isinstance(context_seq, bool):
                    return context_seq
                raise RuntimeError("persisted job prompt lacks context_seq")
            row = conn.execute(
                "SELECT COALESCE(MAX(seq),0) FROM events WHERE session_id=?",
                (self.session_id,),
            ).fetchone()
            context_seq = int(row[0]) if row else 0
            payload = json.dumps(
                {
                    "job_id": job_id,
                    "user_text": user_text,
                    "context_seq": context_seq,
                },
                ensure_ascii=False,
            )
            cursor = conn.execute(
                "INSERT INTO events(session_id,ts,kind,payload) "
                "VALUES(?,?,?,?)",
                (self.session_id, ts, "job_queued", payload),
            )
            seq = int(cursor.lastrowid or 0)
            conn.execute(
                "INSERT INTO idempotent_events(session_id,event_key,seq) "
                "VALUES(?,?,?)",
                (self.session_id, event_key, seq),
            )
            conn.commit()
            return context_seq

    def append_job_status(self, job_id: str, status: str) -> int:
        """Persist a terminal no-answer status once for history/reconnect."""
        if not job_id or len(job_id) > 128:
            raise ValueError("job_id must contain 1-128 characters")
        if status not in {"failed", "cancelled"}:
            raise ValueError("status must be failed or cancelled")
        return self.append_once(
            f"chat-job-status:{job_id}",
            "job_status",
            {"job_id": job_id, "status": status},
        )

    def get_job_turn(self, job_id: str) -> dict[str, str] | None:
        """Return an already-persisted assistant job turn by its stable ID."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT payload FROM events WHERE session_id=? "
                "AND kind='job_turn' ORDER BY seq DESC",
                (self.session_id,),
            ).fetchall()
        for (raw_payload,) in row:
            try:
                payload = json.loads(raw_payload)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict) or payload.get("job_id") != job_id:
                continue
            user_text = payload.get("user_text")
            assistant_text = payload.get("assistant_text")
            if isinstance(user_text, str) and isinstance(assistant_text, str):
                return {
                    "user_text": user_text,
                    "assistant_text": assistant_text,
                }
        return None


def list_sessions(
    project: str,
    db_pfad: Path | None = None,
    *,
    mit_inhalt: bool = False,
) -> list[str]:
    """Alle Session-IDs im Projekt, sortiert.

    mit_inhalt=True: nur Sessions mit mindestens einem user-Event
    (blendet leere session_start-Sessions aus, z.B. Reload-Artefakte).
    """
    pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
    if not pfad.exists():
        return []
    with closing(sqlite3.connect(pfad)) as conn:
        if mit_inhalt:
            rows = conn.execute(
                "SELECT DISTINCT session_id FROM events "
                "WHERE kind IN ('user', 'assistant', 'job_queued') "
                "AND session_id NOT IN ("
                "SELECT target_session_id FROM chat_snapshots) "
                "ORDER BY session_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT session_id FROM events "
                "WHERE session_id NOT IN ("
                "SELECT target_session_id FROM chat_snapshots) "
                "ORDER BY session_id"
            ).fetchall()
    return [str(r[0]) for r in rows]


def list_session_summaries(
    project: str,
    db_pfad: Path | None = None,
    *,
    limit: int = 50,
) -> list[dict[str, str]]:
    """Liefert die juengsten Gespraeche mit menschenlesbarem Titel."""
    pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
    if not pfad.exists() or limit < 1:
        return []
    with closing(sqlite3.connect(pfad)) as conn:
        rows = conn.execute(
            "SELECT session_id, MAX(seq), MAX(ts) FROM events "
            "WHERE kind IN ('user', 'assistant', 'job_turn', 'job_queued') "
            "AND session_id NOT IN ("
            "SELECT target_session_id FROM chat_snapshots) "
            "GROUP BY session_id ORDER BY MAX(seq) DESC LIMIT ?",
            (min(limit, 100),),
        ).fetchall()
        summaries: list[dict[str, str]] = []
        for session_id, _last_seq, updated_at in rows:
            first = conn.execute(
                "SELECT kind, payload FROM events WHERE session_id=? "
                "AND kind IN ('user', 'job_turn', 'job_queued') ORDER BY seq ASC LIMIT 1",
                (session_id,),
            ).fetchone()
            payload: dict[str, Any] = {}
            if first:
                try:
                    parsed = json.loads(first[1]) if first[1] else {}
                    if isinstance(parsed, dict):
                        payload = parsed
                except json.JSONDecodeError:
                    pass
            title = payload.get("text") or payload.get("user_text") or ""
            title = " ".join(str(title).split())[:96] or "Projektgespraech"
            summaries.append({
                "session_id": str(session_id),
                "title": title,
                "updated_at": str(updated_at or ""),
            })
    return summaries


def fork(
    project: str,
    parent_session_id: str,
    at_seq: int | None = None,
    db_pfad: Path | None = None,
) -> str:
    """Forkt eine Session in eine neue session_id und liefert diese.

    Kopiert Events [1..at_seq] (oder alle, wenn at_seq=None) aus der
    Parent-Session in eine neue Session. Parent bleibt unveraendert.
    """
    pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
    parent = ChatSession(project, parent_session_id, db_pfad=pfad)
    alte = parent.load()
    if at_seq is not None:
        alte = [e for e in alte if e["seq"] <= at_seq]
    neue_id = uuid.uuid4().hex
    neu = ChatSession(project, neue_id, db_pfad=pfad)
    for ev in alte:
        neu.append(ev["kind"], ev["payload"])
    return neue_id


def derive_messages(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rekonstruiert LLM-Historie (OpenAI-Format) aus Events.

    Mapping:
      user        -> {"role": "user",      "content": text}
      assistant   -> {"role": "assistant", "content": text}
      tool_call   -> {"role": "assistant", "tool_calls": ...}
      tool_result -> {"role": "tool",      "content": ...}
    Unbekannte kinds werden ignoriert.
    """
    msgs: list[dict[str, Any]] = []
    queued_jobs = {
        str((event.get("payload") or {}).get("job_id"))
        for event in events
        if event.get("kind") == "job_queued"
        and isinstance((event.get("payload") or {}).get("job_id"), str)
    }
    completed_jobs = {
        str((event.get("payload") or {}).get("job_id")):
            (event.get("payload") or {}).get("assistant_text", "")
        for event in events
        if event.get("kind") == "job_turn"
        and isinstance((event.get("payload") or {}).get("job_id"), str)
    }
    terminal_jobs = {
        str((event.get("payload") or {}).get("job_id")):
            (event.get("payload") or {}).get("status")
        for event in events
        if event.get("kind") == "job_status"
        and isinstance((event.get("payload") or {}).get("job_id"), str)
    }
    for ev in events:
        kind = ev.get("kind")
        payload = ev.get("payload") or {}
        if kind == "user":
            msgs.append({
                "role": "user",
                "content": payload.get("text", ""),
            })
        elif kind == "assistant":
            msgs.append({
                "role": "assistant",
                "content": payload.get("text", ""),
            })
        elif kind == "job_queued":
            job_id = str(payload.get("job_id") or "")
            user_text = payload.get("user_text")
            if isinstance(user_text, str):
                msgs.append({"role": "user", "content": user_text})
                if job_id in completed_jobs:
                    msgs.append({
                        "role": "assistant",
                        "content": completed_jobs[job_id],
                    })
                else:
                    status = terminal_jobs.get(job_id)
                    detail = (
                        "Die vorherige Chat-Anfrage ist fehlgeschlagen; "
                        "es liegt keine Antwort vor."
                        if status == "failed" else
                        "Die vorherige Chat-Anfrage wurde abgebrochen; "
                        "es liegt keine Antwort vor."
                        if status == "cancelled" else
                        "Die vorherige Chat-Anfrage wird noch bearbeitet; "
                        "ihre Antwort liegt noch nicht vor."
                    )
                    msgs.append({"role": "assistant", "content": detail})
        elif kind == "job_turn":
            job_id = str(payload.get("job_id") or "")
            if job_id not in queued_jobs:
                msgs.extend([
                    {"role": "user", "content": payload.get("user_text", "")},
                    {"role": "assistant", "content": payload.get("assistant_text", "")},
                ])
        elif kind == "job_status":
            continue
        elif kind == "tool_call":
            msgs.append({
                "role": "assistant",
                "tool_calls": payload.get("tool_calls", []),
            })
        elif kind == "tool_result":
            msgs.append({
                "role": "tool",
                "content": payload.get("content", ""),
            })
    return msgs
