import hashlib
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
        "EventStore.transition_run_status in werkstatt/web/inspector.py "
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
    assert methods["query"]["effects"] == "read"
    assert methods["transition_run_status"]["effects"] == "write"


def test_api_index_covers_javascript_and_java_declarations(tmp_path: Path) -> None:
    from werkstatt.scout import _baue_api_index, _finde_api

    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "overview.js").write_text(
        "function renderDonut(data) { return data; }\n",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "RunStats.java").write_text(
        "class RunStats {\n"
        " public int countRuns(String project) { return db.query(\"SELECT count(*)\"); }\n"
        "}\n",
        encoding="utf-8",
    )

    index = _baue_api_index(tmp_path)

    assert index["static/overview.js"]["language"] == "javascript"
    assert _finde_api(index, "renderDonut")[0]["pfad"] == "static/overview.js"
    assert index["src/RunStats.java"]["language"] == "java"
    assert _finde_api(index, "RunStats.countRuns")[0]["pfad"] == "src/RunStats.java"
    assert _finde_api(index, "RunStats.countRuns")[0]["effects"] == "read"


def test_preflight_accepts_source_verified_java_read_api(tmp_path: Path) -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen
    from werkstatt.scout import _baue_api_index

    java_path = tmp_path / "src" / "RunStats.java"
    java_path.parent.mkdir()
    java_path.write_text(
        "class RunStats {\n"
        " public int countRuns(String project) { return db.query(\"SELECT 1\"); }\n"
        "}\n",
        encoding="utf-8",
    )
    prose = (
        "## src/RunStats.java\n"
        "aggregate_status reads `RunStats.countRuns(project)`."
    )

    assert _pruefe_architect_api_referenzen(prose, _baue_api_index(tmp_path)) == []


def test_preflight_scopes_javascript_symbols_to_javascript_target() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    index = {
        "backend.py": {"functions": [{"name": "renderDonut", "effects": "read"}]},
        "static/overview.js": {
            "language": "javascript",
            "functions": [{"name": "renderDonut", "effects": "unknown"}],
        },
    }
    prose = "## static/overview.js\nRender the chart with `renderDonut(data)`."

    assert _pruefe_architect_api_referenzen(prose, index) == []


def test_preflight_does_not_borrow_api_from_other_language_without_heading() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    index = {
        "backend.py": {"functions": [{"name": "renderDonut", "effects": "read"}]},
        "static/overview.js": {"language": "javascript", "functions": []},
    }
    prose = (
        "Die UI-Datei static/overview.js soll `renderDonut(data)` aufrufen."
    )

    assert _pruefe_architect_api_referenzen(prose, index) == ["renderDonut"]


def test_preflight_deduplicates_repeated_effect_findings_and_ignores_dict_get() -> None:
    from werkstatt.architect import _pruefe_architect_api_referenzen

    index = {
        "store.py": {"functions": [], "classes": [{"name": "Store", "methods": [
            {"name": "get", "effects": "unknown"},
        ]}]},
    }
    prose = (
        "## api.py\n"
        "Die neue Funktion `aggregate_status()` liest `payload.get('kind')` "
        "und `payload.get('status')`."
    )

    assert _pruefe_architect_api_referenzen(prose, index) == []


def test_api_effect_recognizes_select_held_in_local_name(tmp_path: Path) -> None:
    from werkstatt.scout import _baue_api_index

    (tmp_path / "store.py").write_text(
        "class Store:\n"
        " def query(self):\n"
        "  sql = 'SELECT id FROM events'\n"
        "  return self.conn.execute(sql).fetchall()\n",
        encoding="utf-8",
    )
    index = _baue_api_index(tmp_path)
    query = index["store.py"]["classes"][0]["methods"][0]
    assert query["effects"] == "read"


