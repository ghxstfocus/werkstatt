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


def signal_open(
    run_id: str,
    gate_id: str,
    prompt: str,
    optionen: str = "jna",
) -> None:
    """Schreibt ein gate_open-Event, damit die UI das Gate anzeigen kann."""
    EventStore().append(
        run_id=run_id,
        kind=KIND_OPEN,
        payload={
            "gate_id": gate_id,
            "prompt": prompt,
            "optionen": optionen,
        },
    )


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
    EventStore().append(
        run_id=run_id,
        kind="gate_expired",
        payload={"gate_id": gate_id, "timeout_s": timeout},
    )
    raise GateTimeout(
        f"Gate {gate_id} nach {timeout}s nicht beantwortet"
    )
