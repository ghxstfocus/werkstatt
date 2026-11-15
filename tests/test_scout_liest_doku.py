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
    preview = "\n".join(
        [f"{number:06d} | " + "P" * 100 for number in range(12, 89)]
        + [f"{number:06d} | " + "P" * 100 for number in range(220, 241)]
    )
    state = mk_state(
        project_dir=tmp_path,
        project_name="test",
        explorer_context={
            "key_files": [{
                "file": "src/core.py",
                "preview": preview,
                "source_line_ranges": [[12, 88], [220, 240]],
                "source_total_lines": 500,
                "source_complete": False,
                "preview_source_chars": len(preview),
                "source_sha256": "a" * 64,
            }],
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
    assert (
        "[FUNDSTELLE: src/core.py; Zeilen 12-84 von 500; "
        f"Volltextauszug=false; Auszug {len(preview)} Zeichen; "
        f"Quelldatei-SHA256={'a' * 64}]"
    ) in prompts[0]
    assert "QUELLTEXTAUSZUG GEKUERZT: Datei src/core.py" in prompts[0]
    assert (
        f"8000 von {len(preview)} Explorer-Zeichen"
    ) in prompts[0]
    assert "Fehlender Inhalt ist unbekannt" in prompts[0]


def test_scout_marks_explorer_phase_char_truncation(monkeypatch, tmp_path):
    preview = "000001 | " + "P" * 5_991
    state = mk_state(
        project_dir=tmp_path,
        project_name="test",
        explorer_context={
            "key_files": [{
                "file": "src/core.py",
                "preview": preview,
                "source_line_ranges": [[1, 1]],
                "source_total_lines": 200,
                "source_complete": False,
                "preview_source_chars": 12_000,
                "source_sha256": "b" * 64,
            }],
        },
    )
    prompts: list[str] = []
    monkeypatch.setattr(scout, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(
        scout,
        "ask_llm",
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
    assert "6000 von 12000 Zeichen des zeilennummerierten Auszuges" in prompts[0]
