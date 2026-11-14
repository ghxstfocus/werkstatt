from pathlib import Path
from types import SimpleNamespace

from werkstatt.state import LLMReply


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


def _api_index() -> dict:
    return {
        "werkstatt/event_store.py": {
            "functions": [],
            "classes": [{
                "name": "EventStore",
                "methods": [{
                    "name": "append", "args": ["self", "event"],
                    "return": "None", "effects": "write",
                }],
            }],
        },
    }


def test_architect_api_preflight_rejects_missing_existing_method() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    befund = _pruefe_architect_api_referenzen(
        "Nutze `EventStore.append(event)` und danach `EventStore.get_run_record()`.",
        _api_index(),
    )

    assert befund == ["EventStore.get_run_record"]


def test_architect_api_preflight_allows_explicitly_new_method() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    befund = _pruefe_architect_api_referenzen(
        "Die neue Methode `EventStore.get_run_record()` wird im EventStore "
        "implementiert und liefert den Run-Datensatz.",
        _api_index(),
    )

    assert befund == []


def test_architect_api_preflight_rejects_write_api_in_read_aggregate() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    index = {
        "werkstatt/event_store.py": {
            "functions": [],
            "classes": [{
                "name": "EventStore",
                "methods": [
                    {"name": "get_run_record", "args": ["self", "project", "run_id"], "effects": "read"},
                    {"name": "transition_run_status", "args": ["self", "project", "run_id"], "effects": "write"},
                ],
            }],
        },
    }
    prose = (
        "## werkstatt/web/inspector.py\n"
        "Neue Funktion `aggregate_ergebnisse(projekt)` liest Status. "
        "Sie ruft `EventStore.get_run_record(project, run_id)` und "
        "`EventStore.transition_run_status(project, run_id)` auf."
    )

    befund = _pruefe_architect_api_referenzen(prose, index)

    assert befund == [
        "EventStore.transition_run_status "
        + "(Effekt write in Read-Aggregator nicht als read belegt)"
    ]


def test_architect_api_preflight_rejects_unknown_effect_in_read_aggregate() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    index = {
        "werkstatt/store.py": {
            "functions": [],
            "classes": [{"name": "Store", "methods": [
                {"name": "load", "args": ["self"], "effects": "unknown"},
            ]}],
        },
    }
    prose = (
        "## werkstatt/web/inspector.py\n"
        "Die neue Funktion `aggregate_status()` ruft `Store.load()` auf."
    )

    befund = _pruefe_architect_api_referenzen(prose, index)

    assert len(befund) == 1
    assert "Effekt unknown" in befund[0]


def test_ast_index_proves_event_store_read_and_write_effects() -> None:
    from werkstatt.scout import _baue_api_index

    index = _baue_api_index(Path.cwd())
    methods = {
        method["name"]: method
        for cls in index["werkstatt/event_store.py"]["classes"]
        if cls["name"] == "EventStore"
        for method in cls["methods"]
    }

    assert methods["get_run_record"]["effects"] == "read"
    assert methods["transition_run_status"]["effects"] == "write"


def test_architect_revises_plan_after_api_preflight_rejection(monkeypatch, tmp_path) -> None:
    from werkstatt import architect

    replies = iter([
        LLMReply(True, "Nutze `EventStore.get_run_record()` fuer den Lauf. " * 4),
        LLMReply(True, "Nutze `EventStore.append(event)` fuer das vorhandene API. " * 4),
    ])
    prompts: list[str] = []

    def ask_llm(_key, system, *_args, **_kwargs):
        prompts.append(system)
        return next(replies)

    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache=_api_index(),
        scout_auftrag={},
        architect_execution_context="Auftrag pruefen.",
        architect_skills_block="",
    )
    monkeypatch.setattr(architect, "_planner_system", lambda *_args: "System")
    monkeypatch.setattr(architect, "_with_spinner", lambda _label, fn: fn())
    monkeypatch.setattr(architect, "ask_llm", ask_llm)
    monkeypatch.setattr(architect, "_strip_xml_tags", lambda value: value)
    monkeypatch.setattr(architect, "_get_architect_model", lambda: "test-model")
    monkeypatch.setattr(architect, "audit", lambda *_args, **_kwargs: None)

    assert architect.run_architect(state, "Aufgabe", "Kontext", "key", None)
    assert len(prompts) == 2
    assert "EventStore.get_run_record" in prompts[1]
    assert state.architect_prosa == (
        "Nutze `EventStore.append(event)` fuer das vorhandene API. " * 4
    ).strip()
