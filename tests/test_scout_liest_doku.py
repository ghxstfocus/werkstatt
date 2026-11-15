"""Scout receives prioritized project documents through its budgeted context."""
from __future__ import annotations

import json
from types import SimpleNamespace

from tests.factories import mk_state
from werkstatt import scout


def test_scout_offers_status_and_adr_before_optional_project_docs(
    monkeypatch, tmp_path,
) -> None:
    docs = {
        name: f"Beleg aus {name}"
        for name in (
            "status", "adr_index", "architecture", "conventions",
            "entry", "roadmap", "glossary",
        )
    }
    state = mk_state(
        project_dir=tmp_path,
        project_name="test",
        docs=docs,
        explorer_context={
            "key_files": [{
                "file": "src/main.py",
                "preview": "def main(): return 0",
            }],
        },
    )
    offered: list[str] = []
    original_budget = scout._budget_scout_context

    def capture_budget(assignment, sections, **kwargs):
        offered.extend(title for title, _ in sections)
        return original_budget(assignment, sections, **kwargs)

    monkeypatch.setattr(scout, "_budget_scout_context", capture_budget)
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(
        scout, "ask_llm",
        lambda *_args, **_kwargs: SimpleNamespace(
            ok=True,
            content=json.dumps({
                "ziel": "Ziel", "relevante_dateien": [],
                "api_auszug": {}, "vorgeschlagene_aenderungen": [],
                "risiken": [], "auftrag_prosa": "Pruefe das Ziel.",
                "bereits_erfuellt": False,
            }),
        ),
    )
    monkeypatch.setattr(scout, "audit", lambda *_args, **_kwargs: None)

    result = scout._run_scout(
        state, "Pruefe das Projektziel", {}, [], "test-key",
    )

    assert result is not None
    assert offered[:2] == ["PROJEKT-DOKU: status", "PROJEKT-DOKU: adr_index"]
    assert offered[2].startswith("QUELLTEXT")
    assert offered[-5:] == [
        "PROJEKT-DOKU: architecture",
        "PROJEKT-DOKU: conventions",
        "PROJEKT-DOKU: entry",
        "PROJEKT-DOKU: roadmap",
        "PROJEKT-DOKU: glossary",
    ]


def test_scout_does_not_silently_pretruncate_project_docs(
    monkeypatch, tmp_path,
) -> None:
    long_status = "S" * 5_001
    state = mk_state(
        project_dir=tmp_path,
        project_name="test",
        docs={"status": long_status},
    )
    prompts: list[str] = []
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(
        scout, "ask_llm",
        lambda _key, _system, user, **_kwargs: (
            prompts.append(user) or SimpleNamespace(
                ok=True,
                content=json.dumps({
                    "ziel": "Ziel", "relevante_dateien": [],
                    "api_auszug": {}, "vorgeschlagene_aenderungen": [],
                    "risiken": [], "auftrag_prosa": "Pruefe das Ziel.",
                    "bereits_erfuellt": False,
                }),
            )
        ),
    )
    monkeypatch.setattr(scout, "audit", lambda *_args, **_kwargs: None)

    assert scout._run_scout(state, "Pruefe das Projektziel", {}, [], "key")
    assert len(prompts) == 1
    assert long_status in prompts[0]


def test_scout_preview_truncation_names_source_and_original_size(
    monkeypatch, tmp_path,
) -> None:
    state = mk_state(
        project_dir=tmp_path,
        project_name="test",
        explorer_context={
            "key_files": [{"file": "src/core.py", "preview": "P" * 9_001}],
        },
    )
    prompts: list[str] = []
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(
        scout, "ask_llm",
        lambda _key, _system, user, **_kwargs: (
            prompts.append(user) or SimpleNamespace(
                ok=True,
                content=json.dumps({
                    "ziel": "Ziel", "relevante_dateien": [],
                    "api_auszug": {}, "vorgeschlagene_aenderungen": [],
                    "risiken": [], "auftrag_prosa": "Pruefe das Ziel.",
                    "bereits_erfuellt": False,
                }),
            )
        ),
    )
    monkeypatch.setattr(scout, "audit", lambda *_args, **_kwargs: None)

    assert scout._run_scout(state, "Pruefe das Projektziel", {}, [], "key")
    assert len(prompts) == 1
    assert "QUELLTEXTAUSZUG GEKUERZT: Datei src/core.py" in prompts[0]
    assert "8000 von 9001 Zeichen" in prompts[0]
    assert "Fehlender Inhalt ist unbekannt" in prompts[0]
