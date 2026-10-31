"""Commit + Fortschritts-Doku (Fix AZ Stufe 5a, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-Kompatibilitaet.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Audit-Proxy (Fix AZ Stufe 5a)."""
    from werkstatt.loop import audit as _loop_audit
    return _loop_audit(*args, **kwargs)


def _task_fortschritt_block(pd: Path, pn: str) -> str:
    """FIX AD 2026-10-31: Task-Fortschritt aus PhaseState formatieren.

    Zeigt dem User beim Human-Gate (und nach Resume), welche
    Tasks bereits done sind und welche noch offen. Ohne diese
    Anzeige war bei einem abgebrochenen Multi-Task-Lauf (t5
    failed, t1-t4 ok) nicht sichtbar, dass 4/7 schon gebaut
    wurden.

    Format pro Task:
      [x] t1 done
      [!] t5 failed (grund)
      [~] t6 running
      [ ] t7 pending
      [>] t2 split
    """
    from werkstatt.phase_state import PhaseState
    try:
        _ps = PhaseState(pn, base_dir=Path(pd) / ".werkstatt")
        if not _ps.exists():
            return ""
        if not _ps.load():
            return ""
    except Exception:  # noqa: BLE001, S110
        return ""
    _tasks = _ps.data.get("tasks") or []
    if not _tasks:
        return ""
    _done = 0
    _failed = 0
    _pending = 0
    _lines: list[str] = []
    for _t in _tasks:
        if not isinstance(_t, dict):
            continue
        _st = _t.get("status", "pending")
        _tid = _t.get("id", "?")
        _name = (_t.get("name") or "")[:60]
        if _st == "done":
            _lines.append(f"  [x] {_tid} {_name}")
            _done += 1
        elif _st == "failed":
            _fail_grund = _t.get("failure") or "unbekannt"
            _lines.append(f"  [!] {_tid} {_name}  (failed: {_fail_grund})")
            _failed += 1
        elif _st == "running":
            _lines.append(f"  [~] {_tid} {_name}")
            _pending += 1
        elif _st == "split":
            _lines.append(f"  [>] {_tid} {_name}  (split)")
        else:
            _lines.append(f"  [ ] {_tid} {_name}")
            _pending += 1
    _total = len([t for t in _tasks if isinstance(t, dict)])
    _head = (
        f"Tasks: {_done}/{_total} done"
        + (f", {_failed} failed" if _failed else "")
        + (f", {_pending} offen" if _pending else "")
    )
    return _head + "\n" + "\n".join(_lines) + "\n"