def test_architect_revises_plan_after_api_preflight_rejection(monkeypatch, tmp_path) -> None:
    from werkstatt import architect

    target = tmp_path / "werkstatt" / "event_store.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        "class EventStore:\n"
        "    def get_run_record(self, run_id):\n"
        "        return self.connection.execute(run_id)\n",
        encoding="utf-8",
    )
    replies = iter([
        LLMReply(
            True,
            "## werkstatt/event_store.py\n"
            + "Nutze `EventStore.get_run_record()` fuer den Lauf. " * 4,
        ),
        LLMReply(True, "Nutze `EventStore.append(event)` fuer das vorhandene API. " * 4),
    ])
    prompts: list[str] = []
    contents: list[str] = []
    limits: list[int] = []

    def ask_llm(_key, system, content, **kwargs):
        prompts.append(system)
        contents.append(content)
        limits.append(kwargs["max_tokens"])
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
    assert "GEZIELTE KORREKTUR" in prompts[1]
    assert "im aktuellen AST" not in prompts[1]
    assert "ABGELEHNTER ARCHITECT-ENTWURF" in contents[1]
    assert "EventStore.get_run_record" in contents[1]
    assert "BEGRENZTE QUELLBELEGE" in contents[1]
    assert "def get_run_record(self, run_id)" in contents[1]
    assert "Zeilen 1-3" in contents[1]
    assert limits == [
        architect.ARCHITECT_MAX_TOKENS,
        architect.ARCHITECT_MAX_TOKENS,
    ]
    assert state.architect_prosa == (
        "Nutze `EventStore.append(event)` fuer das vorhandene API. " * 4
    ).strip()


def test_api_preflight_source_context_is_project_confined_and_bounded(tmp_path) -> None:
    from werkstatt.architect import _api_preflight_source_context

    root = tmp_path / "project"
    root.mkdir()
    safe = root / "werkstatt" / "safe.py"
    safe.parent.mkdir()
    safe.write_text(
        "class Store:\n    def load(self):\n        return 1\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside.py"
    outside.write_text("def load(): return 'outside'\n", encoding="utf-8")
    plan = "## werkstatt/safe.py\nUse `Store.load()`\n## ../outside.py\nUse `load()`"

    excerpt, metadata = _api_preflight_source_context(root, plan, [], max_chars=1200)

    assert "def load(self)" in excerpt
    assert "outside'" not in excerpt
    assert metadata["files"] == ["werkstatt/safe.py"]
    assert metadata["chars"] <= 1200


def test_api_preflight_retrieval_preserves_plan_path_order_and_reports_omissions(tmp_path) -> None:
    from werkstatt.architect import _api_preflight_source_context

    root = tmp_path / "project"
    first = root / "werkstatt" / "first.py"
    second = root / "werkstatt" / "second.py"
    first.parent.mkdir(parents=True)
    first.write_text("class Store:\n    def load(self):\n        return 1\n", encoding="utf-8")
    second.write_text("class Cache:\n    def load(self):\n        return 2\n", encoding="utf-8")
    plan = (
        "## werkstatt/second.py\nUse `Cache.load()`\n"
        "## werkstatt/first.py\nUse `Store.load()`"
    )

    excerpt, metadata = _api_preflight_source_context(root, plan, [], max_files=1)

    assert metadata["requested_files"] == ["werkstatt/second.py", "werkstatt/first.py"]
    assert metadata["files"] == ["werkstatt/second.py"]
    assert metadata["omitted_files"] == ["werkstatt/first.py"]
    assert "def load(self)" in excerpt
    assert "Retrieval-Auslassungen (keine Negativbelege)" in excerpt


def test_api_preflight_marks_unmatched_symbols_and_missing_files(tmp_path) -> None:
    from werkstatt.architect import _api_preflight_source_context

    root = tmp_path / "project"
    safe = root / "werkstatt" / "safe.py"
    safe.parent.mkdir(parents=True)
    safe.write_text("class Store:\n    def load(self):\n        return 1\n", encoding="utf-8")
    plan = (
        "## werkstatt/safe.py\nUse `Store.missing()`\n"
        "## werkstatt/not_found.py\nUse `Cache.load()`"
    )

    excerpt, metadata = _api_preflight_source_context(root, plan, [])

    assert metadata["unmatched_symbols"] == [{
        "path": "werkstatt/safe.py",
        "symbols": ["missing"],
        "searched_lines": 3,
    }]
    assert metadata["unreadable"] == [{
        "path": "werkstatt/not_found.py",
        "reason": "not_found",
    }]
    assert "kein Beleg fuer Nichtexistenz" in excerpt
    assert "Datei nicht gefunden" in excerpt


def test_api_preflight_never_slices_source_midline_at_budget(tmp_path) -> None:
    from werkstatt.architect import _api_preflight_source_context

    root = tmp_path / "project"
    target = root / "werkstatt" / "safe.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        "class Store:\n    def load(self):\n        return 'x' * 100\n",
        encoding="utf-8",
    )

    excerpt, metadata = _api_preflight_source_context(
        root, "## werkstatt/safe.py\nUse `Store.load()`", [], max_chars=350,
    )

    assert metadata["chars"] == len(excerpt) <= 350
    assert metadata["truncated"] is True
    assert "return 'x' * 100" not in excerpt
    assert metadata["omitted_files"] == ["werkstatt/safe.py"]


