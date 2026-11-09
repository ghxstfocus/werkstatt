"""HTTP-Bruecke fuer Loop-Gates (ADR-0007, OP-202).

Der Loop laeuft als Subprocess (werkstatt/web/app.py:project_start).
Der Event-Store (SQLite/WAL) ist der Cross-Prozess-Kanal, analog zu
terminal_proxy.py. Dieses Modul bietet:

  signal_open()  -- schreibt gate_open-Event (UI sieht das Gate)
  wait()         -- pollt auf gate_answered, fail-closed via GateTimeout

Poll-Intervall 0.2s: Latenz menschlicher Antworten ist Sekunden bis
Minuten, daher irrelevant. SQLite-WAL erlaubt paralleles Lesen waehrend
des Schreibens.
"""
from __future__ import annotations

import time
import uuid
from typing import Final

from werkstatt.event_store import EventStore

__all__ = ["GateTimeout", "make_gate_id", "signal_open", "wait"]

KIND_OPEN: Final = "gate_open"
KIND_ANSWERED: Final = "gate_answered"
DEFAULT_TIMEOUT: Final = 300.0
DEFAULT_POLL: Final = 0.2


class GateTimeout(Exception):
    """Ein Gate wurde nicht rechtzeitig beantwortet (fail-closed)."""


def make_gate_id(kind: str) -> str:
    """Erzeugt eine prozessweit eindeutige Gate-ID (kind + random)."""
    return f"{kind}-{uuid.uuid4().hex[:8]}"


def _flush_projection() -> None:
    """OP-323c: JSONL -> SQLite sofort, damit EventStore.query() das
    Gate-Event sieht. Gates sind kritisch, kein Batch-Wait."""
    try:
        from werkstatt.projection import Projector
        Projector().tail()
    except Exception as exc:
        import sys as _sys
        _sys.stderr.write(f"gate_bridge._flush_projection: {exc!r}\n")


def signal_open(
    run_id: str,
    gate_id: str,
    prompt: str,
    optionen: str = "jna",
    typ: str = "jna",
) -> None:
    """Schreibt ein gate_open-Event, damit die UI das Gate anzeigen kann.

    ``typ`` (OP-381c): "jna" (Buttons) oder "freitext" (Textarea).
    Default "jna" — rueckwaertskompatibel fuer alle bestehenden Aufrufer.
    """
    # OP-323: audit() statt EventStore().append (JSONL autoritativ)
    from pathlib import Path as _Path

    from werkstatt.audit import audit
    audit("gate_open", {
        "gate_id": gate_id,
        "prompt": prompt,
        "optionen": optionen,
        "typ": typ,
        "run_id": run_id,
    }, _Path("."), "werkstatt")
    _flush_projection()


def _finde_antwort(
    store: EventStore, run_id: str, gate_id: str
) -> str | None:
    """Erste gate_answered-Antwort fuer gate_id, oder None."""
    for ev in store.query(run_id, kind=KIND_ANSWERED):
        payload = ev.get("payload") or {}
        if payload.get("gate_id") == gate_id:
            antwort = payload.get("answer")
            if isinstance(antwort, str) and antwort:
                return antwort
    return None


def wait(
    run_id: str,
    gate_id: str,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = DEFAULT_POLL,
) -> str:
    """Blockiert bis POST /api/runs/{run_id}/gate das Gate beantwortet.

    Fail-closed: bei Timeout wird GateTimeout geworfen.
    """
    store = EventStore()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        antwort = _finde_antwort(store, run_id, gate_id)
        if antwort is not None:
            return antwort
        time.sleep(poll_interval)
    # OP-304: Timeout sichtbar machen — sonst bleibt gate_open ewig stehen
    # OP-323: audit() statt EventStore().append
    from pathlib import Path as _Path2

    from werkstatt.audit import audit
    audit("gate_expired", {
        "gate_id": gate_id,
        "timeout_s": timeout,
        "run_id": run_id,
    }, _Path2("."), "werkstatt")
    _flush_projection()
    raise GateTimeout(
        f"Gate {gate_id} nach {timeout}s nicht beantwortet"
    )


def expire_for_run(run_id: str, grund: str = "loop_ended") -> int:
    """Schliesst alle offenen Gates eines Runs atomar.

    Wird vom Loop-Lifecycle (loop.main() -> finally) gerufen:
    sobald der Loop-Prozess endet, sind alle seine Gates abgebrochen.
    Kein PID-Check, kein Heartbeat, kein Timeout — der Lifecycle
    ist der Vertrag.
    """
    if not run_id:
        return 0
    es = EventStore()
    opens = es.query(run_id, kind="gate_open")
    if not opens:
        return 0
    beantwortet = {
        (e.get("payload") or {}).get("gate_id")
        for e in es.query(run_id, kind="gate_answered")
    }
    bereits_expired = {
        (e.get("payload") or {}).get("gate_id")
        for e in es.query(run_id, kind="gate_expired")
    }
    n = 0
    for ev in opens:
        gid = (ev.get("payload") or {}).get("gate_id")
        if not gid or gid in beantwortet or gid in bereits_expired:
            continue
        # OP-323c: audit() statt EventStore().append
        from pathlib import Path as _Path3

        from werkstatt.audit import audit
        audit("gate_expired", {
            "gate_id": gid,
            "grund": grund,
            "run_id": run_id,
        }, _Path3("."), "werkstatt")
        n += 1
    return n

