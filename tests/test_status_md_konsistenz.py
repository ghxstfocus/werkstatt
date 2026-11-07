"""STATUS.md / PROGRESS.md — Konsistenz-Guard (OP 2026-11-07).

Anlass: OP-178 wurde aus STATUS.md entfernt, aber nicht in die
Delete-Zone eingetragen — der Commit ging durch, weil der
Pre-Commit-Check nur pytest/audit/control prueft, keine
Doku-Konsistenz. Drei Regeln:

1. Jede offene OP hat ein **Status:**-Feld im Body.
2. Keine OP ist gleichzeitig offen und in der Delete-Zone.
3. Jede OP-NNN in einem PROGRESS.md-###-Header ist entweder
   offen oder in der Delete-Zone.

Die Regex fuer Regel 3 ist bewusst robust: `OP-NNN:` und
`OP-NNN abgeschlossen:` und `OP-NNN — ...` werden alle erkannt.
Ohne diese Robustheit waere der OP-178-Verlust heute nicht
erkannt worden.
"""
from __future__ import annotations

import pathlib
import re

STATUS = pathlib.Path("/opt/werkstatt/docs/STATUS.md")
PROGRESS = pathlib.Path("/opt/werkstatt/PROGRESS.md")

# Regex-Objekte (modulweit, damit die Test-Funktionen sie nutzen).
RE_OFFENE_OP = re.compile(r"^### (OP-\d+[a-z]?):", re.MULTILINE)
RE_DELETE_ZONE_ENTRY = re.compile(
    r"^- \d{4}-\d{2}-\d{2} \| (OP-\d+[a-z]?) \|", re.MULTILINE)
# Robust: nach OP-NNN darf `:` oder ein Wort oder Zeilenende kommen.
RE_PROGRESS_HEADER_OP = re.compile(
    r"^### \d{4}-\d{2}-\d{2} — (OP-\d+[a-z]?)\b", re.MULTILINE)
RE_STATUS_FELD = re.compile(r"\*\*Status:\*\*")


def _lies(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _offene_ops(status_md: str) -> set[str]:
    return set(RE_OFFENE_OP.findall(status_md))


def _delete_zone_ops(status_md: str) -> set[str]:
    dz_start = status_md.find("## Delete-Zone")
    if dz_start < 0:
        return set()
    return set(RE_DELETE_ZONE_ENTRY.findall(status_md[dz_start:]))


def _progress_header_ops(progress_md: str) -> set[str]:
    return set(RE_PROGRESS_HEADER_OP.findall(progress_md))


# =====================================================================
# Regel 1: Jede offene OP hat ein **Status:**-Feld
# =====================================================================

def test_jede_offene_op_hat_status_feld():
    """Spec: ohne Status-Feld ist eine OP nicht bearbeitbar.

    Der Loop liest **Status:** um zu entscheiden, ob er die OP
    aufgreift. Fehlt das Feld, laeuft die OP stumm an.
    """
    src = _lies(STATUS)
    # In Abschnitte aufteilen: jeder OP-Block endet vor der naechsten
    # ### oder ##-Zeile.
    sektionen = re.split(r"^### (OP-\d+[a-z]?):", src, flags=re.MULTILINE)
    ohne_status: list[str] = []
    for i in range(1, len(sektionen), 2):
        op_id = sektionen[i]
        body = sektionen[i + 1] if i + 1 < len(sektionen) else ""
        m = re.search(r"\n(?=##? )", body)
        block = body[:m.start()] if m else body
        if not RE_STATUS_FELD.search(block):
            ohne_status.append(op_id)
    assert not ohne_status, (
        f"OPs ohne **Status:**-Feld: {sorted(ohne_status)}"
    )


# =====================================================================
# Regel 2: Keine OP doppelt (offen + Delete-Zone)
# =====================================================================

def test_keine_op_gleichzeitig_offen_und_geloescht():
    """Spec: eine OP ist entweder offen oder geloescht, nie beides.

    Duplikate verwirren den Loop — er wuerde die OP aufgreifen,
    obwohl sie in der Delete-Zone als done steht.
    """
    src = _lies(STATUS)
    beide = _offene_ops(src) & _delete_zone_ops(src)
    assert not beide, (
        f"OPs gleichzeitig offen und in Delete-Zone: {sorted(beide)}"
    )


# =====================================================================
# Regel 3: PROGRESS-Header-OPs sind offen oder in Delete-Zone
# =====================================================================

def test_progress_erwaehnte_ops_sind_dokumentiert():
    """Spec: PROGRESS.md-###-Header mit OP-NNN verspricht eine
    abgeschlossene OP. Sie MUSS in STATUS.md stehen — entweder
    noch offen oder in der Delete-Zone.

    Diese Regel faengt den OP-178-Fall: Header in PROGRESS.md,
    OP aus STATUS.md entfernt, Delete-Zone-Eintrag vergessen.
    """
    status = _lies(STATUS)
    progress = _lies(PROGRESS)
    offen = _offene_ops(status)
    dz = _delete_zone_ops(status)
    prog_ops = _progress_header_ops(progress)
    luecken = prog_ops - offen - dz
    assert not luecken, (
        f"OPs in PROGRESS.md-Header, aber weder offen noch Delete-Zone: "
        f"{sorted(luecken)}. "
        f"Vermutlich aus STATUS.md geloescht ohne Delete-Zone-Eintrag."
    )


# =====================================================================
# Regel 4: OP-IDs im PROGRESS.md sind wohlgeformt (keine Tippfehler)
# =====================================================================

def test_progress_header_op_ids_wohlgeformt():
    """Spec: kein `OP-17b` oder `OP-1O8` als Tippfehler.

    Die Regex prueft `OP-<digits><optionaler Kleinbuchstabe>`.
    Tippfehler wie `OP-l78` (kleines L statt 1) entstehen bei
    Copy-Paste und brechen die Verlinkung zu STATUS.md.
    """
    progress = _lies(PROGRESS)
    # Alle Header-OP-IDs muessen dem Muster entsprechen.
    header_op_ids = re.findall(
        r"^### \d{4}-\d{2}-\d{2} — (OP-\S+)",
        progress, re.MULTILINE,
    )
    falsch = [x for x in header_op_ids
              if not re.fullmatch(r"OP-\d+[a-z]?", x.rstrip(":"))]
    assert not falsch, (
        f"Unwohlgeformte OP-IDs im PROGRESS.md: {falsch}"
    )


# =====================================================================
# Regel 5: Keine OP doppelt in Delete-Zone
# =====================================================================

def test_keine_op_doppelt_in_delete_zone():
    """Spec: jede OP erscheint hoechstens einmal in der Delete-Zone.

    Anlass (2026-11-07): OP-179 wurde durch einen fehlerhaften Patch
    doppelt eingefuegt — der Guard-Test hat es nicht gefangen, weil
    Regel 2 nur "offen UND Delete-Zone" prueft, nicht "2x Delete-Zone".
    """
    import collections
    src = _lies(STATUS)
    dz_ops = list(RE_DELETE_ZONE_ENTRY.findall(src))
    cnt = collections.Counter(dz_ops)
    doppelt = [op for op, n in cnt.items() if n > 1]
    assert not doppelt, (
        f"OPs doppelt in Delete-Zone: {doppelt}. "
        f"Jede OP darf nur einen Eintrag haben."
    )
