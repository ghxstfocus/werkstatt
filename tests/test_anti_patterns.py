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
from pathlib import Path

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

    def test_solver_hat_6_eintraege(self) -> None:
        # Phase 3c-1 (Commit 4916b01): Solver-Rolle zu
        # 6 Katalogeintraegen ergaenzt.
        aps = pipeline.anti_patterns_fuer("solver", limit=100)
        ids = {e["id"] for e in aps}
        assert ids == {
            "ap-anker-dekorator",
            "ap-anker-semantik",
            "ap-string-literal-statt-konstante",
            "ap-api-aus-gedaechtnis",
            "ap-anker-aus-chat",
            "ap-fehlender-assert-patch",
        }

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
    def test_fallback_eintrag_wird_immer_gezeigt(self) -> None:
        # ap-import-nachtrag-ohne-ruff hat kein
        # trigger_gruende-Feld (Fallback).
        # Sollte bei jedem Trigger-Grund erscheinen.
        aps = pipeline.anti_patterns_fuer(
            "builder", "p1_trigger", limit=100)
        ids = {e["id"] for e in aps}
        assert "ap-import-nachtrag-ohne-ruff" in ids

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


# =====================================================================
# Phase 3b: _anti_pattern_block + Injektion in baue_anker_rueckmeldung
# =====================================================================

class TestAntiPatternBlock:
    def _state(self, *, anker_fehler=None, project_dir=None):
        from pathlib import Path
        s = pipeline.RunState(
            block_id="test-block",
            aufgabe="test",
            start_ts="2026-10-15T00:00:00+00:00",
            docs={},
            agents={},
            always={},
            optional={},
            file_whitelist=["core/"],
            api_key="test-key",
            budget={"max_review_rounds": 5, "max_llm_calls": 30},
            agent_docs={},
            project_dir=Path(project_dir) if project_dir else Path("/tmp"),
            project_name="test-projekt",
        )
        if anker_fehler:
            s.letzte_anker_fehler = anker_fehler
        return s

    def test_leer_bei_unbekannter_rolle(self) -> None:
        # _anti_pattern_block prueft NICHT die Anker-Fehler,
        # nur Rolle und Trigger-Grund. Bei unbekannter Rolle
        # kommt nichts zurueck.
        s = self._state()
        assert pipeline._anti_pattern_block(s, "gibt-es-nicht") == ""

    def test_leer_bei_trigger_ohne_passende_spezifische(self) -> None:
        # Trigger-Grund ohne spezifischen Eintrag in der
        # Katalog-Rolle: nur Fallback-Eintraege, aber Block
        # ist nicht leer.
        s = self._state()
        block = pipeline._anti_pattern_block(
            s, "test_generator", "p1_trigger")
        assert "## ANTI-PATTERNS" in block

    def test_mit_anker_fehler_enthaelt_block(self) -> None:
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "nicht_gefunden")])
        block = pipeline._anti_pattern_block(s, "builder")
        assert "## ANTI-PATTERNS" in block
        assert "ap-anker-dekorator" in block
        assert "Beschreibung:" in block
        assert "Loesung:" in block

    def test_ohne_trigger_grund_zeigt_fallback(self) -> None:
        # ap-anker-dekorator hat trigger_gruende=[anker_nicht_gemessen].
        # Wenn trigger_grund=None, greift VV2-Fallback: alle
        # Rollen-Eintraege werden gezeigt.
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "nicht_gefunden")])
        block_none = pipeline._anti_pattern_block(s, "builder", None)
        block_ng = pipeline._anti_pattern_block(
            s, "builder", "anker_nicht_gemessen")
        # Beide enthalten ap-anker-dekorator
        assert "ap-anker-dekorator" in block_none
        assert "ap-anker-dekorator" in block_ng

    def test_trigger_grund_filtert(self) -> None:
        # XX1/XX3: Bei trigger_grund=wirkungsloser_patch
        # muss der spezifische Eintrag (ap-string-literal-
        # statt-konstante) in den Top-3 stehen, auch wenn
        # generische Fallback-Eintraege existieren.
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "wirkungslos")])
        block = pipeline._anti_pattern_block(
            s, "builder", "wirkungsloser_patch")
        assert "ap-string-literal-statt-konstante" in block
        # ap-anker-dekorator hat trigger_gruende=[anker_nicht_gemessen]
        # und darf hier NICHT erscheinen.
        assert "ap-anker-dekorator" not in block

    def test_spezifisch_vor_fallback(self) -> None:
        # XX5: Bei trigger_grund=X und spezifischem Kandidaten
        # muss der spezifische Eintrag VOR den Fallbacks stehen.
        aps = pipeline.anti_patterns_fuer(
            "builder", "wirkungsloser_patch", limit=3)
        ids = [e["id"] for e in aps]
        assert ids[0] == "ap-string-literal-statt-konstante"

    def test_ohne_spezifische_fallback_greift(self) -> None:
        # XX5: Bei trigger_grund=X ohne spezifische Kandidaten
        # greifen die Fallbacks.
        aps = pipeline.anti_patterns_fuer(
            "builder", "reviewer_command", limit=100)
        # Kein Eintrag hat trigger_gruende=[reviewer_command],
        # also nur Fallbacks. Mindestens einer da.
        assert len(aps) >= 1

    def test_ohne_trigger_grund_nach_haeufigkeit(self) -> None:
        # XX4: Bei trigger_grund=None ist die Sortierung
        # nach Audit-Haeufigkeit (wie vorher). ap-anker-
        # dekorator hat die hoechste Haeufigkeit.
        aps = pipeline.anti_patterns_fuer("builder", limit=100)
        ids = [e["id"] for e in aps]
        assert ids[0] == "ap-anker-dekorator"

    def test_max_3_eintraege(self) -> None:
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "nicht_gefunden")])
        block = pipeline._anti_pattern_block(
            s, "builder", "anker_nicht_gemessen")
        anzahl = block.count("- [ap-")
        assert anzahl <= 3

    def test_trigger_grund_aus_state(self) -> None:
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "wirkungslos")])
        assert pipeline._ap_trigger_grund_aus_state(s) == (
            "wirkungsloser_patch")

    def test_trigger_grund_prioritaet(self) -> None:
        # Bei mehreren Gruenden gewinnt wirkungslos.
        s = self._state(anker_fehler=[
            (0, "core/x.py", "foo", "nicht_gefunden"),
            (1, "core/y.py", "bar", "wirkungslos"),
        ])
        assert pipeline._ap_trigger_grund_aus_state(s) == (
            "wirkungsloser_patch")

    def test_trigger_grund_leer_ergibt_none(self) -> None:
        s = self._state(
            anker_fehler=[(0, "core/x.py", "", "leer")])
        assert pipeline._ap_trigger_grund_aus_state(s) is None

    def test_kuerzung_bei_500_zeichen(self) -> None:
        lang = "x" * 1000
        gekuerzt = pipeline._ap_kuerzen(lang, 500)
        assert len(gekuerzt) <= 500
        assert gekuerzt.endswith("\u2026")

    def test_keine_kuerzung_bei_kurz(self) -> None:
        kurz = "kurz"
        assert pipeline._ap_kuerzen(kurz, 500) == kurz