def _committe_zielprojekt(state: RunState) -> tuple[bool, str]:
    """M-487: Committet uncommittete Aenderungen im Zielprojekt.

    Wird vom Human-Gate nach 'j' aufgerufen. Fail-closed bei Git-Fehler.
    Rueckgabe: (True, sha) bei Erfolg, (True, "") wenn nichts zu tun,
    (False, fehlertext) bei Fehler.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return False, "kein project_dir"

    try:
        status = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git status fehlgeschlagen: {_e}"
    if not status.stdout.strip():
        audit("loop_human_gate_commit_skip",
              {"reason": "working_tree_clean"}, pd, pn)
        return True, ""

    # FIX 2026-10-31 (Fix K): PROGRESS.md-Eintrag VOR git add -A,
    # damit er im selben Commit landet wie der Task-Diff. Vorher
    # wurde er vom Hauptloop NACH dem Commit geschrieben und blieb
    # uncommitted (Live-Beleg 2026-10-30: 53db3b0).
    try:
        from werkstatt import progress as _progress_k
        _tasks_len_k = len(getattr(state, "tasks", None) or [])
        _tasks_ok_k = int(getattr(state, "tasks_ok_counter", 0) or 0)
        _progress_k.append(
            pd,
            name=f"Phase abgeschlossen: {pn}",
            status="phase_ende",
            info=f"tasks_ok={_tasks_ok_k}/{_tasks_len_k}",
        )
    except Exception:  # noqa: BLE001, S110
        pass

    # FIX 2026-10-31: Task-File-Pruefung VOR git add.
    # Wenn ein Task als done markiert ist und task_files nennt,
    # muessen diese im aktuellen Working Tree stehen. Sonst
    # Fake-Done. Nutzt status --porcelain (erfasst auch
    # untracked, die diff --name-only verschweigt).
    try:
        # FIX X 2026-10-31: splitlines() OHNE strip() — sonst geht
        # das fuehrende Leerzeichen von " M path" verloren und
        # ln[3:] schneidet 2 Zeichen zu weit ab (live: ' M a.py'
        # wurde zu '.py').
        _status_raw = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain", "-uall"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
    except Exception:  # noqa: BLE001
        _status_raw = ""
    _diff_set = set()
    for _ln in _status_raw.splitlines():
        if not _ln or not _ln.strip():
            continue
        # Format: "XY path" — path ab Spalte 3 (2 Status + 1 Space)
        _p = _ln[3:].strip() if len(_ln) > 3 else ""
        if _p and " -> " in _p:
            _p = _p.split(" -> ", 1)[1]
        if _p:
            _diff_set.add(_p)
    _tasks_state = getattr(state, "tasks", None) or []
    for _t in _tasks_state:
        if not isinstance(_t, dict):
            continue
        if _t.get("status") != "done":
            continue
        for _tf in (_t.get("task_files") or []):
            if not isinstance(_tf, str) or not _tf:
                continue
            if _tf not in _diff_set:
                audit("loop_human_gate_task_files_missing",
                      {"task_id": _t.get("id", ""), "file": _tf}, pd, pn)
                return False, (
                    f"Task {_t.get('id','?')} meldet done, aber "
                    f"{_tf} steht nicht im git-Diff. Fake-Done verhindert."
                )

    try:
        add = subprocess.run(
            ["git", "-C", str(pd), "add", "-A"],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git add fehlgeschlagen: {_e}"
    if add.returncode != 0:
        return False, f"git add rc={add.returncode}: {add.stderr.strip()[:200]}"

    _name = getattr(state, "git_author_name", "") or "builder"
    _email = getattr(state, "git_author_email", "") or "builder@security-ai.local"
    _aufgabe = (getattr(state, "aufgabe", "") or "").strip()
    _msg_kurz = _aufgabe.split("\n")[0][:80] if _aufgabe else "Werkstatt-RERUN"
    _msg = f"chore(werkstatt): {_msg_kurz}\n\nRERUN (M-487, human_gate committet selbst)."

    _commit_argv = [
        "git", "-C", str(pd),
        "-c", f"user.name={_name}",
        "-c", f"user.email={_email}",
        "commit", "-m", _msg,
    ]
    try:
        commit = subprocess.run(
            _commit_argv,
            capture_output=True, text=True, check=False, timeout=30,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git commit fehlgeschlagen: {_e}"
    if commit.returncode != 0:
        audit("loop_human_gate_commit_fehler",
              {"rc": commit.returncode, "stderr": commit.stderr[:300]}, pd, pn)
        return False, f"git commit rc={commit.returncode}: {commit.stderr.strip()[:200]}"

    try:
        _rev = subprocess.run(
            ["git", "-C", str(pd), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        _sha = _rev.stdout.strip()[:12]
    except Exception:  # noqa: BLE001
        _sha = ""

    # FIX AH 2026-10-31: Flag setzen, damit der Loop-Ende-Pfad
    # nicht doppelt PROGRESS.md schreibt.
    try:
        state.progress_written_at_commit = True  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        pass
    audit("loop_human_gate_committed",
          {"sha": _sha, "msg": _msg_kurz}, pd, pn)
    return True, _sha


__all__ = ['_committe_zielprojekt', '_task_fortschritt_block']
