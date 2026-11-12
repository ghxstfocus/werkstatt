"""Commit + Fortschritts-Doku (Fix AZ Stufe 5a, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-Kompatibilitaet.
"""
from __future__ import annotations

import os
import re
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
    except Exception:
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
        elif _st == "human_review":
            # OP-060b: Mensch muss entscheiden.
            _hr_grund = _t.get("failure") or "unbekannt"
            _lines.append(
                f"  [~] {_tid} {_name}  (human_review: {_hr_grund})"
            )
            _pending += 1
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


def _doku_nachzug_aktiv() -> bool:
    """OP-048: Opt-in via WERKSTATT_DOKU_NACHZUG=1."""
    return os.environ.get("WERKSTATT_DOKU_NACHZUG") == "1"


def _op_nnn_aus_aufgabe(aufgabe: str) -> str | None:
    """OP-048: Erste OP-NNN-Referenz aus der Aufgabe."""
    m = re.search(r"\bOP-\d{3}[a-z]?\d*\b", aufgabe or "")
    return m.group(0) if m else None


def _status_md_op_entfernen(status_md_path: Path, op_nnn: str) -> tuple[bool, str]:
    """OP-048: Entfernt '### OP-NNN'-Block bis zur naechsten Ueberschrift."""
    if not status_md_path.exists():
        return False, f"STATUS.md nicht gefunden: {status_md_path}"
    txt = status_md_path.read_text(encoding="utf-8")
    pat = re.compile(rf"^### {re.escape(op_nnn)}:", re.MULTILINE)
    m = pat.search(txt)
    if not m:
        return False, f"{op_nnn} nicht in STATUS.md"
    start = m.start()
    rest = txt[m.end():]
    end_pat = re.compile(r"^(### |## )", re.MULTILINE)
    em = end_pat.search(rest)
    end = (m.end() + em.start()) if em else len(txt)
    new_txt = txt[:start].rstrip("\n") + "\n\n" + txt[end:].lstrip("\n")
    status_md_path.write_text(new_txt, encoding="utf-8")
    return True, ""


def _delete_zone_op_append(status_md_path: Path, op_nnn: str, subject: str) -> bool:
    """OP-048: Ergaenzt OP-NNN in der Delete-Zone-Tabelle.

    Legt die Sektion '## Delete-Zone' an, falls sie fehlt.
    """
    from datetime import date as _date_dz
    datum = _date_dz.today().isoformat()
    note = subject.replace("|", "-")[:60]
    new_row = f"| {op_nnn} | erledigt {datum} | {note} | - |"
    try:
        # OP-069-Fix (2026-11-02): Datei muss existieren. Sonst False.
        # Ohne diesen Check legt write_text am Ende die Datei an,
        # was der Akzeptanz "bei fehlender Datei: False" widerspricht.
        if not status_md_path.exists():
            return False
        text = status_md_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        dz_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == "## Delete-Zone":
                dz_idx = i
                break
        if dz_idx < 0:
            if text and not text.endswith("\n"):
                text += "\n"
            text += (
                "## Delete-Zone\n\n"
                "| OP | Status | Notiz | Commit |\n"
                "|---|---|---|---|\n"
                f"{new_row}\n"
            )
        else:
            section_end = len(lines)
            for j in range(dz_idx + 1, len(lines)):
                if lines[j].startswith("## "):
                    section_end = j
                    break
            last_idx = -1
            for j in range(dz_idx, section_end):
                if lines[j].startswith("|"):
                    last_idx = j
            if last_idx < 0:
                return False
            lines.insert(last_idx + 1, new_row)
            text = "\n".join(lines) + "\n"
        status_md_path.write_text(text, encoding="utf-8")
    except OSError:
        return False
    return True


def _progress_op_done(
    pd: Path, op_nnn: str, subject: str, pn: str, *, run_id: str | None = None,
) -> bool:
    """OP-048: Appendiert OP-Done-Eintrag an PROGRESS.md.

    OP-063b: Idempotent gegenueber bereits enthaltenem OP-Praefix.
    Sonst entsteht 'OP-004: OP-004: In core/...'.
    """
    _subj = (subject or "").strip()
    _prefix = f"{op_nnn}:"
    if _subj.upper().startswith(_prefix.upper()):
        _subj = _subj[len(_prefix):].lstrip()
    try:
        from werkstatt import progress as _progress_od
        return _progress_od.append(
            pd,
            name=f"{op_nnn}: {_subj}",
            status="done",
            info=f"Loop-Doku-Nachzug (Ebene 1). Beleg: git log {pn}.",
            run_id=run_id,
        )
    except Exception:
        return False


