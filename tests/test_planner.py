"""Tests fuer den Planner-Agenten (Block P1, 2026-10-15).

Prueft:
  - Parser fuer Planner-Antworten (Auftrag / Rueckfrage / ungueltig).
  - Praefix-Konstanten.
  - Planner-Rolle wird geladen.
  - _planner_lauf signatur.
  - main --planner erkennt Argument.
  - RunState-Felder.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")


import pipeline

# =====================================================================
# Praefix-Konstanten
# =====================================================================

class TestPraefixe:
    def test_praefixe_konstant(self) -> None:
        assert pipeline.PLANNER_BLOCK_PRAEFIXE == (
            "feat", "fix", "docs", "refactor", "test",
        )

    def test_praefixe_ist_tupel(self) -> None:
        assert isinstance(pipeline.PLANNER_BLOCK_PRAEFIXE, tuple)


# =====================================================================
# parse_planner_reply
# =====================================================================

class TestParser:
    def test_auftrag_gueltig(self) -> None:
        text = (
            "Block: feat - Traceroute-Timeout\n"
            "Ziel:\n"
            "  Timeout behandeln.\n"
            "Vorgehen:\n"
            "  1. try/except.\n"
            "Erfolgskriterium:\n"
            "  - Test existiert.\n"
        )
        r = pipeline.parse_planner_reply(text)
        assert r["art"] == "auftrag"
        assert r["praefix"] == "feat"
        assert r["titel"] == "Traceroute-Timeout"

    def test_alle_praefixe_erkannt(self) -> None:
        for p in pipeline.PLANNER_BLOCK_PRAEFIXE:
            text = f"Block: {p} - Titel\nZiel:\n  X\n"
            r = pipeline.parse_planner_reply(text)
            assert r["art"] == "auftrag", f"Praefix {p} nicht erkannt"
            assert r["praefix"] == p

    def test_unbekanntes_praefix_ungueltig(self) -> None:
        text = "Block: chore - irgendwas\nZiel:\n  X\n"
        r = pipeline.parse_planner_reply(text)
        assert r["art"] == "ungueltig"

    def test_ohne_praefix_ungueltig(self) -> None:
        text = "Block: Titel ohne Praefix\nZiel:\n  X\n"
        r = pipeline.parse_planner_reply(text)
        assert r["art"] == "ungueltig"

    def test_rueckfrage(self) -> None:
        text = "RUECKFRAGE:\n  Was ist mit Modul X?\n"
        r = pipeline.parse_planner_reply(text)
        assert r["art"] == "rueckfrage"
        assert "Modul X" in r["frage"]

    def test_leer_ungueltig(self) -> None:
        r = pipeline.parse_planner_reply("")
        assert r["art"] == "ungueltig"

    def test_whitespace_ungueltig(self) -> None:
        r = pipeline.parse_planner_reply("   \n\n")
        assert r["art"] == "ungueltig"

    def test_freitext_ungueltig(self) -> None:
        text = "Das ist kein Format. Nur Prosa."
        r = pipeline.parse_planner_reply(text)
        assert r["art"] == "ungueltig"

    def test_praefix_case_insensitive(self) -> None:
        text = "Block: FEAT - Titel\nZiel:\n  X\n"
        r = pipeline.parse_planner_reply(text)
        # Praefix wird kleingeschrieben erkannt
        assert r["art"] == "auftrag"
        assert r["praefix"] == "feat"

    def test_text_feld_immer_gesetzt(self) -> None:
        text = "irgendwas"
        r = pipeline.parse_planner_reply(text)
        assert r["text"] == text


# =====================================================================
# Rollen
# =====================================================================

class TestRolle:
    def test_planner_rolle_geladen(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        assert "planner" in agents
        assert agents["planner"]["name"] == "planner"

    def test_planner_hard_rules_verfuegbar(self) -> None:
        assert hasattr(pipeline, "HARD_RULES_PLANNER")
        assert "P1." in pipeline.HARD_RULES_PLANNER
        assert "P9." in pipeline.HARD_RULES_PLANNER

    def test_planner_in_mapping(self) -> None:
        assert "planner" in pipeline.HARD_RULES_BY_ROLE
        assert (pipeline.HARD_RULES_BY_ROLE["planner"]
                is pipeline.HARD_RULES_PLANNER)


# =====================================================================
# _planner_lauf
# =====================================================================

class TestPlannerLauf:
    def test_planner_lauf_signatur(self) -> None:
        import inspect
        sig = inspect.signature(pipeline._planner_lauf)
        params = list(sig.parameters.keys())
        assert params == [
            "state", "api_key", "roher_auftrag",
            "project_dir", "project_name", "historie",
            # P2a-S5a-A8: stufe hinzugefuegt.
            "stufe",
            # P2b-5: korrektur_kontext hinzugefuegt.
            "korrektur_kontext",
            # Block 2a / B1: phase_stand hinzugefuegt.
            "phase_stand",
        ]


# =====================================================================
# main --planner
# =====================================================================

class TestMain:
    def test_planner_main_pfad_existiert(self) -> None:
        assert hasattr(pipeline, "_planner_main_pfad")
        import inspect
        sig = inspect.signature(pipeline._planner_main_pfad)
        params = list(sig.parameters.keys())
        assert params == ["project_name", "roher_auftrag", "state_ref"]


# =====================================================================
# RunState-Felder
# =====================================================================

class TestRunState:
    def test_planner_felder_vorhanden(self) -> None:
        import dataclasses
        felder = {f.name for f in dataclasses.fields(pipeline.RunState)}
        assert "planner_model" in felder
        assert "planner_vorschlag" in felder
        assert "planner_modus" in felder
        assert "planner_runden" in felder

    def test_defaults(self) -> None:
        import dataclasses
        d = {f.name: f.default for f in dataclasses.fields(pipeline.RunState)}
        assert d["planner_model"] == "deepseek-chat"
        assert d["planner_vorschlag"] == ""
        assert d["planner_modus"] == "manual"
        assert d["planner_runden"] == 0

# =====================================================================
# Block P2a: planner.md Stufe-1/Stufe-2-Sektionen
# + build_system_prompt(stufe=) Prompt-Asserts.
# =====================================================================

class TestPlannerStufenPrompt:
    def _planner_agent(self) -> dict:
        import pipeline
        return pipeline.load_agents("/opt/werkstatt/agents")["planner"]

    def test_body_enthaelt_stufe_1_sektion(self) -> None:
        agent = self._planner_agent()
        assert "## Stufe 1: Auftrag" in agent["body"]

    def test_body_enthaelt_stufe_2_sektion(self) -> None:
        agent = self._planner_agent()
        assert "## Stufe 2: Phasenplan" in agent["body"]

    def test_prompt_stufe_1_enthaelt_p3(self) -> None:
        import pipeline
        agent = self._planner_agent()
        prompt = pipeline.build_system_prompt(
            agent, {}, [], stufe=1)
        assert "P3. Du antwortest mit GENAU EINEM Auftrag" in prompt

    def test_prompt_stufe_2_enthaelt_p3strich(self) -> None:
        import pipeline
        agent = self._planner_agent()
        prompt = pipeline.build_system_prompt(
            agent, {}, [], stufe=2)
        assert "P3'." in prompt
        assert "P10." in prompt
        assert "P14." in prompt

    def test_prompt_stufe_2_enthaelt_nicht_original_p3(self) -> None:
        import pipeline
        agent = self._planner_agent()
        prompt = pipeline.build_system_prompt(
            agent, {}, [], stufe=2)
        # P3 (Original) darf NICHT enthalten sein.
        assert "P3. Du antwortest mit GENAU EINEM Auftrag" not in prompt

    def test_prompt_default_ist_stufe_1(self) -> None:
        import pipeline
        agent = self._planner_agent()
        p_default = pipeline.build_system_prompt(agent, {}, [])
        p_stufe1 = pipeline.build_system_prompt(
            agent, {}, [], stufe=1)
        assert p_default == p_stufe1

    def test_user_content_stufe_2(self) -> None:
        import pipeline
        uc = pipeline._planner_user_content(
            "roher Auftrag", "historie", stufe=2)
        assert "P10-P14" in uc
        assert "P7/P8" not in uc

    def test_user_content_stufe_1(self) -> None:
        import pipeline
        uc = pipeline._planner_user_content(
            "roher Auftrag", "historie", stufe=1)
        assert "P7/P8" in uc
        assert "P10-P14" not in uc

# =====================================================================
# Planner-Rolle + Blockgroessen (2026-10-16)
# =====================================================================

class TestPlannerRolleGroesse:
    def test_stufe2_hat_p15(self) -> None:
        assert "P15." in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_hat_p16(self) -> None:
        assert "P16." in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_p15_zieldateien(self) -> None:
        assert "Zieldateien" in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_p16_praefix_neu(self) -> None:
        assert "neu:" in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe1_kein_p15(self) -> None:
        assert "P15." not in pipeline.HARD_RULES_PLANNER_STUFE1

    def test_stufe1_kein_p16(self) -> None:
        assert "P16." not in pipeline.HARD_RULES_PLANNER_STUFE1

    def test_stufe1_unveraendert(self) -> None:
        # P1-P9 wortgleich geblieben.
        s = pipeline.HARD_RULES_PLANNER_STUFE1
        assert "P1." in s and "P2." in s and "P9." in s
        assert "P10." not in s and "P15." not in s

    def test_stufe2_p10_p14_unveraendert(self) -> None:
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        for regel in ("P10.", "P11.", "P12.",
                      "P13.", "P14."):
            assert regel in s

    def test_stufe2_hat_refactoring_ausnahme(self) -> None:
        assert "Refactorings" in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_planner_md_zerlegst(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "zerlegst" in text or "zerlege" in text

    def test_planner_md_baubare(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "baubare" in text or "baubar" in text

    def test_planner_md_rolle_stufe_1(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "Deine Rolle (Stufe 1)" in text

    def test_planner_md_rolle_stufe_2(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "Deine Rolle (Stufe 2)" in text

    def test_planner_md_guter_plan(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "GUTER Plan" in text

    def test_planner_md_schlechter_plan(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "SCHLECHT" in text

    def test_build_system_prompt_stufe2_hat_p15(self) -> None:
        # System-Prompt fuer Stufe 2 enthaelt P15.
        # Der Planner-Agent wird geladen.
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["planner"], {}, [], stufe=2)
        assert "P15." in prompt
        assert "P16." in prompt

    def test_build_system_prompt_stufe1_kein_p15(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["planner"], {}, [], stufe=1)
        assert "P15." not in prompt
        assert "P16." not in prompt



# =====================================================================
# Planner-Praezision (2026-10-16): P15-Neu, P17, P18
# =====================================================================

class TestPlannerPraezision:
    def test_stufe2_hat_p17(self) -> None:
        assert "P17." in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_hat_p18(self) -> None:
        assert "P18." in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_p15_unterpunkt_regel(self) -> None:
        # Auflage A1: Unterpunkt-Regel 3-7.
        assert "3-7 Unterpunkte" in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_p15_atomar_ausnahme(self) -> None:
        # Auflage A1: atomare Ausnahme.
        assert "ATOMAR" in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_stufe2_p15_datei_regel(self) -> None:
        # Auflage B1-A2: Datei-Regel wortgleich.
        assert "1-2 Zieldateien plus hoechstens" in (
            pipeline.HARD_RULES_PLANNER_STUFE2)

    def test_stufe2_p17_signatur_tiefe(self) -> None:
        # Auflage B1-A2: Signatur + Schema explizit.
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        assert "Funktions-Signaturen explizit" in s
        assert "Datenbank-Schemas mit Spaltentypen" in s

    def test_stufe2_p17_gut_schlecht_beispiel(self) -> None:
        # Auflage B1-A2: beide Beispiele.
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        assert "class GuardrailRepository:" in s
        assert "Repository mit CRUD-Methoden" in s

    def test_stufe1_kein_p17_p18(self) -> None:
        s = pipeline.HARD_RULES_PLANNER_STUFE1
        assert "P17." not in s
        assert "P18." not in s

    def test_stufe2_p9strich_verweist_auf_p18(self) -> None:
        # Auflage B1-A1: P9' auf P10-P18 erweitert.
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        assert "P10-P18" in s

    def test_planner_md_p18_sektion(self) -> None:
        from pathlib import Path as _P
        text = _P("/opt/werkstatt/agents/planner.md").read_text(
            encoding="utf-8")
        assert "Korrektur-Kompetenz (P18)" in text
        assert "UNBEANTWORTET" in text

    def test_build_system_prompt_stufe2_hat_p17(self) -> None:
        agents = pipeline.load_agents("/opt/werkstatt/agents")
        prompt = pipeline.build_system_prompt(
            agents["planner"], {}, [], stufe=2)
        assert "P17." in prompt
        assert "P18." in prompt


# =====================================================================
# Block 2a (2026-10-16): Korrektur-Kontext — Reviewer-Befund + Phase-Stand
# =====================================================================

class TestPlannerKorrekturKontext:
    def _kk(self) -> dict:
        return {
            "begruendung": "Mensch hat abgelehnt.",
            "alter_plan": "PHASE 18 - Test\nU1: ...",
            "pakete_kompakt": "(keine)",
            "reviewer_befund": "NO-GO\n1. Punkt A\n2. Punkt B",
        }

    def _ps(self) -> dict:
        return {
            "phase_id": 18,
            "unterbloecke": [
                {"id": "U1", "status": "done",
                 "paket_groesse": 3, "letzter_befund": ""},
                {"id": "U2", "status": "no_go",
                 "paket_groesse": 0,
                 "letzter_befund": "NO-GO: Sig falsch"},
                {"id": "U3", "status": "pending",
                 "paket_groesse": 0, "letzter_befund": ""},
            ],
            "naechster": "U2",
        }

    def test_user_content_reviewer_befund_marker(self) -> None:
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk())
        assert "=== REVIEWER-BEFUND (vollstaendig) ===" in uc
        assert "=== /REVIEWER-BEFUND ===" in uc
        assert "1. Punkt A" in uc

    def test_user_content_reviewer_befund_leer_kein_marker(self) -> None:
        kk = self._kk()
        kk["reviewer_befund"] = ""
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2, korrektur_kontext=kk)
        assert "REVIEWER-BEFUND" not in uc

    def test_user_content_reviewer_befund_nicht_gekuerzt(self) -> None:
        kk = self._kk()
        lang = "X" * 5000
        kk["reviewer_befund"] = lang
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2, korrektur_kontext=kk)
        assert lang in uc

    def test_user_content_p10_p18_im_abschluss(self) -> None:
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk())
        assert "P10-P16" in uc
        assert "P17" in uc
        assert "P18" in uc

    def test_user_content_phase_stand_sektion(self) -> None:
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk(),
            phase_stand=self._ps())
        assert "AKTUELLER PHASENSTAND:" in uc
        assert "U1: done" in uc
        assert "U2: no_go" in uc

    def test_user_content_phase_stand_naechster_hinweis(self) -> None:
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk(),
            phase_stand=self._ps())
        assert "Plane NUR U2" in uc
        assert "Beruehre" in uc

    def test_user_content_phase_stand_none_keine_sektion(self) -> None:
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk())
        assert "AKTUELLER PHASENSTAND" not in uc

    def test_user_content_phase_stand_alle_done_fallback(self) -> None:
        ps = self._ps()
        for u in ps["unterbloecke"]:
            u["status"] = "done"
        ps["naechster"] = None
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=2,
            korrektur_kontext=self._kk(),
            phase_stand=ps)
        assert "Alle Unterbloecke sind abgeschlossen" in uc

    def test_phase_stand_sektion_letzter_befund_gekuerzt(self) -> None:
        ps = self._ps()
        ps["unterbloecke"][1]["letzter_befund"] = "Y" * 1000
        sektion = pipeline._phase_stand_sektion(ps)
        assert "letzter Befund:" in sektion
        # Marker aus _truncate_mit_marker
        assert "Y" * 1000 not in sektion

    def test_planner_lauf_reicht_phase_stand_durch(self) -> None:
        import inspect
        sig = inspect.signature(pipeline._planner_lauf)
        assert "phase_stand" in sig.parameters