def test_execution_context_budget_keeps_sections_whole_and_reports_omissions() -> None:
    from werkstatt.planner import _budget_architect_execution_context

    context, metadata = _budget_architect_execution_context(
        [("PRIORITAET", "p" * 11000), ("NACHRANGIG", "n" * 2000)],
    )

    assert len(context) <= 12000
    assert "KONTEXT AUSGELASSEN (kein Negativbeleg): NACHRANGIG" in context
    assert "p" * 11000 in context
    assert "n" * 100 not in context
    assert metadata["included"] == ["PRIORITAET"]
    assert metadata["truncated"] == []
    assert metadata["omitted"] == ["NACHRANGIG"]
    sections = {item["name"]: item for item in metadata["section_manifest"]}
    included = sections["PRIORITAET"]
    start = included["prompt_start"]
    end = included["prompt_end"]
    assert context[start:end] == "## PRIORITAET\n" + "p" * 11000
    assert included["status"] == "included"
    assert included["sha256"] == hashlib.sha256(
        ("## PRIORITAET\n" + "p" * 11000).encode("utf-8"),
    ).hexdigest()
    omitted = sections["NACHRANGIG"]
    assert omitted["status"] == "omitted_optional"
    assert omitted["sha256"] == hashlib.sha256(
        ("## NACHRANGIG\n" + "n" * 2000).encode("utf-8"),
    ).hexdigest()
    assert "prompt_start" not in omitted

    tiny, tiny_metadata = _budget_architect_execution_context(
        [("PRIORITAET", "x" * 100)], max_chars=80,
    )
    assert len(tiny) <= 80
    assert tiny_metadata["chars"] == len(tiny)


def test_architect_execution_context_manifest_covers_all_included_sections() -> None:
    from werkstatt.planner import _budget_architect_execution_context

    context, metadata = _budget_architect_execution_context(
        [("ZIEL", "konkrete Aufgabe"), ("QUELLEN", "aktuelle Belege")],
    )

    for record in metadata["section_manifest"]:
        assert record["status"] == "included"
        start, end = record["prompt_start"], record["prompt_end"]
        section = context[start:end]
        assert hashlib.sha256(section.encode("utf-8")).hexdigest() == record["sha256"]


def test_architect_defensive_context_limit_is_audited(monkeypatch, tmp_path) -> None:
    from types import SimpleNamespace

    from werkstatt import architect

    captured: dict[str, object] = {}
    audits: list[tuple[str, dict]] = []

    class Reply:
        ok = True
        content = "Architect-Plan. " * 8

    def ask_llm(_key, _system, content, **_kwargs):
        captured["content"] = content
        return Reply()

    monkeypatch.setattr(architect, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(architect, "ask_llm", ask_llm)
    monkeypatch.setattr(architect, "audit", lambda kind, payload, *_a, **_k: audits.append((kind, payload)))
    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag={"auftrag_prosa": "Plan pruefen", "api_auszug": {}},
        architect_execution_context="x" * 13000,
    )

    assert not architect.run_architect(state, "Aufgabe", "nicht verwendet", "key", None)
    assert "content" not in captured
    blocked = [payload for kind, payload in audits if kind == "planner_architect_context_budget"]
    assert blocked[-1]["action"] == "blocked"
    assert blocked[-1]["required_context_complete"] is False


def test_scout_prompt_does_not_treat_index_absence_as_proof() -> None:
    from werkstatt.scout import SCOUT_SYSTEM

    assert "fehlender Indexeintrag ist kein Negativbeweis" in SCOUT_SYSTEM
    assert "JavaScript/Java" in SCOUT_SYSTEM
    assert "Fehlender oder gekuerzter Dateiinhalt erlaubt keine Aussage" in SCOUT_SYSTEM
    assert "nicht vollstaendigkeitsbeweisend" in SCOUT_SYSTEM


