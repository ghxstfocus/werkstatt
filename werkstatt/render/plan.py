"""Panel-/Plan-Rendering (OP-138 Phase 2c)."""
from __future__ import annotations

from . import emit as _emit_m
from . import rich as _rich


def _emit_wrapped(text: str, width: int = 88, indent: str = "       ") -> None:
    """Bugfix 2026-11-03: Text auf width umbrechen, jede Zeile indent."""
    import textwrap as _tw
    if not text:
        return
    for line in _tw.wrap(text, width=width):
        _emit_m._emit(f"{indent}{line}")


def _render_plan_plain(phasen, tasks, tests, akzeptanzkriterien) -> None:
    _emit_m._emit("")
    _emit_m._emit("=" * 62)
    _emit_m._emit(f"  PLAN — {len(phasen)} Phasen, {len(tasks)} Tasks")
    _emit_m._emit("=" * 62)
    for _p in phasen:
        _emit_m._emit(f"Phase {_p.get('id', '?')}: {_p.get('titel', '')}")
        for _t in tasks:
            if isinstance(_t, dict) and _t.get("phase_id") == _p.get("id"):
                _files = ", ".join(_t.get("task_files", [])) or "(keine)"
                _emit_m._emit(f"  {_t.get('id')} [{_t.get('action', '?')}] {_t.get('name', '')[:60]}")
                _emit_m._emit(f"       Zieldatei: {_files}")
                _desc = (_t.get("description") or "").strip().replace("\n", " ")
                if _desc:
                    _emit_wrapped(_desc)
        _emit_m._emit("")
    # M-410b: Tasks ohne phase_id (flacher Plan, z.B. Architect)
    _ohne_phase = [
        _t for _t in tasks
        if isinstance(_t, dict) and not _t.get("phase_id")
    ]
    if _ohne_phase:
        _emit_m._emit("")
        for _t in _ohne_phase:
            _files = ", ".join(_t.get("task_files", [])) or "(keine)"
            _emit_m._emit(f"  {_t.get('id')} [{_t.get('action', '?')}] {_t.get('name', '')[:60]}")
            _emit_m._emit(f"       Zieldatei: {_files}")
            _desc = (_t.get("description") or "").strip().replace("\n", " ")
            if _desc:
                _emit_wrapped(_desc)

    if tests:
        _emit_m._emit(f"Tests ({len(tests)}):")
        for _t in tests:
            _emit_m._emit(f"  - {_t}")
    if akzeptanzkriterien:
        _emit_m._emit(f"Akzeptanzkriterien ({len(akzeptanzkriterien)}):")
        for _a in akzeptanzkriterien:
            _emit_m._emit(f"  - {_a}")
    _emit_m._emit("")


def _render_plan_rich(phasen, tasks, tests, akzeptanzkriterien) -> None:
    body = []
    for _p in phasen:
        body.append(f"[bold cyan]Phase {_p.get('id', '?')}[/]: {_p.get('titel', '')}")
        for _t in tasks:
            if isinstance(_t, dict) and _t.get("phase_id") == _p.get("id"):
                _files = ", ".join(_t.get("task_files", [])) or "(keine)"
                _action = _t.get("action", "?")
                _color = {"create": "green", "update": "yellow", "read": "dim"}.get(_action, "white")
                body.append(
                    f"  [{_color}]{_t.get('id')} [{_action}][/] {_t.get('name', '')[:55]}"
                )
                body.append(f"       [dim]→ {_files}[/]")
                _desc = (_t.get("description") or "").strip().replace("\n", " ")
                if _desc:
                    body.append(f"       [dim]{_desc[:800]}[/]")
        body.append("")
    # M-410c: Tasks ohne phase_id (flacher Plan, z.B. Architect)
    _ohne_phase = [
        _t for _t in tasks
        if isinstance(_t, dict) and not _t.get("phase_id")
    ]
    if _ohne_phase:
        body.append("")
        for _t in _ohne_phase:
            _files = ", ".join(_t.get("task_files", [])) or "(keine)"
            _action = _t.get("action", "?")
            _color = {"create": "green", "update": "yellow",
                      "read": "dim", "architect": "magenta"}.get(_action, "white")
            body.append(
                f"  [{_color}]{_t.get('id')} [{_action}][/] "
                f"{_t.get('name', '')[:55]}"
            )
            body.append(f"       [dim]→ {_files}[/]")
            _desc = (_t.get("description") or "").strip().replace("\n", " ")
            if _desc:
                body.append(f"       [dim]{_desc[:800]}[/]")

    if tests:
        body.append(f"[bold]Tests ({len(tests)}):[/]")
        for _t in tests:
            body.append(f"  [dim]-[/] {_t}")
    if akzeptanzkriterien:
        body.append(f"[bold]Akzeptanzkriterien ({len(akzeptanzkriterien)}):[/]")
        for _a in akzeptanzkriterien:
            body.append(f"  [dim]-[/] {_a}")
    _rich._console.print(_rich._RichPanel(
        "\n".join(body),
        title=f"[bold cyan]PLAN[/] — {len(phasen)} Phasen, {len(tasks)} Tasks",
        border_style="cyan",
    ))


def panel_diff(diff_text: str, title: str = "HUMAN GATE") -> None:
    """Zeigt den Diff (Box mit Syntax-Highlighting)."""
    if _rich._use_rich:
        _rich._console.print(_rich._RichPanel(
            _rich._RichSyntax(diff_text, "diff", theme="monokai", line_numbers=False),
            title=f"[bold yellow]{title}[/]",
            border_style="yellow",
        ))
    else:
        _emit_m._emit("")
        _emit_m._emit("=" * 62)
        _emit_m._emit(f"  {title}")
        _emit_m._emit("=" * 62)
        for line in diff_text.splitlines():
            _emit_m._emit(line)
        _emit_m._emit("=" * 62)
        _emit_m._emit("")


def panel_plan(phasen, tasks, tests, akzeptanzkriterien) -> None:
    """Zeigt den Plan (Box in pretty/live, Plain in ci)."""
    if _rich._use_rich:
        _render_plan_rich(phasen, tasks, tests, akzeptanzkriterien)
    else:
        _render_plan_plain(phasen, tasks, tests, akzeptanzkriterien)


plan = panel_plan
