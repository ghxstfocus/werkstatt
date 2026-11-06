"""Patch-Anwendung (Fix AZ Stufe 4, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-Kompatibilitaet
(Tests patchen werkstatt.loop._apply_patches_with_hooks, _call_hook).
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Audit-Proxy (Fix AZ Stufe 4)."""
    from werkstatt.loop import audit as _loop_audit
    return _loop_audit(*args, **kwargs)


def _call_hook(*args, **kwargs):
    """Late-Binding-Hook-Proxy (Fix AZ Stufe 4).

    Tests patchen werkstatt.loop._call_hook. Der Proxy loest den
    Namen bei jedem Aufruf in werkstatt.loop auf, damit die Patches
    wirksam bleiben.
    """
    from werkstatt.loop import _call_hook as _loop_call_hook
    return _loop_call_hook(*args, **kwargs)


def _apply_one_patch(
    content: str, old: str, new: str,
) -> tuple[str, str]:
    """K49: Mehrstufiger old_string-Fallback fuer Aider/Search-Replace."""
    if old in content:
        return content.replace(old, new, 1), "exact"
    _old_s = old.lstrip()
    if _old_s and _old_s in content:
        return content.replace(_old_s, new.lstrip(), 1), "strip"
    _SEP = chr(10) + chr(10)  # "\n\n"
    if _SEP in old:
        _parts = old.rsplit(_SEP, 1)
        _just_old = _parts[-1]
        if _just_old and _just_old in content:
            _new_tail = new.rsplit(_SEP, 1)[-1]
            return (
                content.replace(_just_old, _new_tail, 1),
                "context_only",
            )
    if _SEP in _old_s:
        _parts = _old_s.rsplit(_SEP, 1)
        _just_old = _parts[-1]
        if _just_old and _just_old in content:
            _new_tail = new.rsplit(_SEP, 1)[-1]
            return (
                content.replace(_just_old, _new_tail, 1),
                "context_only",
            )
    return content, "fail"


def _diagnose_patch(content: str, old: str, new: str) -> dict:
    """OP-060a: Diagnose eines Patches VOR dem Anwenden.

    Rueckgabe: {grund, old_string_len, vorkommen}.
    grund: 'leer' | 'kein_match' | 'mehrdeutig' | 'no_effect' | 'ok'.
    """
    if not old:
        return {"grund": "leer", "old_string_len": 0, "vorkommen": 0}
    _vork = content.count(old)
    if _vork == 0:
        return {"grund": "kein_match",
                "old_string_len": len(old), "vorkommen": 0}
    if _vork > 1:
        return {"grund": "mehrdeutig",
                "old_string_len": len(old), "vorkommen": _vork}
    if old == new:
        return {"grund": "no_effect",
                "old_string_len": len(old), "vorkommen": 1}
    return {"grund": "ok", "old_string_len": len(old), "vorkommen": 1}


def _patches_wirklich_angewendet(state) -> bool:
    """K50: True nur, wenn Patches geliefert UND angewandt wurden.

    Wird von beiden Reviewer-Reject-Pfaden genutzt (BUG-A + BUG-B),
    damit die Logik an einer Stelle lebt und testbar ist.
    fail-closed: state.patches truthy, aber applied_count 0/None
    -> False -> Reviewer-Reject wird NICHT ignoriert.
    """
    _applied = int(state.applied_count or 0)
    return bool(state.patches) and _applied > 0


