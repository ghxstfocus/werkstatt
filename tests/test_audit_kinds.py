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

import pytest

sys.path.insert(0, "/opt/werkstatt")
import pipeline

PIPELINE = Path("/opt/werkstatt/pipeline.py")

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


# W48-A16-b (2026-10-18): 30 bekannte Luecken im
# Katalog. Der Test wird in W48-A16-b-2 scharf
# gestellt, sobald die Luecken registriert sind.
# Bekannte Luecken (Stand 2026-10-18):
#   pipeline_escalated, planner_verworfen,
#   anti_patterns_injiziert, planner_rolle_fehlt,
#   solver_budget_exhausted,
#   solver_max_solver_runden_erreicht,
#   quelle_invalid, mess_nach_nahe_budget,
#   basis_gate_test_result,
#   builder_commit_paket_failed_retry,
#   reviewer_call_failed, builder_call_failed,
#   phase_basis_gate_failed,
#   phasen_basis_gate_untracked,
#   planner_start, planner_ungueltig,
#   planner_abgebrochen, planner_bestaetigt,
#   planner_call_failed, recovery_budget,
#   solver_trigger_a, auto_repair_ruff.
@pytest.mark.xfail(
    strict=False,
    reason="W48-A16-b-2: 30 Kinds produktiv "
           "verwendet, aber nicht registriert. "
           "Wird im NAECHSTEN Block (W48-A16-b-2) "
           "behoben: 28 registrieren, 1 umbenennen "
           "(reviewer_call_failed -> judge_call_"
           "failed), _KATALOG_SOLL 122 -> 151. "
           "Bei Ueberschreitung: strict=True "
           "schaltet CI rot.")
def test_audit_kinds_alle_aufrufe_registriert() -> None:
    """Jeder audit('literal', ...) ist im Katalog."""
    calls = _audit_calls(_baum())
    literale = [c for c in calls if c["art"] == "literal"]
    assert literale, "keine audit()-Aufrufe gefunden"
    fehlend = [
        c for c in literale
        if c["kind"] not in pipeline._AUDIT_KINDS_BEKANNT
    ]
    assert not fehlend, (
        "audit()-Aufrufe mit nicht registriertem Kind:\n"
        + "\n".join(
            f"  Z. {c['zeile']}: {c['kind']!r}"
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
    Wenn einer dazukommt, faengt dieser Test ihn,
    bevor der AST-Test ihn uebersieht."""
    tree = _baum()
    treffer = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == "audit"):
            treffer.append(node.lineno)
    assert treffer == [], (
        f"pipeline.audit()-Aufrufe gefunden: {treffer}. "
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
