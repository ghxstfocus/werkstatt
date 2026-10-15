"""Tests fuer den Projekt-Schema-Validator (pipeline.pruefe_projekt_yaml).

Prueft:
  - Pflichtfelder (K) werden erkannt.
  - Unbekannte Felder werden gemeldet.
  - Aliase (agents_dir, handoff, context_prompt) werden aufgeloest.
  - Defaults werden angewendet.
  - Warn-Modus blockiert nicht, Fail-Modus blockiert.
  - Typfehler werden erkannt.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

import pytest

import pipeline

# =====================================================================
# Hilfsfunktionen
# =====================================================================

def basis_config() -> dict:
    """Minimales gueltiges Projekt-Config (alle K gesetzt)."""
    return {
        "project": "test-projekt",
        "project_dir": "/tmp/test-projekt",
        "docs": {
            "decisions": "docs/DESIGN_DECISIONS.md",
            "workflow": "docs/WORKFLOW.md",
        },
        "always_run": ["py_compile"],
        "optional_catalog": ["read_file"],
        "agent_docs": {},
        "file_whitelist": ["core/"],
        "venv_python": "/tmp/test-projekt/.venv/bin/python3",
        "require_human_approval": True,
        "review_commit_package": True,
        "git_author": {"name": "test", "email": "test@example.com"},
    }


# =====================================================================
# Pflichtfelder
# =====================================================================

class TestPflichtfelder:
    def test_leere_config_meldet_pflichtfelder(self) -> None:
        meldungen = pipeline.pruefe_projekt_yaml({}, modus="warn")
        assert any("project" in m and "Pflichtfeld" in m for m in meldungen)
        assert any("project_dir" in m and "Pflichtfeld" in m for m in meldungen)

    def test_gueltige_config_keine_meldungen(self) -> None:
        cfg = basis_config()
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert meldungen == []

    def test_fehlendes_docs_decisions(self) -> None:
        cfg = basis_config()
        del cfg["docs"]["decisions"]
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("docs.decisions" in m and "Pflichtfeld" in m for m in meldungen)


# =====================================================================
# Unbekannte Felder
# =====================================================================

class TestUnbekannteFelder:
    def test_unbekanntes_top_feld(self) -> None:
        cfg = basis_config()
        cfg["zombie_feld"] = 1
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("zombie_feld" in m and "unbekannt" in m for m in meldungen)

    def test_unbekannter_docs_schluessel(self) -> None:
        cfg = basis_config()
        cfg["docs"]["zombie"] = "docs/Z.md"
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("docs.zombie" in m and "unbekannt" in m for m in meldungen)


# =====================================================================
# Aliase
# =====================================================================

class TestAliase:
    def test_agents_dir_aliased_zu_project_agents_dir(self) -> None:
        cfg = basis_config()
        cfg["agents_dir"] = "/tmp/agents"
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert "agents_dir" not in cfg
        assert cfg["project_agents_dir"] == "/tmp/agents"

    def test_docs_handoff_aliased_zu_reviewer(self) -> None:
        cfg = basis_config()
        cfg["docs"]["handoff"] = "docs/HANDOFF.md"
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert "handoff" not in cfg["docs"]
        assert cfg["docs"]["reviewer"] == "docs/HANDOFF.md"

    def test_docs_context_prompt_aliased_zu_context(self) -> None:
        cfg = basis_config()
        cfg["docs"]["context_prompt"] = "docs/CP.md"
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert "context_prompt" not in cfg["docs"]
        assert cfg["docs"]["context"] == "docs/CP.md"

    def test_alias_ueberschreibt_nicht_bestehendes_ziel(self) -> None:
        cfg = basis_config()
        cfg["docs"]["reviewer"] = "docs/NEU.md"
        cfg["docs"]["handoff"] = "docs/ALT.md"
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert cfg["docs"]["reviewer"] == "docs/NEU.md"
        # handoff bleibt als unbekannt stehen, wird gemeldet
        assert cfg["docs"]["handoff"] == "docs/ALT.md"


# =====================================================================
# Defaults
# =====================================================================

class TestDefaults:
    def test_budget_default_wird_gesetzt(self) -> None:
        cfg = basis_config()
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert cfg["budget"]["max_review_rounds"] == 5
        assert cfg["budget"]["max_llm_calls"] == 30

    def test_solver_default_wird_gesetzt(self) -> None:
        cfg = basis_config()
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert cfg["solver"]["p1_schwellwert"] == 0.5
        assert cfg["solver"]["max_runden"] == 3

    def test_default_ueberschreibt_nicht(self) -> None:
        cfg = basis_config()
        cfg["budget"] = {"max_review_rounds": 2}
        pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert cfg["budget"]["max_review_rounds"] == 2


# =====================================================================
# Modi
# =====================================================================

class TestModi:
    def test_warn_modus_blockiert_nicht(self) -> None:
        meldungen = pipeline.pruefe_projekt_yaml({}, modus="warn")
        assert len(meldungen) > 0

    def test_fail_modus_exit_2(self) -> None:
        with pytest.raises(SystemExit) as exc:
            pipeline.pruefe_projekt_yaml({}, modus="fail")
        assert exc.value.code == 2

    def test_fail_modus_gueltige_config(self) -> None:
        cfg = basis_config()
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="fail")
        assert meldungen == []


# =====================================================================
# Typen
# =====================================================================

class TestTypen:
    def test_project_muss_str_sein(self) -> None:
        cfg = basis_config()
        cfg["project"] = 42
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("project" in m and "Typ" in m for m in meldungen)

    def test_require_human_approval_muss_bool_sein(self) -> None:
        cfg = basis_config()
        cfg["require_human_approval"] = "ja"
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("require_human_approval" in m and "Typ" in m
                   for m in meldungen)

    def test_always_run_muss_list_str_sein(self) -> None:
        cfg = basis_config()
        cfg["always_run"] = [1, 2, 3]
        meldungen = pipeline.pruefe_projekt_yaml(cfg, modus="warn")
        assert any("always_run" in m and "Typ" in m for m in meldungen)
