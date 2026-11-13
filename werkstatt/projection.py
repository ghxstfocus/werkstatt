"""OP-322: JSONL -> SQLite Projektor (rebuildbar, idempotent)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
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
                "ts TEXT NOT NULL, "
                "project TEXT NOT NULL DEFAULT 'werkstatt')"
            )
            # OP-323c + OP-306c: Schema-Migration. Aeltere EventStore-Init
            # erzeugt events ohne event_id und ohne project. Beide Spalten
            # idempotent ergaenzen (Snapshot cols vor beiden Checks).
            cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
            if "event_id" not in cols:
                conn.execute("ALTER TABLE events ADD COLUMN event_id TEXT")
            if "project" not in cols:
                # OP-306c: Alle historischen Events stammen aus Werkstatt,
                # DEFAULT 'werkstatt' ist ehrlich (kein Backfill aus JSONL).
                conn.execute(
                    "ALTER TABLE events ADD COLUMN project TEXT NOT NULL "
                    "DEFAULT 'werkstatt'"
                )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_event_id "
                "ON events(event_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_run_seq "
                "ON events(run_id, seq)"
            )
            # OP-306c: Performance-Index fuer project-Filter (sonst
            # linear scan ueber 410k Zeilen in _letzter_run_id).
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_project_seq "
                "ON events(project, seq)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS projection_state ("
                "key TEXT PRIMARY KEY, "
                "value TEXT NOT NULL)"
            )
            conn.commit()

    def _jsonl_files(self) -> list[Path]:
        """Liefert alle fortlaufenden JSONL-Dateien (OP-306c-Fix).

        OP-323-Migrationsdateien (`*-migrated-*.jsonl`) sind statische
        DB-Dumps, keine fortlaufende Quelle — sie wuerden den Checkpoint
        auf einen Sentinel-Wert setzen und den naechsten tail() blockieren.
        """
        d = _werkstatt_home() / AUDIT_DIR_NAME
        if not d.exists():
            return []
        out: list[Path] = []
        for pat in ("semantic-*.jsonl", "stream-*.jsonl", "agent-pipeline-*.jsonl"):
            for f in sorted(d.glob(pat)):
                if "-migrated-" in f.name:
                    continue
                out.append(f)
        return out

    def _read_events(
        self, von_audit_id: str | None = None
    ) -> list[tuple[dict[str, Any], str, int]]:
        """Liest Events ab `von_audit_id` (exklusive) aus allen JSONL-Dateien.

        OP-306c-Fix: Fail-loud bei unbekanntem Checkpoint. Vorher: stumm
        leere Liste zurueckgegeben -> tail() sah 0 neue Events, Checkpoint
        blieb haengen, Projector stand fuer immer (Deadlock).

        Live-Bug 2026-11-08: Checkpoint `MIGRATED-SEM-352017` (aus
        Migration) stand in der alphabetisch letzten `migrated-*.jsonl`
        Zeile 33/33 — alle nachfolgenden Events wurden verworfen.
        """
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
        if not found_start:
            raise ValueError(
                f"Checkpoint {von_audit_id!r} nicht in JSONL gefunden. "
                f"Reset in projection_state noetig "
                f"(UPDATE projection_state SET value='<letzter_echter_audit_id>' "
                f"WHERE key='last_audit_id')."
            )
        return alle

    @staticmethod
    def _event_id(
        event: dict[str, Any], file_name: str, line_num: int,
    ) -> str:
        event_id = event.get("event_id")
        if event_id:
            return str(event_id)
        run_id = event.get("run_id") or ""
        audit_id = event.get("audit_id") or ""
        return hashlib.sha256(
            f"{run_id}|{audit_id}|{file_name}|{line_num}".encode()
        ).hexdigest()[:16]

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _jsonl_inventory(self) -> dict[str, Any]:
        """Return the active JSONL event-ID basis and its time coverage.

        Migration dumps are excluded by ``_jsonl_files``. IDs are unique and
        the first occurrence wins, matching SQLite's ``INSERT OR IGNORE``
        replay semantics.
        """
        event_times: dict[str, datetime | None] = {}
        malformed = 0
        for f in self._jsonl_files():
            with f.open(encoding="utf-8") as fh:
                for line_num, line in enumerate(fh):
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        malformed += 1
                        continue
                    if not isinstance(event, dict):
                        malformed += 1
                        continue
                    event_id = self._event_id(event, f.name, line_num)
                    timestamp = self._parse_timestamp(
                        event.get("timestamp") or event.get("ts")
                    )
                    event_times.setdefault(event_id, timestamp)

        timestamps = [value for value in event_times.values() if value is not None]
        first_event_id = next(iter(event_times), None)
        first_timestamp = event_times.get(first_event_id) if first_event_id else None
        return {
            "event_ids": set(event_times),
            "malformed_jsonl_lines": malformed,
            "untimestamped_events": sum(
                value is None for value in event_times.values()
            ),
            "anchor": {
                "event_id": first_event_id,
                "timestamp": self._format_timestamp(first_timestamp),
            },
            "period": {
                "from": self._format_timestamp(min(timestamps)) if timestamps else None,
                "to": self._format_timestamp(max(timestamps)) if timestamps else None,
            },
        }

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")

    def _insert(
        self,
        conn: sqlite3.Connection,
        ev: dict[str, Any],
        file_name: str = "?",
        line_num: int = 0,
    ) -> bool:
        run_id = ev.get("run_id") or ""
        kind = ev.get("kind") or "?"
        event_id = self._event_id(ev, file_name, line_num)
        # OP-306c: project bekommt eigene Spalte (single source of
        # truth), wird deshalb bewusst aus payload entfernt. Doppel-
        # Speicherung waere Drift-Risiko.
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
            "(event_id, run_id, kind, phase, status, payload, ts, project) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                run_id,
                kind,
                ev.get("phase"),
                ev.get("status"),
                json.dumps(payload, ensure_ascii=False),
                ev.get("timestamp") or ev.get("ts") or "",
                ev.get("project") or "werkstatt",
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
            if letzter and events:
                self._set_checkpoint(conn, "last_audit_id", letzter)
            conn.commit()
        return {"eingefuegt": eingefuegt, "uebersprungen": uebersprungen}

    def status(self) -> dict[str, Any]:
        inventory = self._jsonl_inventory()
        source_ids: set[str] = inventory["event_ids"]
        with closing(self._connect()) as conn:
            sqlite_rows_total = int(
                conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            )
            sqlite_ids = {
                str(row[0])
                for row in conn.execute(
                    "SELECT event_id FROM events WHERE event_id IS NOT NULL"
                )
            }
        sqlite_rows = len(source_ids & sqlite_ids)
        jsonl_events = len(source_ids)
        diff = jsonl_events - sqlite_rows
        return {
            "jsonl_events": jsonl_events,
            "sqlite_rows": sqlite_rows,
            "sqlite_rows_total": sqlite_rows_total,
            "sqlite_rows_outside_basis": sqlite_rows_total - sqlite_rows,
            "diff": diff,
            "last_checkpoint": self._get_checkpoint("last_audit_id"),
            "scope": "global",
            "comparison_basis": "active_jsonl_event_ids",
            "comparison_anchor": inventory["anchor"],
            "comparison_period": inventory["period"],
            "untimestamped_jsonl_events": inventory["untimestamped_events"],
            "malformed_jsonl_lines": inventory["malformed_jsonl_lines"],
            "comparable": (
                inventory["malformed_jsonl_lines"] == 0
                and inventory["untimestamped_events"] == 0
            ),
        }
