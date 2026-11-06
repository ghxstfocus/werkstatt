"""Task-/Step-/Log-API (OP-138 Phase 2c)."""
from __future__ import annotations

import datetime as _dt

from . import emit as _emit_m
from . import rich as _rich
from . import spinner as _spin
from . import tee as _tee_mod

TOTAL_PHASES = 5


def _timestamp() -> str:
    """HH:MM:SS fuer permanente Log-Zeilen."""
    return _dt.datetime.now().strftime("%H:%M:%S")


def footer(success: bool, tasks_total: int, tasks_ok: int) -> None:
    """Zeigt den Loop-Abschluss."""
    _emit_m._emit("")
    if _rich._use_rich:
        style = "green" if success else "red"
        text = "✓ LOOP ERFOLGREICH" if success else "✗ LOOP FEHLGESCHLAGEN"
        _rich._console.print(_rich._RichPanel(
            f"[bold {style}]{text}[/]\n"
            f"  Tasks: {tasks_ok}/{tasks_total}",
            border_style=style,
        ))
    else:
        _emit_m._emit(_rich._bold("═" * 60))
        if success:
            _emit_m._emit(_rich._green(_rich._bold("  ✓ LOOP ERFOLGREICH")))
        else:
            _emit_m._emit(_rich._red(_rich._bold("  ✗ LOOP FEHLGESCHLAGEN")))
        _emit_m._emit(f"  Tasks: {tasks_ok}/{tasks_total}")
        _emit_m._emit(_rich._bold("═" * 60))
    _emit_m._emit("")
    _emit_m._publish("summary", "", success=success, tasks_total=tasks_total, tasks_ok=tasks_ok)


def group_end() -> None:
    if _rich.IS_CI:
        print("::endgroup::")


def group_start(name: str) -> None:
    """Phasen-Header."""
    if _rich.IS_CI:
        print(f"::group::{name}")
    elif _rich._use_rich:
        _rich._console.rule(f"[bold cyan]{name}[/]")
    else:
        _emit_m._emit(f"--- {name} ---")


def header(title: str) -> None:
    """Zeigt den Loop-Header (einmal pro Lauf)."""
    _emit_m._emit("")
    if _rich._use_rich:
        _rich._console.print(_rich._RichPanel(
            f"[bold]Werkstatt Loop[/] — {title}",
            title="[cyan]Loop[/]",
            border_style="cyan",
        ))
    else:
        _emit_m._emit(_rich._bold("═" * 60))
        _emit_m._emit(_rich._bold(f"  WERKSTATT LOOP — {title}"))
        _emit_m._emit(_rich._bold("═" * 60))
    _emit_m._emit("")


def hook(name: str, ok: bool, reason: str = "") -> None:
    """Zeigt einen Hook-Aufruf."""
    marker = _rich._green("✓") if ok else _rich._yellow("!")
    extra = f" — {reason}" if reason and not ok else ""
    _emit_m._emit(f"           {marker} hook: {name}{extra}")


def log_line(
    label: str, detail: str = "",
    elapsed_s: float | None = None,
    ok: bool = True,
) -> None:
    """Permanente Zeile mit Zeitstempel. Ersetzt nicht, appends.

    Beispiel: [12:47:16] OK Explorer  . 3.1s . 8 files
    """
    ts = _timestamp()
    if _rich.IS_CI:
        status = "ok" if ok else "fail"
        _emit_m._emit_raw(f"::log::{ts} {status} {label} {detail}")
    else:
        _el = f" · {elapsed_s:.1f}s" if elapsed_s is not None else ""
        if _rich._use_rich:
            mark = "[green]OK[/]" if ok else "[red]X[/]"
            _rich._console.print(
                f"[dim]{ts}[/] {mark} [bold]{label}[/]{_el}"
                + (f" · [dim]{detail}[/]" if detail else "")
            )
        else:
            mark = "OK" if ok else "X"
            _emit_m._emit_raw(f"[{ts}] {mark} {label}{_el}" + (f" · {detail}" if detail else ""))
    _emit_m._publish("log_line", label + (f" · {detail}" if detail else ""))
    _status_tee = "OK" if ok else "X"
    _tee_mod._tee(
        f"[{ts}] {_status_tee} {label}"
        + (f" · {detail}" if detail else "")
        + (f" · {elapsed_s:.1f}s" if elapsed_s is not None else "")
    )


def patch(file: str, action: str = "create") -> None:
    """Zeigt einen angewendeten Patch."""
    icon = "＋" if action == "create" else "✎"
    _emit_m._emit(f"           {icon} {file}")


def status_header(label: str, detail: str = "") -> None:
    """Ueberschreibbare Status-Zeile oben (nur live)."""
    if not _rich.IS_LIVE:
        return
    try:
        _spin.spinner_update(label, detail)
    except Exception:
        pass


