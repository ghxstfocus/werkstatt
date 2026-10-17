"""Werkstatt: Parser-Funktionen.

W36-2a (2026-10-17): Extrahiert aus pipeline.py.
"""
from __future__ import annotations

import re as _re_w35a2c
from typing import Any

_ID_MUSTER = _re_w35a2c.compile(r"^U[A-Za-z0-9]+$")


def _parse_phase_kopf(text: str) -> tuple[str, str]:
    """Parst den PHASE-Kopf (Stufe 2).

    Rueckgabe: (phase_id, phase_titel).

    Fehler immer als ValueError mit klarer Regel.

    Auflage P2a-S5a-A5: z.strip() beim Erkennen
    toleriert fuehrende Whitespaces vor "PHASE:"
    (LLM-Replies mit Einrueckung).
    Auflage P2a-S5a-A6: split(" - ", 1) — maxsplit=1,
    damit ein Titel, der " - " enthaelt, nicht
    zerfaellt.
    """
    zeilen = text.splitlines()
    kopf_idx: int | None = None
    for i, z in enumerate(zeilen):
        if z.strip().startswith("PHASE:"):
            kopf_idx = i
            break
    if kopf_idx is None:
        raise ValueError("kein PHASE:-Kopf gefunden")
    kopf = zeilen[kopf_idx].strip()[len("PHASE:"):].strip()
    if " - " not in kopf:
        raise ValueError("Phase: Trenner '-' fehlt")
    phase_id, phase_titel = kopf.split(" - ", 1)
    if not phase_id.strip():
        raise ValueError("Phase: id leer nach strip()")
    if not phase_titel.strip():
        raise ValueError("Phase: titel leer nach strip()")
    return phase_id.strip(), phase_titel.strip()




def _parse_phase_plan(text: str) -> list[dict[str, Any]]:
    """Parst einen Phasentext in Unterbloecke.

    Eingabeformat (verbindlich):
      PHASE: <id> - <Titel>
      UNTERBLOCK: U1 - <Titel>
      Unterpunkte:
        - <Punkt>
        - <Punkt>
      Geschaetzte Runden: 2

    Rueckgabe: Liste von dicts, je Eintrag:
      {"id": "U1", "titel": "...",
       "unterpunkte": ["...", "..."],
       "geschaetzte_runden": 2}

    Der PHASE-Kopf wird validiert, aber NICHT zurueckgegeben
    (Auflage P2a-S2-A1). Den PHASE-Kopf liest der Aufrufer
    separat.

    Fehler immer als ValueError mit Regel + id/Position.
    """
    # PHASE-Kopf validieren ueber _parse_phase_kopf
    # (Auflage P2a-S5a-A9: ohne Zuweisung, damit
    # keine unbenutzten Variablen entstehen).
    _parse_phase_kopf(text)
    zeilen = text.splitlines()
    # Zweiter splitlines() bewusst: _parse_phase_kopf
    # gibt die Position nicht zurueck (P2a-S5a-A1).
    # Text ist kurz (<100 Zeilen).
    kopf_idx = next(
        i for i, z in enumerate(zeilen)
        if z.strip().startswith("PHASE:")
    )

    # 2. Unterbloecke ab kopf_idx+1 sammeln.
    unterbloecke: list[dict[str, Any]] = []
    i = kopf_idx + 1
    pos = 0
    while i < len(zeilen):
        roh = zeilen[i]
        stripped = roh.strip()
        if not stripped:
            i += 1
            continue
        if not stripped.startswith("UNTERBLOCK"):
            i += 1
            continue
        pos += 1
        # Kopf ungueltig, wenn nicht exakt "UNTERBLOCK: U<n> - <Titel>"
        if not stripped.startswith("UNTERBLOCK:"):
            raise ValueError(
                f"Unterblock {pos} (Zeile {i+1}): Kopf ungueltig: "
                f"{roh!r}")
        rest = stripped[len("UNTERBLOCK:"):].strip()
        if " - " not in rest:
            raise ValueError(
                f"Unterblock {pos} (Zeile {i+1}): Kopf ungueltig: "
                f"{roh!r}")
        id_teil, titel_teil = rest.split(" - ", 1)
        id_roh = id_teil.strip()
        titel_roh = titel_teil.strip()
        # W35a-2c (2026-10-17): Suffix-IDs zulassen
        # (U2a1, U2b, U3, ...). Nur Grundform pruefen:
        # beginnt mit U, danach alphanumerisch, nicht
        # leer.
        if not _ID_MUSTER.match(id_roh):
            raise ValueError(
                f"Unterblock {pos}: id ungueltig: "
                f"{id_roh!r}")
        # Eindeutigkeit pruefen.
        if any(u.get("id") == id_roh for u in unterbloecke):
            raise ValueError(
                f"Unterblock {pos}: id doppelt: {id_roh!r}")
        if not titel_roh:
            raise ValueError(f"U{pos}: titel leer nach strip()")

        # Sektion Unterpunkte.
        i += 1
        while i < len(zeilen) and not zeilen[i].strip():
            i += 1
        if i >= len(zeilen) or \
                zeilen[i].strip() != "Unterpunkte:":
            raise ValueError(
                f"U{pos}: Reihenfolge Unterpunkte/Runden verletzt")
        i += 1
        unterpunkte: list[str] = []
        while i < len(zeilen):
            zp = zeilen[i]
            sp = zp.strip()
            if not sp:
                i += 1
                continue
            if sp.startswith("- "):
                punkt = sp[len("- "):].strip()
                if not punkt:
                    raise ValueError(
                        f"U{pos}: unterpunkt leer nach strip()")
                unterpunkte.append(punkt)
                i += 1
                continue
            if sp.startswith("Geschaetzte Runden:"):
                break
            # Fremdzeile zwischen Sektionen.
            raise ValueError(
                f"U{pos}: Reihenfolge Unterpunkte/Runden verletzt")
        if not unterpunkte:
            raise ValueError(f"U{pos}: unterpunkte fehlen")

        # Sektion Geschaetzte Runden.
        while i < len(zeilen) and not zeilen[i].strip():
            i += 1
        if i >= len(zeilen) or \
                not zeilen[i].strip().startswith("Geschaetzte Runden:"):
            raise ValueError(f"U{pos}: geschaetzte_runden fehlt")
        runden_roh = zeilen[i].strip()[len("Geschaetzte Runden:"):].strip()
        try:
            n = int(runden_roh)
        except ValueError as exc:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}") from exc
        if str(n) != runden_roh:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}")
        if type(n) is not int or n < 1:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}")
        i += 1

        unterbloecke.append({
            "id": id_roh,
            "titel": titel_roh,
            "unterpunkte": unterpunkte,
            "geschaetzte_runden": n,
        })

    if not unterbloecke:
        raise ValueError("Phase: kein Unterblock gefunden")
    if len(unterbloecke) > 20:
        raise ValueError(
            f"{len(unterbloecke)} Unterbloecke: "
            "Obergrenze 20 ueberschritten")
    return unterbloecke