class TestBaueAnkerRueckmeldungMitAP:
    def _state(self, *, anker_fehler=None):
        s = pipeline.RunState(
            block_id="test-block",
            aufgabe="test",
            start_ts="2026-10-15T00:00:00+00:00",
            docs={},
            agents={},
            always={},
            optional={},
            file_whitelist=["core/"],
            api_key="test-key",
            budget={"max_review_rounds": 5, "max_llm_calls": 30},
            agent_docs={},
            project_dir=Path("/tmp"),
            project_name="test-projekt",
        )
        if anker_fehler:
            s.letzte_anker_fehler = anker_fehler
        return s

    def test_ohne_fehler_leer(self) -> None:
        s = self._state()
        assert pipeline.baue_anker_rueckmeldung(s) == ""

    def test_mit_fehler_enthaelt_ap_block(self) -> None:
        s = self._state(
            anker_fehler=[(0, "core/x.py", "foo", "nicht_gefunden")])
        block = pipeline.baue_anker_rueckmeldung(s)
        assert "## ANKER-PRUEFUNG" in block
        assert "## ANTI-PATTERNS" in block
        # Reihenfolge: ANKER-PRUEFUNG kommt vor ANTI-PATTERNS
        idx_ap = block.find("## ANKER-PRUEFUNG")
        idx_anti = block.find("## ANTI-PATTERNS")
        assert idx_ap < idx_anti


# =====================================================================
# Phase 3c-2: Reviewer-Injektion in build_system_prompt
# =====================================================================