def step(
    phase_nr: int,
    name: str,
    detail: str = "",
    ok: bool = True,
    elapsed_s: float | None = None,
) -> None:
    """Zeigt einen Loop-Schritt."""
    marker = _rich._green("✓") if ok else _rich._red("✗")
    label = f"[{phase_nr}/{TOTAL_PHASES}]"
    name_padded = name.ljust(14)
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if detail:
        _emit_m._emit(f"  {_rich._dim(label)} {marker} {_rich._bold(name_padded)} {_rich._dim('...')} {detail}{timing}")
    else:
        _emit_m._emit(f"  {_rich._dim(label)} {marker} {_rich._bold(name_padded)}{timing}")


def summary(
    tasks_ok: int, tasks_failed: int,
    elapsed_s: float, task_details: list[dict] | None = None,
) -> None:
    """Zusammenfassung am Ende (permanent)."""
    ts = _timestamp()
    total = tasks_ok + tasks_failed
    _el = f"{elapsed_s:.1f}s"
    if _rich.IS_CI:
        print(f"::log::{ts} done {tasks_ok}/{total} tasks in {_el}")
        return
    if _rich._use_rich:
        _rich._console.print("")
        _rich._console.print(
            f"[dim]{ts}[/] [bold green]Done[/] · {_el} · "
            f"[green]{tasks_ok}[/]/{total} Tasks"
            + (f" · [red]{tasks_failed} failed[/]" if tasks_failed else "")
        )
        for t in (task_details or []):
            mark = "[green]OK[/]" if t.get("ok") else "[red]X[/]"
            name = t.get("name", "?")
            el = f" · {t.get('elapsed_s', 0):.1f}s" if t.get("elapsed_s") else ""
            _rich._console.print(f"  {mark} {name}{el}")
    else:
        print(f"[{ts}] Done · {_el} · {tasks_ok}/{total} Tasks" + (f" · {tasks_failed} failed" if tasks_failed else ""))


def task(nr: int, total: int, name: str) -> None:
    """Startet einen Task."""
    label = f"[{nr}/{total}]"
    if _rich.IS_LIVE and _rich._HAS_RICH:
        _spin.spinner_start(f"Task {nr}/{total}", name[:50])
    else:
        _emit_m._emit_raw(f"  {_rich._dim(label)} {_rich._cyan('→')} {name}")
    _emit_m._publish("task_started", f"Task {nr}/{total}: {name}", nr=nr, total=total, name=name)


def task_done(
    nr: int, total: int, name: str,
    elapsed_s: float | None = None,
    ok: bool = True, reason: str = "",
) -> None:
    """Permanente Zeile: Task fertig (ok oder failed)."""
    ts = _timestamp()
    _el = f" · {elapsed_s:.1f}s" if elapsed_s is not None else ""
    if _rich.IS_CI:
        status = "ok" if ok else "fail"
        print(f"::log::{ts} {status} Task {nr}/{total}: {name}{_el}")
        return
    mark_ok = "[green]OK[/]" if ok else "[red]X[/]"
    mark_plain = "OK" if ok else "X"
    suffix = f" [dim]({reason})[/]" if reason else ""
    if _rich._use_rich:
        _rich._console.print(
            f"[dim]{ts}[/] {mark_ok} [bold]Task {nr}/{total}[/]: {name}{_el}{suffix}"
        )
    else:
        print(f"[{ts}] {mark_plain} Task {nr}/{total}: {name}{_el}" + (f" ({reason})" if reason else ""))


def task_failed(nr: int, total: int, reason: str = "") -> None:
    label = f"[{nr}/{total}]"
    extra = f" — {reason}" if reason else ""
    if _rich.IS_LIVE and _rich._HAS_RICH:
        _spin.spinner_stop()
    _emit_m._emit_raw(f"  {_rich._dim(label)} {_rich._red('✗')} task failed{extra}")
    _emit_m._publish("task_done", f"Task {nr}/{total}: failed{extra}", nr=nr, total=total, ok=False, reason=reason)


def task_ok(nr: int, total: int, elapsed_s: float | None = None) -> None:
    label = f"[{nr}/{total}]"
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if _rich.IS_LIVE and _rich._HAS_RICH:
        _spin.spinner_stop()
    _emit_m._emit_raw(f"  {_rich._dim(label)} {_rich._green('✓')} task ok{timing}")
    _emit_m._publish("task_done", f"Task {nr}/{total}: ok{timing}", nr=nr, total=total, ok=True, elapsed_s=elapsed_s)


def task_started(nr: int, total: int, name: str) -> None:
    """Permanente Zeile: Task startet."""
    ts = _timestamp()
    if _rich.IS_CI:
        print(f"::log::{ts} start Task {nr}/{total}: {name}")
        return
    if _rich._use_rich:
        _rich._console.print(
            f"[dim]{ts}[/] [cyan]>[/] [bold]Task {nr}/{total}[/]: {name} [dim](running)[/]"
        )
    else:
        print(f"[{ts}] > Task {nr}/{total}: {name} (running)")
