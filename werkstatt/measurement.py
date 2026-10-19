"""Mess-Bloecke (Phase 2 / Gate 18, 2026-10-19).

Aus pipeline.py extrahiert (Befund BQ, Reviewer-B:
8 Funktionen, collect_messwerte + 7 Mess-Bloecke).

Enthaelt:
- _mess_index_block
- _mess_inhalt_block
- _mess_inhalt_nach_apply
- _mess_inhalt_zieldateien (Phase C, stummes Fehlerbild,
  Befund AQ, deklariert)
- _messwerte_fuer_planner
- _messwerte_fuer_prompt
- format_messwerte_block
- collect_messwerte

Konsumenten:
- pipeline.py (Loop-Kontext, 4x collect_messwerte).
- commit_input.py (5 Funktionen, importiert
  _mess_index_block, _mess_inhalt_nach_apply,
  format_messwerte_block, collect_messwerte).

P1-Verortung (Befund BR): der 579-Verlust entsteht
NICHT hier, sondern in pipeline.py/_post_apply_messung
(Schreiber-Seite). _mess_inhalt_nach_apply ist der
Leser, nicht die Ursache.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from werkstatt.state import RunState


def _mess_index_block(state: RunState) -> str:
    """W52b-D: Index der Messungen statt Volltext.

    Format:
      PFAD  SHA1  GROESSE  PREVIEW  DATEI

    PREVIEW: erste 200 Zeichen (whitespace-normalisiert,
    mit ... wenn gekuerzt). Der Agent liest bei Bedarf
    per read_file. Kein Volltext im Prompt.

    Branchenstandard (Haystack, Cursor, OpenDev): Pointer
    = Identitaet + Groesse + Preview + Pfad."""
    _PREVIEW_LEN = 200
    if not getattr(state, "messungen", None):
        return "(keine Messungen)"
    zeilen = ["PFAD  SHA1  GROESSE  PREVIEW  DATEI"]
    for m in state.messungen:
        datei = getattr(m, "datei", None)
        rel = str(datei) if datei else "(nicht gespeichert)"
        # Preview lesen (nur wenn Datei existiert).
        preview = ""
        if datei is not None:
            try:
                roh = datei.read_text(encoding="utf-8",
                                      errors="replace")
                # Whitespace normalisieren (einzeilig).
                prev = " ".join(roh.split())
                if len(prev) > _PREVIEW_LEN:
                    preview = prev[:_PREVIEW_LEN] + "..."
                else:
                    preview = prev
            except OSError:
                preview = ""
        zeilen.append(
            f"{m.pfad}  {m.sha1[:8]}  {m.groesse}  "
            f"{preview or '(leer)'}  {rel}")
    return "\n".join(zeilen)


def _mess_inhalt_block(state: RunState) -> str:
    """W52b-D: Volltext-Block NUR fuer Rollen, die ihn
    brauchen (Planner beim Erstplan, Judge nach Apply)."""
    if not getattr(state, "messungen", None):
        return "(keine Messungen)"
    teile = []
    for m in state.messungen:
        datei = getattr(m, "datei", None)
        if datei is None:
            continue
        try:
            inhalt = datei.read_text(encoding="utf-8",
                                     errors="replace")
        except OSError:
            continue
        teile.append(f"=== {m.pfad} ===")
        teile.append(inhalt)
    return "\n".join(teile) if teile else "(keine Messungen)"


def _messwerte_fuer_planner(state: RunState) -> str:
    """W52b-D: Index statt Volltext.

    Der Planner bekommt die Datei-Liste + Pfade, liest
    bei Bedarf per read_file. Kein 100K-String mehr."""
    return _mess_index_block(state)


def _mess_inhalt_zieldateien(
        state: RunState, ziel_pfade: set[str]) -> str:
    """W61: Volltext der Zieldateien aus state.messungen.

    Nur fuer die Zieldateien (die der Builder patchen soll).
    Andere Messungen (Planner, Basis-Gate) bleiben im Index.
    """
    if not ziel_pfade or not getattr(state, "messungen", None):
        return ""
    teile = []
    for m in state.messungen:
        if not any(z in m.pfad or m.pfad in z
                   for z in ziel_pfade):
            continue
        datei = getattr(m, "datei", None)
        if datei is None:
            continue
        try:
            inhalt = datei.read_text(encoding="utf-8",
                                     errors="replace")
        except OSError:
            continue
        teile.append(f"=== ZIELDATEI {m.pfad} ===")
        teile.append(inhalt)
    return "\n".join(teile)


_NEW_FILE_MARKER = (
    "(nicht anwendbar -- reine new_file-Patches, "
    "Dateien werden durch die Patches neu angelegt)")


def _alle_patches_sind_new_file(state: RunState) -> bool:
    """New_file-Marker (2026-10-16): sind alle
    Patches typ=new_file?

    Liefert True, wenn mindestens ein Patch vorhanden
    ist UND alle Patches typ=new_file haben.
    Liefert False, wenn keine Patches da sind oder
    mindestens einer typ != new_file hat.
    """
    patches = state.code_patches or []
    if not patches:
        return False
    return all(
        isinstance(p, dict) and p.get("typ") == "new_file"
        for p in patches)


def _messwerte_fuer_prompt(state: RunState) -> str:
    """W52b-D: Index statt Volltext fuer Builder.

    - Bei reinen new_file-Patches: _NEW_FILE_MARKER.
    - Sonst: Index der Messungen. Der Builder liest
      die Datei bei Bedarf per read_file."""
    if not getattr(state, "messungen", None):
        if _alle_patches_sind_new_file(state):
            return _NEW_FILE_MARKER
        return "(keine)"
    return _mess_index_block(state)


def _mess_inhalt_nach_apply(state: RunState) -> str:
    """W52b-D: Volltext aus state.messungen_nach_apply.

    Fallback auf mess_protokoll_nach_apply (String), solange
    die strukturierte Liste in alten Laeufen leer ist."""
    nach = getattr(state, "messungen_nach_apply", None)
    if nach:
        teile = []
        for m in nach:
            datei = getattr(m, "datei", None)
            if datei is None:
                continue
            try:
                inhalt = datei.read_text(encoding="utf-8",
                                         errors="replace")
            except OSError:
                continue
            teile.append(f"=== {m.pfad} ===")
            teile.append(inhalt)
        if teile:
            return "\n".join(teile)
    # Fallback (Bestandsleser, deprecated).
    return state.mess_protokoll_nach_apply or ""


def collect_messwerte(state: RunState) -> dict[str, Any]:
    """Auflage 2135: extrahiert Messwerte aus dem Basis-Protokoll.

    Liefert ein dict mit den Werten, die der Builder fuer die
    Commit-Message braucht:
      - test_anzahl (int | None)
      - ruff (gruen|rot)
      - mypy (gruen|rot)
      - py_compile (gruen|rot)
      - git_status (clean|geaendert)
      - git_head (str)
      - verstrichene_zeit_s (float)

    Basis: state.basis_protokoll (geschrieben vom Basis-Gate).
    Fallback bei Parse-Fehler: test_anzahl = None, sonst "rot".
    """
    import re as _re
    # Auflage 2196: nach apply_and_recheck hat
    # basis_protokoll_nach_apply die aktuellen Werte.
    basis = (
        state.basis_protokoll_nach_apply
        or state.basis_protokoll
        or ""
    )

    # Pro Messung: (mid, rc, stdout)
    # Auflage 2198: test_count nutzt seit 2176 das Format
    # STDOUT (letzte Zeile). Der Zusatz ist optional.
    treffer = _re.findall(
        r"=== (\w+) ===\nARGV: [^\n]*\nRC: (\d+)\n"
        r"STDOUT(?: \(letzte Zeile\))?:\n(.*?)STDERR:",
        basis, _re.DOTALL,
    )
    werte: dict[str, Any] = {
        "test_anzahl": None,
        "ruff": "rot",
        "mypy": "rot",
        "py_compile": "rot",
        "git_status": "geaendert",
        "git_head": "",
        "verstrichene_zeit_s": 0.0,
    }
    for mid, rc_str, stdout in treffer:
        rc = int(rc_str)
        if mid == "test_count":
            m = re.search(r"(\d+) tests? collected", stdout)
            if m:
                werte["test_anzahl"] = int(m.group(1))
        elif mid == "ruff":
            werte["ruff"] = "gruen" if rc == 0 else "rot"
        elif mid == "mypy":
            werte["mypy"] = "gruen" if rc == 0 else "rot"
        elif mid == "py_compile":
            werte["py_compile"] = "gruen" if rc == 0 else "rot"
        elif mid == "git_status":
            werte["git_status"] = ("clean"
                                   if stdout.strip() == ""
                                   else "geaendert")
        elif mid == "git_head":
            werte["git_head"] = stdout.strip()

    # F3-Fix (2026-10-16): git_head-Fallback.
    # apply_and_recheck ueberspringt git_head;
    # basis_protokoll_nach_apply enthaelt es nicht.
    # Fallback auf basis_protokoll.
    if not werte.get("git_head"):
        _protokolle = [
            state.basis_protokoll_nach_apply,
            state.basis_protokoll,
        ]
        for _prot in _protokolle:
            if not _prot:
                continue
            for _m in _re.finditer(
                    r"=== (\w+) ===\nARGV: [^\n]*\nRC: \d+\n"
                    r"STDOUT(?: \(letzte Zeile\))?:\n(.*?)STDERR:",
                    _prot, _re.DOTALL):
                if _m.group(1) == "git_head":
                    werte["git_head"] = _m.group(2).strip()
                    break
            if werte.get("git_head"):
                break

    # Verstrichene Zeit aus start_monotonic
    if state.start_monotonic > 0:
        werte["verstrichene_zeit_s"] = (
            time.monotonic() - state.start_monotonic)

    return werte


def format_messwerte_block(werte: dict[str, Any]) -> str:
    """Formatiert die Messwerte fuer den Builder-Prompt.

    Auflage 2135: Der Builder verwendet diese Werte woertlich.
    """
    test_anzahl = werte.get("test_anzahl")
    test_str = str(test_anzahl) if test_anzahl is not None else "nicht gemessen"
    return (
        "MESSWERTE (von der Werkstatt gemessen, nicht schaetzen):\n"
        f"  test_anzahl: {test_str}\n"
        f"  ruff: {werte.get('ruff', 'rot')}\n"
        f"  mypy: {werte.get('mypy', 'rot')}\n"
        f"  py_compile: {werte.get('py_compile', 'rot')}\n"
        f"  git_status: {werte.get('git_status', 'geaendert')}\n"
        f"  git_head: {werte.get('git_head', '')}\n"
        f"  verstrichene_zeit_s: {werte.get('verstrichene_zeit_s', 0.0):.0f}"
    )


