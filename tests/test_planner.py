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
