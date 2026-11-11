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
                "WHERE kind IN ('user', 'assistant') "
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
        elif kind == "job_turn":
            msgs.extend([
                {"role": "user", "content": payload.get("user_text", "")},
                {"role": "assistant", "content": payload.get("assistant_text", "")},
            ])
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