def _update_kennzahlen(status_md_path: Path, pd: Path) -> bool:
    """OP-055: Aktualisiert HEAD-Zeile in '## Kennzahlen' (nur HEAD).

    Tests/ruff/mypy: Follow-up (blockiert von OP-039, pytest --co -q
    kostet bei security-ai 30-60s).
    """
    if not status_md_path.exists():
        return False
    try:
        sha = subprocess.run(
            ["git", "-C", str(pd), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout.strip()
    except Exception:
        return False
    if not sha:
        return False
    txt = status_md_path.read_text(encoding="utf-8")
    head_pat = re.compile(r"^(- HEAD: )\S+[^\n]*$", re.MULTILINE)
    if not head_pat.search(txt):
        return False
    new_txt = head_pat.sub("\\g<1>" + sha, txt, count=1)
    if new_txt == txt:
        return False
    status_md_path.write_text(new_txt, encoding="utf-8")
    return True


def _update_changelog(pd: Path, entry: str) -> bool:
    """OP-056: Fuegt Zeile in '## [Unreleased]' ein. Nur wenn Datei existiert."""
    changelog = Path(pd) / "CHANGELOG.md"
    if not changelog.exists():
        return False
    txt = changelog.read_text(encoding="utf-8")
    unrel_pat = re.compile(r"^## \[Unreleased\]\s*$", re.MULTILINE)
    m = unrel_pat.search(txt)
    if not m:
        return False
    pos = m.end()
    while pos < len(txt) and txt[pos] == "\n":
        pos += 1
    new_txt = txt[:pos] + f"- {entry}\n" + txt[pos:]
    changelog.write_text(new_txt, encoding="utf-8")
    return True


def _architecture_drift_check(pd: Path) -> dict:
    """OP-057: Meldet .py neu/geloescht ohne ARCHITECTURE.md-Aenderung."""
    try:
        diff = subprocess.run(
            ["git", "-C", str(pd), "diff", "--name-status", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
    except Exception:
        return {"drift": False, "reason": "git_diff_failed"}
    py_changed = []
    arch_changed = False
    for ln in diff.splitlines():
        parts = ln.split("\t", 1)
        if len(parts) != 2:
            continue
        st, path = parts
        if path == "docs/ARCHITECTURE.md":
            arch_changed = True
        if path.endswith(".py") and st in ("A", "D"):
            py_changed.append((st, path))
    if py_changed and not arch_changed:
        return {"drift": True, "py": py_changed}
    return {"drift": False, "py": py_changed, "arch_changed": arch_changed}


def _build_commit_subject(aufgabe: str, op_nnn: str | None) -> str:
    """OP-063: Commit-Subject aus Aufgabe, wortgrenzen-sicher.

    OP-169: Markdown-Header-Prefix (z.B. "### ") vor dem OP-NNN-
    startswith-Check strippen. Sonst startet _line mit "### " und
    der OP-Prefix wird doppelt ("OP-145: ### OP-145: ...").
    """
    _line = (aufgabe or "").split("\n")[0].strip()
    if not _line:
        _line = "update"
    while _line.startswith("#"):
        _line = _line[1:].lstrip()
    if op_nnn and _line.upper().startswith(op_nnn.upper()):
        _rest = _line[len(op_nnn):].lstrip(": ").strip()
        if _rest:
            _line = _rest
    # OP-063b: Limit gilt fuer das GESAMTE Subject (inkl. OP-Praefix).
    # Sonst wird z.B. 'OP-004: ' (8 Zeichen) nicht eingerechnet und
    # 'fix(security-ai): OP-004: ...' landet ueber 72 Zeichen.
    _total_limit = 55
    if op_nnn:
        _prefix_len = len(op_nnn) + 2  # 'OP-NNN: '
        _limit = max(20, _total_limit - _prefix_len)
    else:
        _limit = _total_limit
    if len(_line) > _limit:
        _cut = _line[:_limit]
        _sp = _cut.rfind(" ")
        if _sp > 20:
            _line = _cut[:_sp].rstrip(".,;:")
        else:
            _line = _cut.rstrip(".,;:")
    if op_nnn:
        return f"{op_nnn}: {_line}"
    return _line


def _post_commit_check(project_dir: Path) -> tuple[bool, str, dict[str, object]]:
    """Prueft nach Commit HEAD, committed Diff und sauberen Working Tree."""
    commands = [
        ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
        ["git", "-C", str(project_dir), "show", "--check", "--oneline", "HEAD"],
        ["git", "-C", str(project_dir), "status", "--porcelain", "--untracked-files=all"],
    ]
    results: list[subprocess.CompletedProcess[str]] = []
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except Exception as exc:
            return False, "", {
                "reason": "command_failed",
                "message": f"{command[3]} fehlgeschlagen: {exc}",
            }
        if result.returncode != 0:
            return False, "", {
                "reason": "command_failed",
                "message": (
                    f"{command[3]} rc={result.returncode}: "
                    f"{(result.stderr or '').strip()[:240]}"
                ),
            }
        results.append(result)

    sha = results[0].stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", sha):
        return False, sha, {
            "reason": "invalid_head",
            "message": "HEAD lieferte keine gueltige Commit-SHA.",
        }

    pending: list[str] = []
    for line in results[2].stdout.splitlines():
        if line.strip():
            pending.append(line[3:].strip()[:240] if len(line) > 3 else line[:240])
        if len(pending) == 20:
            break
    if pending:
        return False, sha, {
            "reason": "working_tree_dirty_after_commit",
            "message": f"Arbeitsbaum enthaelt nach Commit noch {len(pending)} angezeigte Aenderung(en).",
            "pending_files": pending,
        }
    return True, sha, {"reason": "verified", "message": "HEAD, Commit-Diff und Arbeitsbaum sind geprueft."}


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
    except Exception as _e:
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
        _tasks_len_k = len(state.tasks or [])
        _tasks_ok_k = int(getattr(state, "tasks_ok_counter", 0) or 0)
        _progress_k.append(
            pd,
            name=f"Phase abgeschlossen: {pn}",
            status="phase_ende",
            info=f"tasks_ok={_tasks_ok_k}/{_tasks_len_k}",
            run_id=getattr(state, "run_id", None),
        )
    except Exception:
        pass

    # OP-048/055/056/057: Doku-Selbstpflege Ebene 1+2 (opt-in WERKSTATT_DOKU_NACHZUG=1).
    if _doku_nachzug_aktiv():
        _op_nnn = _op_nnn_aus_aufgabe(state.aufgabe or "")
        _status_path = Path(pd) / "docs" / "STATUS.md"
        if not _op_nnn:
            audit("doku_nachzug_skip", {"reason": "no_op_in_aufgabe"}, pd, pn)
        elif not _status_path.exists():
            audit("doku_nachzug_skip",
                  {"reason": "no_status_md", "op_nnn": _op_nnn}, pd, pn)
        else:
            _subject = (state.aufgabe or "").strip().split("\n")[0][:60]
            # M-Fix-2026-11-02: Delete-Zone-Append VOR dem Entfernen pruefen.
            # Sonst geht der OP spurlos verloren wenn die Sektion fehlt.
            _dz_ok = _delete_zone_op_append(_status_path, _op_nnn, _subject)
            if not _dz_ok:
                audit("doku_nachzug_skip",
                      {"reason": "delete_zone_append_failed",
                       "op_nnn": _op_nnn}, pd, pn)
            _rm_ok = False
            if _dz_ok:
                _rm_ok, _rm_msg = _status_md_op_entfernen(_status_path, _op_nnn)
            if _rm_ok:
                _progress_op_done(
                    Path(pd), _op_nnn, _subject, pn,
                    run_id=getattr(state, "run_id", None),
                )
                _update_kennzahlen(_status_path, Path(pd))
                _update_changelog(Path(pd), f"{_op_nnn}: {_subject}")
                _drift = _architecture_drift_check(Path(pd))
                if _drift.get("drift"):
                    audit("committer_architecture_drift",
                          {"py_changed": _drift.get("py", [])}, pd, pn)
                    print(f"  WARNUNG: Architecture-Drift: "
                          f"{len(_drift.get('py', []))} neue/geloeschte .py "
                          f"ohne ARCHITECTURE.md-Aenderung")
            else:
                # OP-063: OP-NNN steht vielleicht nur noch in der
                # Delete-Zone (Body schon entfernt). Dann ist
                # _rm_ok=False, aber der OP-Eintrag in PROGRESS.md
                # fehlt trotzdem — Retry.
                _dz_text = (
                    _status_path.read_text(encoding="utf-8")
                    if _status_path.exists() else ""
                )
                _already_dz = f"| {_op_nnn} |" in _dz_text
                if _already_dz:
                    _progress_op_done(
                        Path(pd), _op_nnn, _subject, pn,
                        run_id=getattr(state, "run_id", None),
                    )
                    audit("doku_nachzug_delete_zone_retry",
                          {"op_nnn": _op_nnn}, pd, pn)
                else:
                    audit("doku_nachzug_skip",
                          {"reason": _rm_msg, "op_nnn": _op_nnn},
                          pd, pn)

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
    except Exception:
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
    _tasks_state = state.tasks or []
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
    except Exception as _e:
        return False, f"git add fehlgeschlagen: {_e}"
    if add.returncode != 0:
        return False, f"git add rc={add.returncode}: {add.stderr.strip()[:200]}"

    _name = state.git_author_name or "builder"
    _email = state.git_author_email or "builder@security-ai.local"
    _aufgabe = (state.aufgabe or "").strip()
    # OP-038: Konsistente Commit-Message nach Conventional-Commits-Schema.
    # Format: <type>(<scope>): <kurztitel>  + Body mit Loop-Hinweis.
    # type: docs (alle .md), feat (code neu), fix (code-patch), chore (mixed)
    _aufgabe_line = (_aufgabe.split("\n")[0] if _aufgabe else "").strip()
    # type ableiten: hat der Diff nur .md?
    _changed = [p["file"] for p in (state.patches or [])
                if isinstance(p, dict) and p.get("file")]
    _only_md = bool(_changed) and all(f.endswith(".md") for f in _changed)
    _any_md = any(f.endswith(".md") for f in _changed) if _changed else False
    if _only_md:
        _type = "docs"
    elif _changed and not _any_md:
        _action = "feat"
        # feat vs fix: bei create neu, bei update patch
        _actions = [p.get("action") for p in (state.patches or [])
                    if isinstance(p, dict)]
        if all(a == "create" for a in _actions if a):
            _type = "feat"
        else:
            _type = "fix"
    else:
        _type = "chore"
    # Scope: Projektname (Manifest hat <name>)
    _scope = state.project_name or "werkstatt"
    # OP-063: Subject wortgrenzen-sicher, OP-NNN als Praefix.
    _op_nnn_subj = _op_nnn_aus_aufgabe(_aufgabe) if _aufgabe else None
    _msg_kurz = _build_commit_subject(_aufgabe or "", _op_nnn_subj)
    # Message bauen
    _msg = f"{_type}({_scope}): {_msg_kurz}\n\nLoop-Auftrag (Werkstatt human_gate)."
    # Laengen-Check: 72 Zeichen Subject-Limit
    if len(_msg.split("\n")[0]) > 72:
        _subject = _msg.split("\n")[0][:69] + "..."
        _rest = "\n".join(_msg.split("\n")[1:])
        _msg = _subject + "\n" + _rest

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
    except Exception as _e:
        return False, f"git commit fehlgeschlagen: {_e}"
    if commit.returncode != 0:
        audit("loop_human_gate_commit_fehler",
              {"rc": commit.returncode, "stderr": commit.stderr[:300]}, pd, pn)
        return False, f"git commit rc={commit.returncode}: {commit.stderr.strip()[:200]}"

    # Commit ist noch kein Abschluss: HEAD, Commit-Diff und Working Tree
    # werden nach dem Commit erneut geprueft. So werden Hook-Reste und
    # parallele Aenderungen nicht als Teil des geprueften Commits ausgegeben.
    _check_ok, _sha_full, _check_info = _post_commit_check(Path(pd))
    _sha = _sha_full[:12]
    try:
        state.progress_written_at_commit = True
    except (AttributeError, TypeError):
        pass

    if not _check_ok:
        audit(
            "loop_human_gate_commit_postcheck_failed",
            {
                "sha": _sha,
                "reason": _check_info.get("reason", "unknown"),
                "pending_files": _check_info.get("pending_files", [])[:20],
            },
            pd,
            pn,
        )
        audit(
            "loop_human_gate_committed",
            {"sha": _sha, "msg": _msg_kurz, "post_commit_check": "failed"},
            pd,
            pn,
        )
        return False, (
            f"Commit {_sha or '(SHA unbekannt)'} erstellt, "
            f"Nachkontrolle fehlgeschlagen: "
            f"{_check_info.get('message', 'Arbeitsbaum erneut pruefen')}"
        )

    audit(
        "loop_human_gate_committed",
        {"sha": _sha, "msg": _msg_kurz, "post_commit_check": "passed"},
        pd,
        pn,
    )
    return True, _sha


__all__ = ['_committe_zielprojekt', '_task_fortschritt_block']
