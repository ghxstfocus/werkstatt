"""Live-Spinner (nur RENDER_MODE=live, OP-138 Phase 2b)."""
from __future__ import annotations

import threading

from . import emit as _emit_m
from . import rich as _rich

_live: _rich._RichLive | None = None


_spinner_text = ""


_live_lock = threading.Lock()


def spinner_start(label: str, detail: str = "") -> None:
    """Startet einen Live-Spinner (nur RENDER_MODE=live).

    In ci/pretty: No-Op. In live: Live-Bereich mit Spinner + Text.
    """
    global _live, _spinner_text
    _emit_m._publish("spinner", label, state="start", label=label, detail=detail)
    if not _rich.IS_LIVE or not _rich._HAS_RICH:
        # Fallback: Heartbeat-Zeile
        _emit_m._emit(f"  · {label} ... {detail}" if detail else f"  · {label} ...")
        return

    with _live_lock:
        # M-377: idempotent — wenn schon aktiv, nur updaten.
        if _live is not None:
            _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
            _live.update(_rich._RichSpinner("dots", text=_spinner_text, style="cyan"))
            return
        _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
        _spinner = _rich._RichSpinner("dots", text=_spinner_text, style="cyan")
        _live = _rich._RichLive(_spinner, console=_rich._console, refresh_per_second=10, transient=True)
        try:
            _live.start()
        except Exception:  # noqa: BLE001
            # Falls rich trotzdem crasht: Live deaktivieren, kein Loop-Abbruch.
            _live = None


def spinner_update(label: str, detail: str = "") -> None:
    """Aktualisiert den Live-Spinner (nur RENDER_MODE=live)."""
    global _spinner_text
    _emit_m._publish("spinner", label, state="update", label=label, detail=detail)
    if not _rich.IS_LIVE or not _rich._HAS_RICH or _live is None:
        return
    with _live_lock:
        _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
        _live.update(_rich._RichSpinner("dots", text=_spinner_text, style="cyan"))


def spinner_stop(final_label: str = "") -> None:
    """Beendet den Live-Spinner (nur RENDER_MODE=live)."""
    global _live
    if not _rich.IS_LIVE or not _rich._HAS_RICH or _live is None:
        return
    with _live_lock:
        if _live is not None:
            try:
                _live.stop()
            except Exception:  # noqa: BLE001, S110
                # Live-Objekt ist bereits gestoppt oder ungueltig.
                pass
        _live = None
