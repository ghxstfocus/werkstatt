"""Spec: planner.py — Rest-Funktionen (Split-Kette ist anderweitig abgedeckt).

Nicht dupliziert (bereits getestet):
- _merge_mini_tasks           -> test_k15a_merge.py
- _extrahiere_prosa_abschnitt -> test_k15c_blockgroesse.py
- _zerlege_in_sub_tasks       -> test_k11/k19b/k19b_split*
- _korrigiere_aktion(_seq)    -> test_k20/k20b*
- architect_start-Fallback    -> test_k19b_integration.py
- _erledigte_punkte/_migrations_stand/_pruefe_migrations_kollision
                              -> test_k6*/test_k17*

Getestet hier:
- _normalisiere
- _planner_system Migrationsstand-Block (K32)
- _pruefe_api_widerspruch (GOLD-Neu 2026-10-30)
- Audit-Katalog: neue Scout-Kinds sind eingetragen
"""
from __future__ import annotations

import pytest

from werkstatt import planner


# =====================================================================
# _normalisiere
# =====================================================================

def test_normalisiere_leerstring():
    assert planner._normalisiere("") == ""


def test_normalisiere_entfernt_backticks():
    assert planner._normalisiere("1. In `applier.py`") == "1. In applier.py"


def test_normalisiere_mehrfach_leerzeichen():
    assert planner._normalisiere("a    b\t\tc") == "a b c"


def test_normalisiere_strip_an_raendern():
    assert planner._normalisiere("   text   ") == "text"


def test_normalisiere_idempotent():
    s = "1. In `applier.py`   mit   Leerzeichen"
    once = planner._normalisiere(s)
    twice = planner._normalisiere(once)
    assert once == twice


def test_normalisiere_beide_marker_formen_gleich():
    assert planner._normalisiere("1. In `applier.py`") == \
        planner._normalisiere("1. In applier.py")


# =====================================================================
# _planner_system — Migrationsstand-Block (K32)
# =====================================================================

def _mig_ctx() -> dict:
    return {
        "hoechste": "0016",
        "naechste": "0017",
        "alle": ["0014", "0015", "0016"],
    }


def test_planner_system_ohne_migrationsstand():
    s = planner._planner_system("Aufgabe")
    assert "<migrationsstand" not in s


def test_planner_system_mit_leerem_ctx_kein_block():
    s = planner._planner_system("Aufgabe", explorer_ctx={})
    assert "<migrationsstand" not in s


def test_planner_system_mit_migrationsstand_enthaelt_felder():
    s = planner._planner_system(
        "Aufgabe",
        explorer_ctx={"migrations": _mig_ctx()},
    )
    assert '<migrationsstand pflicht="true">' in s
    assert "Hoechste belegte Migrationsnummer: 0016" in s
    assert "Naechste freie Nummer: 0017" in s
    assert "0017" in s


def test_planner_system_migrationsstand_verbotene_nummern():
    ctx = {
        "hoechste": "0020",
        "naechste": "0021",
        "alle": [f"{i:04d}" for i in range(1, 21)],
    }
    s = planner._planner_system("A", explorer_ctx={"migrations": ctx})
    verboten = s.split("VERBOTEN")[1].split("\n")[0]
    for n in ("0016", "0017", "0018", "0019", "0020"):
        assert n in verboten
    assert "0001" not in verboten


def test_planner_system_migrationsstand_kommt_vor_dateien():
    ctx = {
        "migrations": _mig_ctx(),
        "key_files": [{"file": "app/main.py"}],
    }
    s = planner._planner_system("A", explorer_ctx=ctx)
    i_mig = s.find("<migrationsstand")
    i_datei = s.find("app/main.py")
    assert i_mig >= 0
    assert i_datei >= 0
    assert i_mig < i_datei, \
        "Migrationsstand muss VOR den Explorer-Dateien stehen"


# =====================================================================
# _pruefe_api_widerspruch — GOLD-Neu 2026-10-30
# =====================================================================

def _ci() -> dict:
    """Minimaler Code-Index fuer Widerspruchs-Tests."""
    return {
        "core/services/audit_reader.py": {
            "all": [], "imports": [], "classes": [],
            "functions": [
                {"name": "list_recent_assessments",
                 "args": [], "return": "list"},
            ],
        },
        "app/main.py": {
            "all": [], "imports": [], "classes": [],
            "functions": [{"name": "run", "args": [], "return": ""}],
        },
    }


def test_widerspruch_ohne_scout_report():
    assert planner._pruefe_api_widerspruch(None, _ci()) == []


def test_widerspruch_ohne_api_auszug():
    assert planner._pruefe_api_widerspruch({}, _ci()) == []
    assert planner._pruefe_api_widerspruch(
        {"relevante_dateien": []}, _ci()) == []


def test_widerspruch_leerer_api_auszug():
    assert planner._pruefe_api_widerspruch(
        {"api_auszug": {}}, _ci()) == []


def test_widerspruch_erwartet_kein_befund():
    report = {"api_auszug": {
        "core/services/audit_reader.py": ["list_recent_assessments"],
    }}
    assert planner._pruefe_api_widerspruch(report, _ci()) == []


def test_widerspruch_symbol_fehlt():
    report = {"api_auszug": {
        "core/services/audit_reader.py": ["read_events"],
    }}
    befunde = planner._pruefe_api_widerspruch(report, _ci())
    assert len(befunde) == 1
    assert befunde[0]["art"] == "fehlt"
    assert befunde[0]["symbol"] == "read_events"
    assert befunde[0]["gefunden_in"] == []


