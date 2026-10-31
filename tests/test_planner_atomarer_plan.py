"""Spec: Fix AY — atomarer Plan (Scout-Skip des Architect).

Deckt _tasks_aus_betroffenen_stellen: ein Task pro Datei mit allen
Scout-Stellen. Bei mehreren Dateien: leerer Plan (Fallback auf
Architect-Pfad).
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.planner import (
    _tasks_aus_betroffenen_stellen,
    run_planner,
)


class TestTasksAusStellen:
    def test_eine_datei_mehrere_stellen_ein_task(self) -> None:
        scout = {
            "atomarer_plan": True,
            "betroffene_stellen": [
                {"datei": "a.py", "zeile": 10, "alt": "x",
                 "neu": "y", "grund": "g1"},
                {"datei": "a.py", "zeile": 20, "alt": "p",
                 "neu": "q", "grund": "g2"},
                {"datei": "a.py", "zeile": 30, "alt": "r",
                 "neu": "s", "grund": "g3"},
            ],
        }
        tasks = _tasks_aus_betroffenen_stellen(scout, "aufgabe")
        assert len(tasks) == 1
        t = tasks[0]
        assert t["task_files"] == ["a.py"]
        assert t["action"] == "update"
        assert "Z. 10" in t["description"]
        assert "Z. 20" in t["description"]
        assert "Z. 30" in t["description"]

    def test_zwei_dateien_nicht_atomar(self) -> None:
        """Mehrere Dateien = nicht atomar -> Fallback auf Architect."""
        scout = {
            "atomarer_plan": True,
            "betroffene_stellen": [
                {"datei": "a.py", "zeile": 10, "alt": "x", "neu": "y"},
                {"datei": "b.py", "zeile": 5, "alt": "z", "neu": "w"},
            ],
        }
        assert _tasks_aus_betroffenen_stellen(scout, "aufgabe") == []

    def test_leere_stellen(self) -> None:
        scout = {"atomarer_plan": True, "betroffene_stellen": []}
        assert _tasks_aus_betroffenen_stellen(scout, "aufgabe") == []

    def test_fehlende_stellen(self) -> None:
        scout = {"atomarer_plan": True}
        assert _tasks_aus_betroffenen_stellen(scout, "aufgabe") == []

    def test_ungueltige_eintraege_ignoriert(self) -> None:
        scout = {
            "atomarer_plan": True,
            "betroffene_stellen": [
                "kein dict",
                {"datei": "a.py", "zeile": 10, "alt": "x", "neu": "y"},
                {"kein_datei": True},
                {"datei": "", "zeile": 20},
                {"datei": 123, "zeile": 30},
            ],
        }
        tasks = _tasks_aus_betroffenen_stellen(scout, "aufgabe")
        assert len(tasks) == 1
        assert "Z. 10" in tasks[0]["description"]
        assert "Z. 20" not in tasks[0]["description"]



class TestSkipArchitect:
    def test_atomarer_plan_ruft_keinen_architect(self, tmp_path) -> None:
        """Fix AY: atomarer_plan=True -> run_planner baut Task direkt
        aus betroffene_stellen, ohne Architect-LLM-Call."""
        st = SimpleNamespace(
            project_dir=tmp_path,
            project_name="testproj",
            api_key="sk-test",
            aufgabe="ersetze x durch y in a.py",
            docs=None,
            tasks=[],
            akzeptanzkriterien=[],
            preflight_fehler=None,
            explorer_ctx=None,
        )
        scout = {
            "atomarer_plan": True,
            "betroffene_stellen": [
                {"datei": "a.py", "zeile": 10, "alt": "x",
                 "neu": "y", "grund": "g1"},
                {"datei": "a.py", "zeile": 20, "alt": "p",
                 "neu": "q", "grund": "g2"},
            ],
        }
        with patch("werkstatt.planner._deterministic_entfernen_precheck",
                   return_value=False), \
             patch("werkstatt.planner._run_scout",
                   return_value=scout), \
             patch("werkstatt.planner.ask_llm") as _llm, \
             patch("werkstatt.planner.audit"):
            ok = run_planner(st)
        assert ok is True
        assert len(st.tasks) == 1
        assert st.tasks[0]["task_files"] == ["a.py"]
        assert "Z. 10" in st.tasks[0]["description"]
        assert "Z. 20" in st.tasks[0]["description"]
        # Beweis: kein Architect-LLM-Call.
        _llm.assert_not_called()