def _apply_patches_with_diagnose(
    state: RunState,
    patches: list,
    *,
    phase_label: str = "",
) -> tuple[int, list[dict]]:
    """Wendet search/replace-Patches an, MIT Hooks (M-330).

    Wird vom Haupt-Pfad UND von der Reflection genutzt.
    Hooks:
      - pre_tool_use pro Patch (allow-Check)
      - post_tool_use nach Apply
      - simplify nach Apply

    Rueckgabe: (Anzahl, Liste der Diagnosen).
    Jede Diagnose: {file, old_string_len, vorkommen, grund}.
    """
    pd = state.project_dir
    pn = state.project_name

    diags: list[dict] = []

    # 1. PreToolUse pro Patch
    for _pat in patches:
        if not isinstance(_pat, dict):
            continue
        _hook_res = _call_hook("pre_tool_use.py", {
            "patch": _pat.get("new_string", "") or _pat.get("content", ""),
            "action": _pat.get("action", "update"),
            "project_dir": str(pd),
        })
        if not _hook_res.get("allow", False):
            audit("loop_hook_blocked",
                  {"hook": "pre_tool_use", "phase": phase_label,
                   "reason": _hook_res.get("reason", "")},
                  pd, pn)
            for _p in patches:
                if isinstance(_p, dict):
                    diags.append({
                        "file": _p.get("file", ""),
                        "old_string_len": len(_p.get("old_string", "") or ""),
                        "grund": "hook_blocked", "vorkommen": 0})
            return 0, diags

    # 2. Apply (search/replace)
    _applied = 0
    for _pat in patches:
        if not isinstance(_pat, dict):
            continue
        _f = _pat.get("file", "")
        _old = _pat.get("old_string", "")
        _new = _pat.get("new_string", "")
        _action_del = _pat.get("action", "update")
        if _action_del == "delete":
            # Fix AV: Delete im Reflection/Phase-Repair-Pfad.
            # Keine Task-Whitelist (task_files=None), nur harte Checks.
            if not _f:
                continue
            _ok_d, _grund_d = _delete_ziel_erlaubt(
                Path(_f), None, Path(pd),
            )
            if not _ok_d:
                audit("loop_patch_delete_blocked",
                      {"file": _f, "grund": _grund_d,
                       "phase": phase_label, "modus": "reflection"}, pd, pn)
                continue
            _target = Path(pd) / _f
            if not _target.exists():
                audit("loop_patch_delete_skip_missing",
                      {"file": _f, "phase": phase_label,
                       "modus": "reflection"}, pd, pn)
                diags.append({"file": _f, "old_string_len": 0,
                              "grund": "datei_fehlt", "vorkommen": 0})
                continue
            try:
                _target.unlink()
            except OSError as _e:
                audit("loop_patch_delete_failed",
                      {"file": _f, "fehler": str(_e)[:200],
                       "phase": phase_label, "modus": "reflection"}, pd, pn)
                continue
            audit("loop_patch_deleted",
                  {"file": _f, "phase": phase_label,
                   "modus": "reflection"}, pd, pn)
            diags.append({"file": _f, "old_string_len": 0,
                          "grund": "delete_ok", "vorkommen": 1})
            _applied += 1
            continue
        if not _f or not _old or not _new:
            diags.append({"file": _f, "old_string_len": len(_old or ""),
                          "grund": "leer", "vorkommen": 0})
            continue
        _target = Path(pd) / _f
        if not _target.exists():
            audit("loop_patch_file_missing",
                  {"file": _f, "phase": phase_label}, pd, pn)
            diags.append({"file": _f, "old_string_len": len(_old),
                          "grund": "datei_fehlt", "vorkommen": 0})
            continue
        _content = _target.read_text(encoding="utf-8")
        _diag = _diagnose_patch(_content, _old, _new)
        if _diag["grund"] in ("kein_match", "no_effect", "leer"):
            # Bestehende Audit-Erwartungen (K30): bei kein_match
            # zusaetzlich loop_patch_old_string_not_found schreiben.
            if _diag["grund"] == "kein_match":
                audit("loop_patch_old_string_not_found",
                      {"file": _f, "phase": phase_label}, pd, pn)
            diags.append({"file": _f, **_diag})
            continue
        _neu_content, _match = _apply_one_patch(_content, _old, _new)
        if _match == "fail":
            audit("loop_patch_old_string_not_found",
                  {"file": _f, "phase": phase_label}, pd, pn)
            diags.append({"file": _f, **_diag})
            continue
        # FIX N 2026-10-31: Write-Fehler fail-closed.
        try:
            _target.write_text(
                _collapse_excess_blank_lines(_neu_content),
                encoding="utf-8",
            )
        except OSError as _e:
            audit("loop_patch_write_failed",
                  {"file": _f, "phase": phase_label, "fehler": str(_e)[:200]},
                  pd, pn)
            diags.append({"file": _f, **_diag, "grund": "write_failed"})
            continue
        audit("loop_patch_applied",
              {"file": _f, "phase": phase_label, "match": _match}, pd, pn)
        diags.append({"file": _f, **_diag})
        _applied += 1

    if _applied == 0:
        return 0, diags

    # M-334b: post_tool_use entfernt. Der Hook prueft die
    # Werkstatt-Baseline (cwd=/opt/werkstatt), nicht das
    # Zielprojekt. _verify_patches prueft das Zielprojekt
    # (via verify.json). post_tool_use war redundant und blind.

    # 4. Simplify
    _hook_res = _call_hook("simplify.py", {
        "diff": _get_git_diff_for_hook() if "_get_git_diff_for_hook" in globals() else "",
    })
    if not _hook_res.get("allow", False):
        audit("loop_hook_blocked",
              {"hook": "simplify", "phase": phase_label,
               "reason": _hook_res.get("reason", "")},
              pd, pn)

    return _applied, diags


