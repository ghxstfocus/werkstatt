"""W48-A16-b (2026-10-18): Katalog-Nutzungs-Test.

Prueft alle audit("...")-Aufrufe in pipeline.py
gegen _AUDIT_KINDS_BEKANNT.

AST-Grenzen (siehe audit/00-audit-grenzen.md):
  Erkannt:
    - ast.Call mit ast.Name="audit", erstes
      Argument ast.Constant (Literal).
    - ast.Call mit ast.Name="audit", erstes
      Argument ast.JoinedStr (f-String,
      dynamisch).
  NICHT erkannt:
    - ast.Attribute: pipeline.audit(...)
      (heute 0 Treffer, test_audit_kinds_kein_
      attribute_aufruf prueft das).
    - Alias-Import: from x import audit as y.
    - getattr-Dispatch: getattr(pipeline, "audit").
    - Dynamische Kinds ohne f-String:
      kind = "x"; audit(kind, ...).

Dynamische Kinds (f-String) werden gegen eine
Whitelist erlaubter Praefixe geprueft. Heute:
  builder_deadlock_ (Werte aus klassifiziere_
  deadlock: anker_nicht_gemessen, rueckfrage,
  leer).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pipeline

PIPELINE = Path("/opt/werkstatt/pipeline.py")
# 18e (2026-10-19): audit() liegt seit Phase 2 in
# werkstatt/audit.py. AST-Test muss beide Dateien
# walken.
AUDIT_MODUL = Path("/opt/werkstatt/werkstatt/audit.py")

# Erlaubte dynamische Praefixe. Neue MUESSEN
# hier eingetragen werden.
DYNAMISCHE_PRAEFIXE = ("builder_deadlock_",)

# Erlaubte dynamische Werte pro Praefix
# (aufgeloest aus klassifiziere_deadlock).
DYNAMISCHE_WERTE = {
    "builder_deadlock_": {
        "anker_nicht_gemessen",
        "rueckfrage",
        "leer",
    },
}


def _audit_calls(tree: ast.Module) -> list[dict]:
    """Sammelt alle ast.Call mit ast.Name='audit'."""
    treffer: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name)
                and node.func.id == "audit"):
            continue
        if not node.args:
            treffer.append({
                "zeile": node.lineno,
                "art": "kein_argument",
                "kind": None,
            })
            continue
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant):
            treffer.append({
                "zeile": node.lineno,
                "art": "literal",
                "kind": arg0.value,
            })
        elif isinstance(arg0, ast.JoinedStr):
            treffer.append({
                "zeile": node.lineno,
                "art": "fstring",
                "kind": None,
            })
        else:
            treffer.append({
                "zeile": node.lineno,
                "art": "sonstig",
                "kind": None,
            })
    return treffer


def _baum() -> ast.Module:
    return ast.parse(PIPELINE.read_text(encoding="utf-8"))


def _baeume() -> list[tuple[str, ast.Module]]:
    """18e: parst alle Dateien mit audit()-Aufrufen.

    pipeline.py (Hauptcode) + werkstatt/audit.py (Modul
    seit Phase 2). Liefert Liste (dateiname, ast.Module).
    """
    dateien = [("pipeline.py", PIPELINE)]
    if AUDIT_MODUL.exists():
        dateien.append(("werkstatt/audit.py", AUDIT_MODUL))
    return [
        (name, ast.parse(pfad.read_text(encoding="utf-8")))
        for name, pfad in dateien
    ]


# W48-A16-b-2 (2026-10-18): 36 Kinds registriert.
# Der Test ist scharf (kein xfail mehr).
#
# Herkunft: W48-A16-b (a074be1) hat 35 audit()-
# Aufrufe mit nicht registrierten Kinds aufgedeckt
# (AST-Walk, 35 distinkte Kinds, 48 Calls).
# W48-A16-b-2 registriert 35 + judge_call_failed
# (Umbenennung reviewer_call_failed Z. 9503
# -> judge_call_failed; reviewer_call_failed
# bleibt fuer Z. 9255).
#
# Katalog 122 -> 162. _KATALOG_SOLL = 162.
#
# Dynamische Kinds (nicht per AST-Walk pruefbar,
# daher in test_audit_dynamische_werte_aufgeloest
# separat geprueft):
#   builder_deadlock_* (3 Werte)
#
# Kinds mit dynamischem Aufruf, aber AST-Walk
# sieht sie nicht (Variable als erstes Argument):
#   planner_new_file_auf_existierend (Z. 11954)
#   planner_pfad_ausserhalb_projekt (Z. 11956)
#   planner_phase_zu_gross (Z. 11974)
#   llm_timeout_connect
# Diese 4 sind im Katalog, aber der AST-Test
# findet sie nicht. Bekannte Grenze.
#
# Die 36 neuen Kinds (alphabetisch):
#   aggregator_failed, anti_patterns_injiziert,
#   auto_repair_ruff, basis_gate_test_result,
#   builder_call_failed, builder_commit_paket_failed,
#   builder_commit_paket_failed_retry,
#   commit_review_ohne_messung, judge_call_failed,
#   memory_yaml_korrupt, mess_nach_nahe_budget,
#   phase_basis_gate_failed, phase_suite_rot_recovery,
#   phasen_basis_gate_untracked, pipeline_abgebrochen,
#   pipeline_escalated, planner_abgebrochen,
#   planner_basis_gate_failed, planner_bestaetigt,
#   planner_call_failed, planner_phase_yaml_kaputt,
#   planner_rolle_fehlt, planner_start,
#   planner_uebersprungen, planner_ungueltig,
#   planner_verworfen, quelle_invalid, recovery_budget,
#   review_command, reviewer_call_failed,
#   reviewer_run_solver_phase2_ignoriert,
#   solver_budget_exhausted, solver_max_runden_erreicht,
#   solver_trigger_a, solver_trigger_b.
def test_audit_kinds_alle_aufrufe_registriert() -> None:
    """Jeder audit('literal', ...) ist im Katalog.

    18e: walkt pipeline.py UND werkstatt/audit.py.
    """
    literale = []
    for dateiname, baum in _baeume():
        calls = _audit_calls(baum)
        for c in calls:
            if c["art"] == "literal":
                c["datei"] = dateiname
                literale.append(c)
    assert literale, "keine audit()-Aufrufe gefunden"
    fehlend = [
        c for c in literale
        if c["kind"] not in pipeline._AUDIT_KINDS_BEKANNT
    ]
    assert not fehlend, (
        "audit()-Aufrufe mit nicht registriertem Kind:\n"
        + "\n".join(
            f"  {c['datei']} Z. {c['zeile']}: {c['kind']!r}"
            for c in fehlend
        )
    )


def test_audit_kind_nicht_registriert_wird_erkannt() -> None:
    """Synthetisch: unbekanntes Kind wird erkannt."""
    quelle = 'audit("gibt_es_nicht", {}, None, None)\n'
    tree = ast.parse(quelle)
    calls = _audit_calls(tree)
    assert len(calls) == 1
    assert calls[0]["art"] == "literal"
    assert calls[0]["kind"] == "gibt_es_nicht"
    assert calls[0]["kind"] not in pipeline._AUDIT_KINDS_BEKANNT


def test_audit_kind_im_kommentar_nicht_erkannt() -> None:
    """Synthetisch: audit() im Kommentar ist kein Call."""
    quelle = (
        '# audit("gibt_es_nicht", {}, None, None)\n'
        'x = 1\n'
    )
    tree = ast.parse(quelle)
    calls = _audit_calls(tree)
    assert calls == [], (
        f"Kommentar-Aufruf faelschlich erkannt: {calls}")


def test_audit_dynamische_werte_aufgeloest() -> None:
    """Jeder f-String-audit() hat einen erlaubten
    Praefix, und jeder Praefix hat aufgeloeste
    Werte im Katalog."""
    calls = _audit_calls(_baum())
    fstrings = [c for c in calls if c["art"] == "fstring"]
    assert fstrings, "keine f-String-audit()-Aufrufe gefunden"
    # Praefix-Whitelist pruefen.
    for c in fstrings:
        zeile = c["zeile"]
        # Praefix aus dem f-String extrahieren.
        quelle = PIPELINE.read_text(encoding="utf-8")
        zeilen = quelle.splitlines()
        if zeile - 1 < len(zeilen):
            z = zeilen[zeile - 1]
            ok = any(
                f'f"{p}' in z or f"f'{p}" in z
                for p in DYNAMISCHE_PRAEFIXE)
            assert ok, (
                f"Z. {zeile}: f-String-audit() ohne "
                f"erlaubten Praefix: {z.strip()}")
    # Aufgeloeste Werte pruefen.
    for praefix, werte in DYNAMISCHE_WERTE.items():
        for wert in werte:
            kind = praefix + wert
            assert kind in pipeline._AUDIT_KINDS_BEKANNT, (
                f"dynamischer Kind {kind!r} nicht im "
                f"Katalog. DYNAMISCHE_WERTE oder "
                f"klassifiziere_deadlock pruefen.")


def test_audit_kinds_kein_attribute_aufruf() -> None:
    """Heute kein pipeline.audit(...)-Aufruf.

    18e: walkt pipeline.py UND werkstatt/audit.py.
    """
    treffer = []
    for dateiname, baum in _baeume():
        for node in ast.walk(baum):
            if not isinstance(node, ast.Call):
                continue
            if (isinstance(node.func, ast.Attribute)
                    and node.func.attr == "audit"):
                treffer.append((dateiname, node.lineno))
    assert treffer == [], (
        f"audit()-Aufrufe als Attribut gefunden: {treffer}. "
        f"Der AST-Test erkennt sie NICHT. Bitte "
        f"_audit_calls() erweitern oder Aufruf "
        f"entfernen.")


def test_katalog_anzahl_matcht_soll() -> None:
    """Katalog-Groesse == _KATALOG_SOLL."""
    assert len(pipeline._AUDIT_KINDS_BEKANNT) == \
        pipeline._KATALOG_SOLL, (
        f"Katalog hat {len(pipeline._AUDIT_KINDS_BEKANNT)} "
        f"Eintraege, _KATALOG_SOLL sagt "
        f"{pipeline._KATALOG_SOLL}. Bei neuem Kind: "
        f"_KATALOG_SOLL anpassen.")
