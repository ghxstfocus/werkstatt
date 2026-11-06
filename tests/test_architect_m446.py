"""M-446-Regress-Schutz (2026-11-05).

Regress 2026-11-03: architect.py lud "using-werkstatt",
"plan-crafting", "commit-history". "plan-crafting" enthaelt
"## Tools" mit run_readonly(...) — deepseek-reasoner ruft Tools
und liefert DSML-Syntax statt Prosa.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def test_architect_laedt_keine_skills():
    """kein load_skill_by_name im architect.py-Quelltext."""
    src = Path("werkstatt/architect.py").read_text()
    assert "load_skill_by_name" not in src, (
        "M-446 verbietet Skills im Architect-Prompt. Regress-Schutz: "
        "kein load_skill_by_name in architect.py."
    )


def test_architect_prompt_ohne_plan_crafting():
    """Funktional: _planner_system enthaelt KEINE Skill- oder Tool-
    Referenzen. Explorer liefert WO, Scout liefert WAS, Architect
    liefert WIE — er misst NICHT selbst."""
    from werkstatt.architect import _planner_system

    st = mk_state(
        api_index_cache={},
        docs={},
        explorer_findings={},
        scout_api_auszug={},
    )
    prompt = _planner_system("test", {"key_files": []}, st)

    # Keine Tool-Definitionen
    for marker in ("## Tools", "run_readonly", "read_file", "write_file",
                   "<tools>", "grep"):
        assert marker.lower() not in prompt.lower(), (
            f"'{marker}' im Architect-Prompt — triggert DSML bei "
            f"deepseek-reasoner. Architect darf nicht messen."
        )

    # Keine Skill-Namen (auch nicht als Metadata-Liste)
    for marker in ("plan-crafting", "using-werkstatt", "commit-history",
                   "## verfuegbare skills", "## verfügbare skills"):
        assert marker.lower() not in prompt.lower(), (
            f"'{marker}' im Architect-Prompt — M-446-Verstoss. "
            f"Architect bekommt keine Skills, auch nicht als Liste."
        )