def _apply_patches_with_hooks(
    state: RunState,
    patches: list,
    *,
    phase_label: str = "",
) -> int:
    """OP-060a: Wrapper fuer Rueckwaerts-Kompatibilitaet.

    Ruft _apply_patches_with_diagnose auf und gibt nur die Anzahl
    angewendeter Patches zurueck. Bestehende Aufrufer bleiben
    unveraendert.
    """
    applied, _diags = _apply_patches_with_diagnose(
        state, patches, phase_label=phase_label,
    )
    return applied


def _delete_ziel_erlaubt(
    target_rel: Path,
    task_files,
    project_dir: Path,
) -> tuple[bool, str]:
    """Fix AV: strukturelle Sicherheit fuer action='delete'.

    task_files=None -> Reflection-Modus, kein Whitelist-Check.
    Rueckgabe: (ok, grund). grund="" bei ok.
    """
    _parts = target_rel.parts
    if target_rel.is_absolute() or ".." in _parts:
        return False, "pfad"
    if ".git" in _parts:
        return False, ".git"
    if "data" in _parts and "migrations" in _parts:
        return False, "migrations"
    if task_files is not None and str(target_rel) not in task_files:
        return False, "nicht_in_task_files"
    _pdr = project_dir.resolve()
    try:
        (_pdr / target_rel).resolve().relative_to(_pdr)
    except ValueError:
        return False, "ausserhalb_project_dir"
    return True, ""



def _get_git_diff_for_hook(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._get_git_diff_for_hook."""
    from werkstatt.loop import _get_git_diff_for_hook as _orig
    return _orig(*args, **kwargs)


__all__ = [
    '_apply_one_patch',
    '_apply_patches_with_diagnose',
    '_apply_patches_with_hooks',
    '_delete_ziel_erlaubt',
    '_diagnose_patch',
    '_patches_wirklich_angewendet',
]


def _collapse_excess_blank_lines(text: str, max_blank: int = 2) -> str:
    """Reduziert 3+ aufeinanderfolgende Leerzeilen auf max_blank.

    Der Builder fuegt bei update-Tasks gelegentlich Extra-Leerzeilen
    nach def-Zeilen ein (Live-Beleg 2026-11-02: __all__-Task, Ruff E303).

    Nicht automatisch gehookt: Diagnose-Tests erwarten unveraenderten
    Content. Manuell aufrufbar als Post-Process:

        content = _collapse_excess_blank_lines(content)
    """
    lines = text.splitlines()
    out = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= max_blank:
                out.append(line)
        else:
            blank_run = 0
            out.append(line)
    result = chr(10).join(out)
    if text.endswith(chr(10)):
        result += chr(10)
    return result