def test_architect_prompt_does_not_claim_unavailable_source_verification() -> None:
    from werkstatt.architect import ARCHITECT_SYSTEM

    assert "benenne die Belegluecke" in ARCHITECT_SYSTEM
    assert "Behaupte nicht, Dateien selbst gelesen" in ARCHITECT_SYSTEM
    assert "Index-Treffer ist kein Beweis der Nichtexistenz" in ARCHITECT_SYSTEM


def test_scout_handoff_preserves_every_reported_section_without_field_slices() -> None:
    import json

    from werkstatt.architect import _format_scout_auftrag

    report = {
        "auftrag_prosa": "P" * 3_500,
        "api_auszug": {
            f"pkg/module_{file_index}.py": [
                f"Symbol{file_index}_{symbol_index}" for symbol_index in range(6)
            ]
            for file_index in range(12)
        },
        "risiken": [f"Risiko {index}: " + "R" * 240 for index in range(12)],
        "api_widersprueche": [
            {"datei": "pkg/api.py", "symbol": f"missing_{index}"}
            for index in range(12)
        ],
    }

    rendered = _format_scout_auftrag(report)

    assert "P" * 3_500 in rendered
    assert "pkg/module_11.py: Symbol11_5" in rendered
    assert "Risiko 11: " + "R" * 240 in rendered
    assert json.dumps(
        report["api_widersprueche"], ensure_ascii=False,
    ) in rendered


def test_architect_blocks_oversized_complete_prompt_and_audits_handoff(
    monkeypatch, tmp_path,
) -> None:
    from types import SimpleNamespace

    from werkstatt import architect

    calls: list[object] = []
    audits: list[tuple[str, dict]] = []
    report = {
        "auftrag_prosa": "Pflichtkontext " * 5_000,
        "api_auszug": {},
        "risiken": [],
    }
    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag=report,
        architect_execution_context="",
        architect_execution_context_manifest={
            "max_chars": 12000,
            "chars": 240,
            "included": ["PHASE-STATE"],
            "truncated": [],
            "omitted": ["VORHERIGE FEHLSCHLAEGE"],
        },
    )
    monkeypatch.setattr(architect, "ask_llm", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(architect, "audit", lambda *a, **k: audits.append((a[0], a[1])))

    assert not architect.run_architect(state, "Aufgabe", "", "key", None)
    assert calls == []
    event = next(
        payload for kind, payload in audits
        if kind == "planner_architect_context_budget"
        and payload.get("scope") == "llm_request"
    )
    assert event["action"] == "blocked"
    assert event["required_context_complete"] is False
    assert event["scout_handoff_chars"] > 0
    assert len(event["scout_source_sha256"]) == 64


def test_architect_llm_receives_complete_scout_report_and_audits_its_hash(
    monkeypatch, tmp_path,
) -> None:
    import hashlib
    import json
    from types import SimpleNamespace

    from werkstatt import architect

    prosa = "Vollstaendige Scout-Anforderung " * 100
    report = {
        "auftrag_prosa": prosa,
        "api_auszug": {"pkg/target.py": [f"api_{index}" for index in range(30)]},
        "relevante_dateien": [{
            "pfad": "pkg/target.py",
            "zeilen": [25],
            "warum": "Scout hat die Zieldatei benannt",
        }],
        "risiken": [f"Risiko {index}: " + "R" * 240 for index in range(12)],
        "api_widersprueche": [
            {"datei": "pkg/api.py", "symbol": f"missing_{index}"}
            for index in range(12)
        ],
    }
    target = tmp_path / "pkg" / "target.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        "\n".join(
            f"line_{line}" + (" = 'live target evidence'" if line == 25 else "")
            for line in range(1, 51)
        ),
        encoding="utf-8",
    )
    captured: dict[str, str] = {}
    audits: list[tuple[str, dict]] = []

    class Reply:
        ok = True
        content = "Architect-Plan. " * 8

    def ask_llm(_key, system, _user, **_kwargs):
        captured["system"] = system
        captured["manifest"] = _kwargs.get("context_manifest")
        return Reply()

    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        api_index_cache={"already_built": True},
        docs={},
        scout_auftrag=report,
        architect_execution_context="",
        architect_execution_context_manifest={
            "max_chars": 12000,
            "chars": 240,
            "included": ["PHASE-STATE"],
            "truncated": [],
            "omitted": ["VORHERIGE FEHLSCHLAEGE"],
        },
    )
    monkeypatch.setattr(architect, "_with_spinner", lambda _label, call: call())
    monkeypatch.setattr(architect, "ask_llm", ask_llm)
    monkeypatch.setattr(
        architect, "audit", lambda kind, payload, *_a, **_k: audits.append((kind, payload)),
    )

    assert architect.run_architect(state, "Aufgabe", "", "key", None)
    prompt = captured["system"]
    assert prosa.strip() in prompt
    assert "api_29" in prompt
    assert "Risiko 11: " + "R" * 240 in prompt
    assert '"symbol": "missing_11"' in prompt
    assert "live target evidence" in prompt
    assert 'datei="pkg/target.py" zeilen="15-35"' in prompt

    canonical = json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    event = next(
        payload for kind, payload in audits
        if kind == "planner_architect_context_budget"
        and payload.get("scope") == "llm_request"
    )
    assert event["action"] == "send"
    assert event["required_context_complete"] is True
    assert event["scout_source_sha256"] == hashlib.sha256(
        canonical.encode("utf-8"),
    ).hexdigest()
    source = event["source_evidence"]["sources"][0]
    assert source["path"] == "pkg/target.py"
    assert source["included_ranges"] == [[15, 35]]
    assert source["source_sha256"] == hashlib.sha256(
        target.read_bytes(),
    ).hexdigest()
    manifest = captured["manifest"]
    assert isinstance(manifest, dict)
    assert manifest["budget_event"] == "planner_architect_context_budget"
    assert manifest["source_evidence"] == event["source_evidence"]
    assert manifest["scout_report_sha256"] == event["scout_source_sha256"]
    assert manifest["execution_context"] == state.architect_execution_context_manifest


