"""OP-322: JSONL -> SQLite Projektor (rebuildbar, idempotent)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from werkstatt.audit import AUDIT_DIR_NAME, _werkstatt_home


class Projector:
    def __init__(self, db_pfad: Path | None = None) -> None:
        if db_pfad is None:
            db_pfad = _werkstatt_home() / ".werkstatt" / "events.db"
        self.db_pfad = Path(db_pfad)
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
                "event_id TEXT, "
                "run_id TEXT NOT NULL, "
                "kind TEXT NOT NULL, "
                "phase TEXT, "
                "status TEXT, "
                "payload TEXT NOT NULL, "
                "ts TEXT NOT NULL)"
            )
            # OP-323c: Schema-Migration. Aeltere EventStore-Init erzeugt
            # events ohne event_id. Hier ergaenzen, sonst scheitert INSERT.
            cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
            if "event_id" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN event_id TEXT")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_event_id "
                "ON events(event_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_run_seq "
                "ON events(run_id, seq)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS projection_state ("
                "key TEXT PRIMARY KEY, "
                "value TEXT NOT NULL)"
            )
            conn.commit()

    def _jsonl_files(self) -> list[Path]:
        d = _werkstatt_home() / AUDIT_DIR_NAME
        if not d.exists():
            return []
        out: list[Path] = []
        for pat in ("semantic-*.jsonl", "stream-*.jsonl", "agent-pipeline-*.jsonl"):
            out.extend(sorted(d.glob(pat)))
        return out

    def _read_events(
        self, von_audit_id: str | None = None
    ) -> list[tuple[dict[str, Any], str, int]]:
        alle: list[tuple[dict[str, Any], str, int]] = []
        found_start = von_audit_id is None
        for f in self._jsonl_files():
            with f.open(encoding="utf-8") as fh:
                for line_idx, line in enumerate(fh):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not found_start:
                        if d.get("audit_id") == von_audit_id:
                            found_start = True
                        continue
                    alle.append((d, f.name, line_idx))
        return alle

    def _count_jsonl(self) -> int:
        total = 0
        for f in self._jsonl_files():
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        total += 1
        return total

    def _insert(
        self,
        conn: sqlite3.Connection,
        ev: dict[str, Any],
        file_name: str = "?",
        line_num: int = 0,
    ) -> bool:
        run_id = ev.get("run_id") or ""
        kind = ev.get("kind") or "?"
        event_id = ev.get("event_id")
        if not event_id:
            aid = ev.get("audit_id") or ""
            event_id = hashlib.sha256(
                f"{run_id}|{aid}|{file_name}|{line_num}".encode()
            ).hexdigest()[:16]
        payload = {
            k: v
            for k, v in ev.items()
            if k not in {
                "seq", "event_id", "audit_id", "timestamp", "ts",
                "agent", "project", "kind", "run_id", "phase", "status",
            }
        }
        cur = conn.execute(
            "INSERT OR IGNORE INTO events "
            "(event_id, run_id, kind, phase, status, payload, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                run_id,
                kind,
                ev.get("phase"),
                ev.get("status"),
                json.dumps(payload, ensure_ascii=False),
                ev.get("timestamp") or ev.get("ts") or "",
            ),
        )
        return cur.rowcount > 0

    def _get_checkpoint(self, key: str) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT value FROM projection_state WHERE key=?", (key,)
            ).fetchone()
        return row[0] if row else None

    def _set_checkpoint(self, conn: sqlite3.Connection, key: str, val: str) -> None:
        conn.execute(
            "INSERT INTO projection_state(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, val),
        )

    def rebuild(self) -> dict[str, int]:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM events")
            conn.execute("DELETE FROM projection_state")
            conn.commit()
        return self.tail(von_anfang=True)

    def tail(self, von_anfang: bool = False) -> dict[str, int]:
        checkpoint = None if von_anfang else self._get_checkpoint("last_audit_id")
        events = self._read_events(von_audit_id=checkpoint)
        eingefuegt = 0
        uebersprungen = 0
        letzter = checkpoint
        with closing(self._connect()) as conn:
            for ev, fname, lnum in events:
                if self._insert(conn, ev, fname, lnum):
                    eingefuegt += 1
                else:
                    uebersprungen += 1
                aid = ev.get("audit_id")
                if aid:
                    letzter = aid
            if letzter and eingefuegt > 0:
                self._set_checkpoint(conn, "last_audit_id", letzter)
            conn.commit()
        return {"eingefuegt": eingefuegt, "uebersprungen": uebersprungen}

    def status(self) -> dict[str, int | str | None]:
        jsonl_events = self._count_jsonl()
        with closing(self._connect()) as conn:
            sqlite_rows = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return {
            "jsonl_events": jsonl_events,
            "sqlite_rows": sqlite_rows,
            "diff": jsonl_events - sqlite_rows,
            "last_checkpoint": self._get_checkpoint("last_audit_id"),
        }