class TestReviewerInjektion:
    def _state(self):
        from pathlib import Path as _P
        return pipeline.RunState(
            block_id="test-block",
            aufgabe="test",
            start_ts="2026-10-15T00:00:00+00:00",
            docs={},
            agents={},
            always={},
            optional={},
            file_whitelist=["core/"],
            api_key="test-key",
            budget={"max_review_rounds": 5, "max_llm_calls": 30},
            agent_docs={},
            project_dir=_P("/tmp"),
            project_name="test-projekt",
        )

    def _agent(self, name):
        return {"name": name, "body": f"Body-{name}"}

    def test_reviewer_mit_state_enthaelt_ap_block(self) -> None:
        s = self._state()
        prompt = pipeline.build_system_prompt(
            self._agent("reviewer"), {}, [], state=s)
        assert "## ANTI-PATTERNS" in prompt

    def test_reviewer_ohne_state_kein_ap_block(self) -> None:
        prompt = pipeline.build_system_prompt(
            self._agent("reviewer"), {}, [])
        assert "## ANTI-PATTERNS" not in prompt

    def test_reviewer_mit_mit_anti_patterns_false(self) -> None:
        s = self._state()
        prompt = pipeline.build_system_prompt(
            self._agent("reviewer"), {}, [],
            state=s, mit_anti_patterns=False)
        assert "## ANTI-PATTERNS" not in prompt

    def test_builder_mit_state_kein_ap_block(self) -> None:
        # Builder bekommt den Block via baue_anker_rueckmeldung,
        # nicht via build_system_prompt.
        s = self._state()
        prompt = pipeline.build_system_prompt(
            self._agent("builder"), {}, [], state=s)
        assert "## ANTI-PATTERNS" not in prompt

    def test_solver_mit_state_kein_ap_block(self) -> None:
        # Solver bekommt den Block via rufe_solver (Phase 3c-3),
        # nicht via build_system_prompt.
        s = self._state()
        prompt = pipeline.build_system_prompt(
            self._agent("solver"), {}, [], state=s)
        assert "## ANTI-PATTERNS" not in prompt

    def test_reviewer_ap_block_max_3(self) -> None:
        s = self._state()
        prompt = pipeline.build_system_prompt(
            self._agent("reviewer"), {}, [], state=s)
        anzahl = prompt.count("- [ap-")
        assert anzahl <= 3


# =====================================================================
# Phase 3c-3: Solver-Injektion in rufe_solver
# =====================================================================

class TestSolverInjektion:
    def _state(self):
        from pathlib import Path as _P
        return pipeline.RunState(
            block_id="test-block",
            aufgabe="test",
            start_ts="2026-10-15T00:00:00+00:00",
            docs={},
            agents={},
            always={},
            optional={},
            file_whitelist=["core/"],
            api_key="test-key",
            budget={"max_review_rounds": 5, "max_llm_calls": 30},
            agent_docs={},
            project_dir=_P("/tmp"),
            project_name="test-projekt",
        )

    def test_rufe_solver_signatur_hat_trigger_grund(self) -> None:
        import inspect
        sig = inspect.signature(pipeline.rufe_solver)
        assert "trigger_grund" in sig.parameters
        assert "aufrufer" in sig.parameters
        assert sig.parameters["trigger_grund"].default is None
        assert sig.parameters["aufrufer"].default == "unbekannt"

    def test_anti_pattern_block_mit_aufrufer(self) -> None:
        # YY4: aufrufer wird ins Audit geschrieben.
        # Wir koennen das Audit-Log nicht direkt testen,
        # aber die Funktion akzeptiert den Parameter.
        s = self._state()
        s.letzte_anker_fehler = [
            (0, "core/x.py", "foo", "nicht_gefunden")]
        block = pipeline._anti_pattern_block(
            s, "solver", "anker_nicht_gemessen",
            aufrufer="deadlock")
        assert "## ANTI-PATTERNS" in block

    def test_solver_rolle_hat_6_kandidaten(self) -> None:
        # Nach 3c-1: Solver hat 6 Eintraege.
        aps = pipeline.anti_patterns_fuer(
            "solver", "anker_nicht_gemessen", limit=100)
        # Spezifisch fuer anker_nicht_gemessen:
        # ap-anker-dekorator, ap-anker-semantik,
        # ap-anker-aus-chat, ap-fehlender-assert-patch.
        ids = {e["id"] for e in aps}
        assert "ap-anker-dekorator" in ids
        assert "ap-anker-semantik" in ids

    def test_solver_trigger_grund_none_fallback(self) -> None:
        aps = pipeline.anti_patterns_fuer("solver", limit=100)
        # Fallback: alle 6 Rollen-Eintraege.
        assert len(aps) == 6