def test_architect_source_retrieval_is_project_confined_and_marks_rejection(
    tmp_path,
) -> None:
    from werkstatt.architect import _format_scout_source_evidence

    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("SECRET_OUTSIDE = True\n", encoding="utf-8")
    report = {
        "relevante_dateien": [
            {"pfad": "../outside.py", "zeilen": [1]},
            {"pfad": str(tmp_path / "absolute.py"), "zeilen": [1]},
        ],
    }

    rendered, manifest = _format_scout_source_evidence(project, report)

    assert "SECRET_OUTSIDE" not in rendered
    assert "QUELLDATEIEN ABGELEHNT" in rendered
    assert manifest["included_files"] == []
    assert manifest["rejected_files"] == [
        {"path": "../outside.py", "reason": "unsafe_or_unsupported_path"},
        {
            "path": str(tmp_path / "absolute.py").replace("\\", "/"),
            "reason": "unsafe_or_unsupported_path",
        },
    ]


def test_architect_scout_source_budget_marks_omissions_and_stale_hints(
    tmp_path,
) -> None:
    from werkstatt.architect import _format_scout_source_evidence

    project = tmp_path / "project"
    project.mkdir()
    (project / "target.py").write_text(
        "def target():\n    return 'current'\n", encoding="utf-8",
    )
    rendered, manifest = _format_scout_source_evidence(
        project,
        {"relevante_dateien": [{
            "pfad": "target.py", "zeilen": [90],
        }]},
        max_files=1, max_chars=2_000,
    )

    assert len(rendered) <= 2_000
    assert "ausserhalb der aktuellen Datei" in rendered
    sources = manifest.get("sources")
    assert isinstance(sources, list) and sources
    assert isinstance(sources[0], dict)
    assert sources[0].get("unresolved_line_hints") == [90]
    block_start = sources[0]["context_start"]
    block_end = sources[0]["context_end"]
    excerpt = rendered[block_start:block_end]
    assert excerpt.startswith('<source datei="target.py"')
    assert excerpt.endswith("</source>")
    assert sources[0]["excerpt_chars"] == len(excerpt)
    assert sources[0]["excerpt_sha256"] == hashlib.sha256(
        excerpt.encode("utf-8"),
    ).hexdigest()
