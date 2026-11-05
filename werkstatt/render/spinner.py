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


def _with_spinner(label: str, fn):
    """M-455: Fuehrt fn aus, mit Spinner + Heartbeat alle 2s.

    Zeigt dem Nutzer, dass der Loop laeuft (nicht haengt).
    """
    import threading as _th
    import time as _time

    from .progress import _emit_progress, heartbeat
    from .tasks import log_line

    try:
        spinner_start(label)
    except Exception:  # noqa: BLE001, S110
        pass

    _start = _time.monotonic()
    _emit_progress(label, "start", "")
    _done = _th.Event()
    _result: list = [None]
    _exc: list = [None]

    def _worker():
        try:
            _result[0] = fn()
        except Exception as e:  # noqa: BLE001
            _exc[0] = e
        finally:
            _done.set()

    def _heartbeat_loop():
        _last = -1
        while not _done.is_set():
            _el = int(_time.monotonic() - _start)
            if _el // 2 > _last // 2:
                try:
                    heartbeat(label, _el)
                except Exception:  # noqa: BLE001, S110
                    pass
                _last = _el
            _done.wait(timeout=0.5)

    _t = _th.Thread(target=_worker, daemon=True)
    _hb = _th.Thread(target=_heartbeat_loop, daemon=True)
    _t.start()
    _hb.start()
    _t.join()
    _hb.join(timeout=1)

    try:
        spinner_stop()
    except Exception:  # noqa: BLE001, S110
        pass

    # M-456: permanente Log-Zeile.
    try:
        _elapsed = _time.monotonic() - _start
        log_line(label, elapsed_s=_elapsed, ok=(_exc[0] is None))
    except Exception:  # noqa: BLE001, S110
        pass

    _elapsed_total = _time.monotonic() - _start
    _emit_progress(
        label,
        "done" if _exc[0] is None else "failed",
        f"{_elapsed_total:.1f}s",
    )

    if _exc[0] is not None:
        raise _exc[0]
    return _result[0]