def test_widerspruch_symbol_verschoben():
    report = {"api_auszug": {
        "core/services/audit_reader.py": ["run"],
    }}
    befunde = planner._pruefe_api_widerspruch(report, _ci())
    assert len(befunde) == 1
    assert befunde[0]["art"] == "verschoben"
    assert befunde[0]["symbol"] == "run"
    assert befunde[0]["gefunden_in"] == ["app/main.py"]


def test_widerspruch_mehrere_in_einer_datei():
    report = {"api_auszug": {
        "core/services/audit_reader.py": [
            "list_recent_assessments",
            "read_events",
            "run",
        ],
    }}
    befunde = planner._pruefe_api_widerspruch(report, _ci())
    assert len(befunde) == 2
    arten = {b["symbol"]: b["art"] for b in befunde}
    assert arten == {"read_events": "fehlt", "run": "verschoben"}


def test_widerspruch_mehrere_dateien():
    report = {"api_auszug": {
        "a.py": ["read_events"],
        "b.py": ["gibtsnicht"],
    }}
    befunde = planner._pruefe_api_widerspruch(report, _ci())
    assert len(befunde) == 2


def test_widerspruch_ignoriert_ungueltige_eintraege():
    report = {"api_auszug": {
        "a.py": [123, None, "read_events", ""],
        "b.py": "keine-liste",
        42: ["x"],
    }}
    befunde = planner._pruefe_api_widerspruch(report, _ci())
    assert len(befunde) == 1
    assert befunde[0]["symbol"] == "read_events"


def test_widerspruch_deterministisch():
    report = {"api_auszug": {
        "a.py": ["read_events", "run"],
    }}
    a = planner._pruefe_api_widerspruch(report, _ci())
    b = planner._pruefe_api_widerspruch(report, _ci())
    assert a == b


# =====================================================================
# Audit-Katalog: neue Scout-Kinds muessen eingetragen sein
# =====================================================================

@pytest.mark.parametrize("kind", [
    "planner_scout_ok",
    "planner_scout_llm_fehler",
    "planner_scout_json_fehler",
    "planner_scout_api_widerspruch",
])
def test_audit_kind_scout_bekannt(kind):
    """Alle Scout-Audit-Kinds sind in _AUDIT_KINDS_BEKANNT.

    Verhindert stillen Katalog-Drift.
    """
    from werkstatt.audit import _AUDIT_KINDS_BEKANNT
    assert kind in _AUDIT_KINDS_BEKANNT, \
        f"{kind} fehlt in _AUDIT_KINDS_BEKANNT"


# =====================================================================
# GOLD 2026-10-30: <measured_files_hinweis> statt <pflicht>
# =====================================================================

def test_planner_system_measured_files_als_kontext():
    """Der Block sagt explizit: KONTEXT, keine Aufgabenliste.

    Regression: Live 2026-10-30 20:26 baute der Architect 29 Tasks
    fuer 28 gemessene Dateien, weil <pflicht> "DEINE TASKS MUESSEN
    GENAU DIESE N DATEIEN VERWENDEN" sagte.
    """
    ctx = {"key_files": [{"file": "a.py"}, {"file": "b.py"}]}
    s = planner._planner_system("Testaufgabe", ctx)
    assert "<measured_files_hinweis>" in s
    assert "KONTEXT, keine Aufgabenliste" in s
    assert "<pflicht>" not in s
    assert "MUESSEN GENAU DIESE" not in s


# =====================================================================
# GOLD 2026-10-30: preview-Rendering in _planner_system
# =====================================================================

def test_planner_system_rendert_datei_inhalt():
    """Wenn key_files preview haben, landet der Inhalt im Prompt."""
    ctx = {"key_files": [
        {"file": "a.py", "why": "explizit", "confidence": "high",
         "preview": "def foo():\n    return 1\n"},
    ]}
    s = planner._planner_system("Aufgabe", ctx)
    assert "<ist_zustand>" in s
    assert "<datei_inhalt" in s
    assert 'datei="a.py"' in s
    assert "def foo():\n    return 1" in s


def test_planner_system_ohne_preview_kein_ist_zustand():
    """Ohne preview kein <ist_zustand>-Block."""
    ctx = {"key_files": [
        {"file": "a.py", "why": "explizit", "confidence": "high"},
    ]}
    s = planner._planner_system("Aufgabe", ctx)
    assert "<ist_zustand>" not in s


# =====================================================================
# GOLD 2026-10-30: Scout-Abbruch -> skip_plan_gate
# =====================================================================

def test_loop_skip_plan_gate_bei_auftrag_bereits_erfuellt():
    """Wenn run_planner auftrag_bereits_erfuellt setzt, springt der
    Loop direkt zum Human-Gate (Plan-Gate ueberspringen).

    Regression: Live 2026-10-30 21:58 — Scout meldete
    bereits_erfuellt, run_planner gab True zurueck, aber der
    Plan-Gate failte (Tasks leer), Loop brach ab mit
    'LOOP FEHLGESCHLAGEN'.
    """
    import inspect
    from werkstatt import loop as loop_mod
    src = inspect.getsource(loop_mod.run_pipeline_loop)
    assert "auftrag_bereits_erfuellt" in src
    assert "skip_plan_gate" in src or "via" in src
    assert "_task_ende(state, phase_state, \"scout_skip\"" in src or \
           "scout_skip" in src
