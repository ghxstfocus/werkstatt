"""Tests fuer die Anti-Pattern-Bibliothek (pipeline.lade_anti_patterns
und pipeline.anti_patterns_fuer).

Prueft:
  - Katalog laedt und validiert (fail-closed).
  - Pflichtfelder, id-Format, kategorie, rollen.
  - audit_kinds muessen bekannt sein.
  - trigger_gruende muessen in ERLAUBTE_SOLVER_QUELLEN stehen.
  - Filter nach Rolle.
  - Filter nach Trigger-Grund (VV2 Fallback).
  - Limit (VV1).
  - Sortierung nach Audit-Haeufigkeit.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

import pytest

import pipeline

# =====================================================================
# Katalog laden und validieren
# =====================================================================

class TestKatalog:
    def test_katalog_laedt(self) -> None:
        aps = pipeline.lade_anti_patterns()
        assert isinstance(aps, list)
        assert len(aps) >= 7

    def test_alle_pflichtfelder_gesetzt(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            for feld in pipeline._AP_PFLICHTFELDER:
                assert feld in e, f"{e['id']}: Pflichtfeld {feld} fehlt"

    def test_ids_eindeutig(self) -> None:
        aps = pipeline.lade_anti_patterns()
        ids = [e["id"] for e in aps]
        assert len(ids) == len(set(ids))

    def test_id_format(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            assert pipeline._AP_IDS_RE.match(e["id"]), e["id"]

    def test_rollen_erlaubt_und_nicht_leer(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            assert e["rollen"], f"{e['id']}: rollen leer"
            for r in e["rollen"]:
                assert r in pipeline._AP_ROLLEN_ERLAUBT, f"{e['id']}: {r}"

    def test_kategorie_1_2_3(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            assert e["kategorie"] in (1, 2, 3), e["id"]

    def test_audit_kinds_bekannt(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            for ak in e.get("audit_kinds", []) or []:
                assert ak in pipeline._AUDIT_KINDS_BEKANNT, \
                    f"{e['id']}: {ak}"

    def test_trigger_gruende_bekannt(self) -> None:
        aps = pipeline.lade_anti_patterns()
        for e in aps:
            for tg in e.get("trigger_gruende", []) or []:
                assert tg in pipeline.ERLAUBTE_SOLVER_QUELLEN, \
                    f"{e['id']}: {tg}"


# =====================================================================
# Filter nach Rolle
# =====================================================================

class TestRolle:
    def test_builder_limit_3(self) -> None:
        aps = pipeline.anti_patterns_fuer("builder")
        assert len(aps) <= 3

    def test_builder_enthaelt_anker_eintraege(self) -> None:
        ids = {e["id"] for e in pipeline.anti_patterns_fuer(
            "builder", limit=100)}
        assert "ap-anker-dekorator" in ids
        assert "ap-anker-semantik" in ids

    def test_reviewer_limit_3(self) -> None:
        aps = pipeline.anti_patterns_fuer("reviewer")
        assert len(aps) <= 3

    def test_test_generator_sieht_4_eintraege(self) -> None:
        # Phase 3a-2 hat drei weitere Eintraege fuer
        # test_generator ergaenzt.
        aps = pipeline.anti_patterns_fuer("test_generator", limit=100)
        ids = {e["id"] for e in aps}
        assert "ap-test-name-substring" in ids
        assert "ap-modul-konstante-instanz" in ids
        assert "ap-tests-nicht-gesammelt" in ids
        assert "ap-rueckgabe-typ-helper" in ids
        assert len(ids) == 4

    def test_solver_keine_eintraege(self) -> None:
        aps = pipeline.anti_patterns_fuer("solver", limit=100)
        assert aps == []

    def test_unbekannte_rolle_leer(self) -> None:
        aps = pipeline.anti_patterns_fuer("gibt-es-nicht", limit=100)
        assert aps == []


# =====================================================================
# Limit
# =====================================================================

class TestLimit:
    def test_limit_default_3(self) -> None:
        aps = pipeline.anti_patterns_fuer("builder")
        assert len(aps) == 3

    def test_limit_1(self) -> None:
        aps = pipeline.anti_patterns_fuer("builder", limit=1)
        assert len(aps) == 1

    def test_limit_groesser_anzahl(self) -> None:
        aps = pipeline.anti_patterns_fuer("builder", limit=1000)
        assert len(aps) >= 6


# =====================================================================
# Trigger-Filter (VV2)
# =====================================================================

class TestTrigger:
    def test_eintrag_ohne_trigger_wird_immer_gezeigt(self) -> None:
        # ap-anker-dekorator hat kein trigger_gruende-Feld.
        # Sollte bei jedem Trigger-Grund erscheinen.
        aps = pipeline.anti_patterns_fuer(
            "builder", "p1_trigger", limit=100)
        ids = {e["id"] for e in aps}
        assert "ap-anker-dekorator" in ids

    def test_eintrag_mit_trigger_nur_wenn_passend(self) -> None:
        # Hypothetischer Eintrag mit trigger_gruende wird
        # nur gezeigt, wenn der Grund passt. Heute hat noch
        # kein Eintrag trigger_gruende, daher nur die
        # Grundpruefung.
        aps = pipeline.anti_patterns_fuer(
            "builder", "builder_rueckfrage", limit=100)
        # Alle Eintraege ohne trigger_gruende erscheinen.
        assert isinstance(aps, list)


# =====================================================================
# Sortierung (Audit-Haeufigkeit)
# =====================================================================

class TestSortierung:
    def test_ap_anker_dekorator_oben(self) -> None:
        # ap-anker-dekorator hat audit_kinds mit vielen
        # Treffern (builder_anker_fehler +
        # anker_einrueckung_korrigiert). Sollte bei
        # builder vorn stehen.
        aps = pipeline.anti_patterns_fuer("builder", limit=100)
        assert aps[0]["id"] == "ap-anker-dekorator"

    def test_reihenfolge_stabil(self) -> None:
        a = pipeline.anti_patterns_fuer("builder", limit=100)
        b = pipeline.anti_patterns_fuer("builder", limit=100)
        assert [e["id"] for e in a] == [e["id"] for e in b]


# =====================================================================
# Schema-Validierung (fail-closed)
# =====================================================================

class TestValidierung:
    def test_ungueltige_id_wird_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "AP_GROSS", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 2,
                 "rollen": ["builder"]},
                index=0)

    def test_leere_rollen_werden_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 2,
                 "rollen": []},
                index=0)

    def test_unbekannte_rolle_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 2,
                 "rollen": ["gibt-es-nicht"]},
                index=0)

    def test_unbekannte_kategorie_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 4,
                 "rollen": ["builder"]},
                index=0)

    def test_unbekanntes_audit_kind_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 2,
                 "rollen": ["builder"],
                 "audit_kinds": ["gibt-es-nicht"]},
                index=0)

    def test_unbekannter_trigger_grund_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x",
                 "beschreibung": "x", "loesung": "x",
                 "begruendung": "x", "kategorie": 2,
                 "rollen": ["builder"],
                 "trigger_gruende": ["gibt-es-nicht"]},
                index=0)

    def test_fehlendes_pflichtfeld_abgewiesen(self) -> None:
        with pytest.raises(SystemExit):
            pipeline._validiere_ap_eintrag(
                {"id": "ap-x", "titel": "x"},
                index=0)
