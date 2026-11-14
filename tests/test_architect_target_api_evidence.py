from pathlib import Path
from types import SimpleNamespace


def test_scout_architect_prompt_includes_exact_target_api_signatures() -> None:
    from werkstatt.architect import _planner_system
    from werkstatt.scout import _baue_api_index

    status = (
        "### OP-374: Backfill\n"
        "- **Betroffene Dateien:** werkstatt/projection.py, "
        "werkstatt/web/inspector.py\n"
        "- **Tests:** tests/test_projection.py\n"
    )
    state = SimpleNamespace(
        aufgabe="Bearbeite OP-374",
        docs={"status": status},
        scout_auftrag={
            "auftrag_prosa": "Pruefe den Backfill.",
            "api_auszug": {
                "werkstatt\\projection.py": [
                    "Projector.tail(von_audit_id)",
                ],
                "werkstatt\\web\\inspector.py": [
                    "_letzter_run_id(es, projekt)",
                ],
            },
        },
        api_index_cache=_baue_api_index(Path.cwd()),
    )

    prompt = _planner_system("Bearbeite OP-374", state=state)

    assert "def tail(self, von_anfang) -> dict[str, int]" in prompt
    assert "def _connect(self)" not in prompt
    assert "Scout nennt: Projector.tail(von_audit_id)" in prompt
    assert "def _letzter_run_id(es, projekt) -> str | None" in prompt
    assert "secret_unrelated" not in prompt
    assert "Neue APIs duerfen vorgeschlagen werden" in prompt


def test_scout_api_evidence_rejects_traversal_and_bounds_signatures() -> None:
    from werkstatt.architect import _format_target_api_evidence

    functions = [
        {"name": f"api_{index}", "args": ["value"], "return": "str"}
        for index in range(100)
    ]
    state = SimpleNamespace(
        aufgabe="Aufgabe ohne OP",
        docs={},
        scout_auftrag={
            "relevante_dateien": [{"pfad": "../../outside.py"}],
            "api_auszug": {},
        },
        api_index_cache={"safe.py": {"functions": functions, "classes": []}},
    )

    evidence = _format_target_api_evidence(state, {
        "key_files": [{"file": "safe.py"}, {"file": "../outside.py"}],
    })

    assert "### safe.py" in evidence
    assert "outside.py" not in evidence
    assert "api_63" in evidence
    assert "api_64" not in evidence
    assert "Signaturauszug begrenzt" in evidence
