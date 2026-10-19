"""Patch-Anwendung (Phase 2 / Gate 18, 2026-10-19).

Aus pipeline.py extrahiert (Reviewer-Gate 18 /
apply.py: A). Enthaelt:
- apply_code_patches (361 Z.)
- _shift_lines (13 Z.) — Einrueckungs-Normalisierung.

Ausnahme von der 300er-Grenze (Reviewer P-2):
apply_code_patches ist EINE Funktion mit 361 Z.,
Verhalten 1:1. Zerlegung gehoert in Phase 3b
(Loop-Umbau), wenn die Deadlock-Kette angefasst
wird.

Konsumenten:
- pipeline.py (Loop-Kontext, 2x apply_code_patches).
- pruefe_anker_gegen_messung in pipeline.py ruft
  _shift_lines (importiert aus apply.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from werkstatt.audit import audit

if TYPE_CHECKING:
    from werkstatt.state import RunState


def _shift_lines(text: str, prefix: str = "  ") -> str:
    """Auflage 2165: ergaenzt jede nicht-leere Zeile um prefix.

    Wird fuer die Einrueckungs-Normalisierung verwendet:
    Der Builder liefert Anker/Ersatz oft um 2 Spaces
    zu kurz. Wenn der Anker nur in der +2-Variante
    genau 1x matcht, korrigieren wir.
    """
    zeilen = text.split("\n")
    return "\n".join(
        (prefix + z) if z else z for z in zeilen
    )


def apply_code_patches(state: RunState,
                       patches: list[dict[str, str]],
                       dry_run: bool = False) -> bool:
    """UMB-1a: wendet Code-Patches an (In-Memory-Rollback).

    Pruefungen pro Patch:
      - pfad in state.file_whitelist
      - Datei existiert
      - pfad nicht doppelt in patches
      - Anker count == 1

    Bei dry_run: nur pruefen, nichts schreiben.

    Bei Fehler: nichts wurde geschrieben, return False.
    Wenn spaeter etwas fehlschlaegt (theoretisch nicht
    nach Vollvalidierung): In-Memory-Rollback.
    """
    # ---- Phase 1: Validierung ----
    if not patches:
        print("[!] apply_code_patches: keine Patches.")
        return False
    # Auflage 2173: Doppel-Pruefung auf (Pfad, Anker),
    # nicht nur Pfad. Mehrere Patches pro Datei sind
    # legitim, solange Anker unterschiedlich.
    gesehen: set[tuple[Path, str]] = set()
    original: dict[Path, str] = {}
    plan: list[dict[str, Any]] = []
    # P2b-Luecke-A / A3: Konflikt-Pruefung VOR Anwenden.
    # Sammle alle Pfade, pruefe new_file-Konflikte.
    neue_pfade: set[str] = set()
    patch_pfade: set[str] = set()
    # W59 (2026-10-18): Read-vor-Edit. Jeder Pfad
    # (typ=patch) muss vor dem Patch in
    # state.gelesene_dateien stehen. mtime muss
    # uebereinstimmen. Sonst fail-closed.
    for p in patches:
        typ = p.get("typ", "patch")
        pfad = p.get("pfad", "")
        if typ == "new_file" or not pfad:
            continue
        if pfad not in state.gelesene_dateien:
            print(f"[!] apply_code_patches: {pfad} "
                  f"nicht gemessen. Fail closed (W59).")
            audit("patch_ohne_messung",
                  {"pfad": pfad},
                  state.project_dir, state.project_name)
            return False
        _ziel = state.project_dir / pfad
        try:
            _mtime_ist = _ziel.stat().st_mtime
        except OSError:
            _mtime_ist = 0.0
        _mtime_soll = state.gelesene_dateien[pfad]
        if abs(_mtime_ist - _mtime_soll) > 1e-6:
            print(f"[!] apply_code_patches: {pfad} "
                  f"seit Messung geaendert. Fail closed (W59).")
            audit("patch_datei_geaendert_seit_messung",
                  {"pfad": pfad,
                   "mtime_ist": _mtime_ist,
                   "mtime_soll": _mtime_soll},
                  state.project_dir, state.project_name)
            return False
    for p in patches:
        typ = p.get("typ", "patch")
        pfad = p.get("pfad", "")
        if not pfad:
            print("[!] apply_code_patches: Patch ohne pfad.")
            return False
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] apply_code_patches: Pfad nicht in "
                  f"Whitelist: {pfad}")
            return False
        if typ == "new_file":
            if pfad in neue_pfade or pfad in patch_pfade:
                print(f"[!] apply_code_patches: Konflikt "
                      f"(new_file) auf {pfad}.")
                return False
            neue_pfade.add(pfad)
        else:
            if pfad in neue_pfade:
                print(f"[!] apply_code_patches: Konflikt "
                      f"(patch nach new_file) auf {pfad}.")
                return False
            patch_pfade.add(pfad)
        ziel = state.project_dir / pfad
        # P2b-Luecke-A: Weiche typ.
        if typ == "new_file":
            if ziel.exists():
                # W43 (2026-10-17): new_file-Idempotenz.
                # Datei existiert bereits. Wenn Inhalt
                # gleich: skip (bereits angewendet).
                # Wenn Inhalt anders: echter Konflikt.
                _soll_inhalt = p.get("inhalt", "")
                try:
                    _ist_inhalt = ziel.read_text(
                        encoding="utf-8")
                except OSError:
                    _ist_inhalt = None
                if _ist_inhalt == _soll_inhalt:
                    audit("patch_bereits_angewendet",
                          {"pfad": pfad,
                           "typ": "new_file",
                           "len": len(_soll_inhalt)},
                          state.project_dir, state.project_name)
                    print(f"[i] apply_code_patches: "
                          f"new_file bereits angewendet: "
                          f"{pfad}")
                    continue
                print(f"[!] apply_code_patches: new_file "
                      f"auf existierende Datei (Inhalt "
                      f"abweichend): {pfad}")
                audit("patch_konflikt_new_file",
                      {"pfad": pfad},
                      state.project_dir, state.project_name)
                return False
            plan.append({"typ": "new_file",
                         "ziel": ziel,
                         "inhalt": p.get("inhalt", "")})
            continue
        anker = p.get("anker", "")
        ersatz = p.get("ersatz", "")
        if not ziel.exists():
            print(f"[!] apply_code_patches: Datei fehlt: {pfad}")
            return False
        if (ziel, anker) in gesehen:
            print(f"[!] apply_code_patches: Patch "
                  f"(pfad, anker) doppelt: {pfad}")
            return False
        gesehen.add((ziel, anker))
        inhalt = ziel.read_text(encoding="utf-8")
        count = inhalt.count(anker)
        # Auflage 2161: Pruefe Zeilen-Anfang.
        am_anfang = (
            inhalt.startswith(anker)
            or ("\n" + anker) in inhalt
        )
        # Auflage 2165: Einrueckungs-Normalisierung.
        # Der Builder liefert Anker/Ersatz oft um 2 Spaces
        # zu kurz. Korrektur, wenn:
        #   - count != 1 (kein exakter Match), ODER
        #   - nicht am Zeilen-Anfang (Substring-Match).
        # UND die +2-Variante genau 1x am Zeilen-Anfang
        # matcht.
        if count != 1 or not am_anfang:
            anker_plus = _shift_lines(anker, "  ")
            plus_count = inhalt.count(anker_plus)
            plus_am_anfang = (
                inhalt.startswith(anker_plus)
                or ("\n" + anker_plus) in inhalt
            )
            if plus_count == 1 and plus_am_anfang:
                print(f"[i] apply_code_patches: Anker in {pfad} "
                      f"um 2 Spaces verschoben. Korrigiere.")
                audit("anker_einrueckung_korrigiert",
                      {"pfad": pfad}, state.project_dir,
                      state.project_name)
                anker = anker_plus
                ersatz = _shift_lines(ersatz, "  ")
                p["anker"] = anker
                p["ersatz"] = ersatz
                count = 1
                am_anfang = True
        # W24a (2026-10-17): Idempotenz in Phase 1.
        # Wenn anker nicht da ist (count == 0), aber ersatz
        # schon im Datei-Inhalt: Patch bereits angewendet.
        _aktuell_phase1 = (
            ziel.read_text(encoding="utf-8")
            if ziel.exists() else "")
        if count == 0 and ersatz in _aktuell_phase1:
            audit("patch_bereits_angewendet",
                  {"pfad": str(ziel.relative_to(
                      state.project_dir)),
                   "anker_len": len(anker)},
                  state.project_dir, state.project_name)
            print(f"[i] apply_code_patches: Patch bereits "
                  f"angewendet in "
                  f"{ziel.relative_to(state.project_dir)}.")
            continue
        if count != 1:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"kommt {count}x vor. Erwartet 1x.")
            return False
        if not am_anfang:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"steht nicht am Zeilen-Anfang. Fail closed.")
            return False
        original[ziel] = inhalt
        plan.append({"typ": "patch",
                     "ziel": ziel,
                     "anker": anker,
                     "ersatz": ersatz})

    if dry_run:
        print(f"[i] apply_code_patches (dry_run): "
              f"{len(plan)} Patches validiert.")
        return True

    # ---- Phase 2: Anwendung ----
    # Auflage 2173: bei mehreren Patches pro Datei
    # muss jede Iteration den AKTUELLEN Stand lesen,
    # nicht den Urzustand. Sonst ueberschreibt der
    # zweite Patch den ersten.
    geschrieben: list[Path] = []
    # P2b-Luecke-A: neue Dateien separat merken, damit
    # der Rollback sie loeschen kann (nicht zurueckschreiben).
    neue_dateien: list[Path] = []
    try:
        for eintrag in plan:
            ziel = eintrag["ziel"]
            if eintrag["typ"] == "new_file":
                ziel.parent.mkdir(parents=True, exist_ok=True)
                ziel.write_text(eintrag["inhalt"],
                                encoding="utf-8")
                # W59 (2026-10-18, A-W59-3): mtime
                # nach dem Schreiben aktualisieren,
                # damit weitere Patches an derselben
                # Datei nicht blockieren.
                try:
                    _rel = str(ziel.relative_to(
                        state.project_dir))
                    state.gelesene_dateien[_rel] = \
                        ziel.stat().st_mtime
                except (OSError, ValueError):
                    pass
                neue_dateien.append(ziel)
                print(f"[+] Neue Datei: "
                      f"{ziel.relative_to(state.project_dir)}")
                audit("code_patches_new_file",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "zeilen":
                           eintrag["inhalt"].count("\n") + 1},
                      state.project_dir, state.project_name)
                continue
            # patch (alt).
            anker = eintrag["anker"]
            ersatz = eintrag["ersatz"]
            aktuell = ziel.read_text(encoding="utf-8")
            # W24a (2026-10-17): Idempotenz-Check.
            # Verhindert doppelte Anwendung desselben Patches.
            _hat_ersatz = ersatz in aktuell
            _hat_anker = anker in aktuell
            if _hat_ersatz and not _hat_anker:
                # Patch bereits angewendet.
                audit("patch_bereits_angewendet",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "anker_len": len(anker)},
                      state.project_dir, state.project_name)
                print(f"[i] Patch bereits angewendet: "
                      f"{ziel.relative_to(state.project_dir)}")
                geschrieben.append(ziel)
                continue
            # Ambig nur, wenn WEDER anker in ersatz
            # (Erweiterung) NOCH ersatz in anker (Entfernung).
            # W35a-2d-6 (2026-10-17): Praefix-Faelle.
            if (_hat_ersatz and _hat_anker
                    and anker not in ersatz
                    and ersatz not in anker):
                # Echter Ambig-Fall.
                print(f"[FAIL] Patch ambig: anker und "
                      f"ersatz beide in "
                      f"{ziel.relative_to(state.project_dir)}.")
                audit("patch_ambig",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "anker_len": len(anker),
                       "ersatz_len": len(ersatz)},
                      state.project_dir, state.project_name)
                return False
            if not _hat_anker:
                # Weder anker noch ersatz: Datei extern
                # geaendert. Fail-closed.
                print(f"[FAIL] Anker fehlt in "
                      f"{ziel.relative_to(state.project_dir)}.")
                audit("patch_anker_fehlt",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "anker_len": len(anker)},
                      state.project_dir, state.project_name)
                return False
            neu = aktuell.replace(anker, ersatz, 1)
            # W54-g (2026-10-18): Ersatz-Duplikat
            # pruefen. Bug 20261018-014952:
            # Builder lieferte Patch mit doppeltem
            # Import im Ersatz. patch_ambig und
            # W54-b fingen das nicht.
            # A-W54g-6: Reihenfolge (c) vor (a),
            # je ein Audit mit grund-Feld.
            _anker_stripped = anker.strip()
            # (c) Anker 2x im Ersatz (A-W54g-5:
            # nur bei Anker >= 10 Zeichen).
            if (len(_anker_stripped) >= 10
                    and ersatz.count(_anker_stripped) >= 2):
                print(f"[FAIL] apply_code_patches: "
                      f"Anker {pfad} 2x im Ersatz.")
                audit("patch_ersatz_doppelte_zeilen",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "grund": "anker_doppelt",
                       "anker_count": ersatz.count(
                           _anker_stripped),
                       "anker_len": len(_anker_stripped)},
                      state.project_dir, state.project_name)
                return False
            # (a) Lange Zeile (>= 40 Zeichen) 2x im
            # Ersatz (sekundaere Heuristik).
            # W61: Schwelle 50 statt 40. Kurze legitime
            # Assertions (z.B. 42 Zeichen) in verschiedenen
            # Test-Methoden sind kein Duplikat. Echte
            # Duplikate (Imports, lange Code-Zeilen) bleiben.
            _ersatz_zeilen = [
                z.strip() for z in ersatz.splitlines()
                if len(z.strip()) >= 50]
            if len(_ersatz_zeilen) != len(
                    set(_ersatz_zeilen)):
                print(f"[FAIL] apply_code_patches: "
                      f"Lange Zeile 2x im Ersatz: "
                      f"{pfad}")
                audit("patch_ersatz_doppelte_zeilen",
                      {"pfad": str(ziel.relative_to(
                          state.project_dir)),
                       "grund": "lange_zeile_doppelt",
                       "anzahl_zeilen": len(
                           _ersatz_zeilen),
                       "anzahl_eindeutig": len(set(
                           _ersatz_zeilen))},
                      state.project_dir, state.project_name)
                return False
            ziel.write_text(neu, encoding="utf-8")
            # W59 (2026-10-18, A-W59-3): mtime
            # nach dem Schreiben aktualisieren.
            try:
                _rel = str(ziel.relative_to(
                    state.project_dir))
                state.gelesene_dateien[_rel] = \
                    ziel.stat().st_mtime
            except (OSError, ValueError):
                pass
            geschrieben.append(ziel)
            print(f"[+] Code gepatcht: "
                  f"{ziel.relative_to(state.project_dir)}")
    except OSError as exc:
        print(f"[!] apply_code_patches: Schreibfehler: {exc}")
        # Rollback: neue Dateien loeschen, alte zurueck.
        for ziel in neue_dateien:
            try:
                ziel.unlink()
            except OSError as exc2:
                print(f"[!] Rollback (unlink) fehlgeschlagen "
                      f"fuer {ziel}: {exc2}")
        for ziel in geschrieben:
            try:
                ziel.write_text(original[ziel], encoding="utf-8")
            except OSError as exc2:
                print(f"[!] Rollback fehlgeschlagen fuer {ziel}: {exc2}")
        return False

    return True


