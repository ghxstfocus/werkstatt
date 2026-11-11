"""Tests fuer OP-231: read-only Tool-Registry."""
from __future__ import annotations

import pytest

from werkstatt import chat_tools

FORBIDDEN = {"write_file", "apply_patch", "git_commit",
             "shell_exec", "start_loop"}


def test_verbotene_tools_fehlen() -> None:
    for name in FORBIDDEN:
        assert name not in chat_tools.CHAT_TOOLS


def test_neun_soll_tools_vorhanden() -> None:
    erwartet = {
        "read_file", "grep", "git_log", "git_diff",
        "audit_query", "pytest_collect", "diagnose", "read_status", "next_op",
    }
    erwartet.add("request_loop_action")
    erwartet.update({"pytest_run", "write_temp_test"})
    assert set(chat_tools.CHAT_TOOLS) == erwartet


def test_debugger_tools_are_hidden_outside_debugger_mode() -> None:
    read_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="read")
    }
    debugger_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="debugger")
    }
    assert "pytest_run" not in read_names
    assert "write_temp_test" not in read_names
    assert {"pytest_run", "write_temp_test"} <= debugger_names
    assert len(read_names) == 10
    assert len(debugger_names) == 12


def test_openai_schemas_anzahl() -> None:
    schemas = chat_tools.openai_schemas()
    assert len(schemas) == 10
    for s in schemas:
        assert s["type"] == "function"
        assert s["function"]["name"] in chat_tools.CHAT_TOOLS


def test_read_file_blockt_ausserhalb() -> None:
    r = chat_tools.execute_tool("read_file", {"path": "/etc/passwd"})
    assert "Fehler" in r or "nicht" in r


def test_read_file_liest_projekt() -> None:
    r = chat_tools.execute_tool("read_file", {"path": "pyproject.toml"})
    assert len(r) > 0
    assert "Fehler" not in r[:80]


def test_grep_findet_pattern() -> None:
    r = chat_tools.execute_tool(
        "grep", {"pattern": "chat_loop", "path": "werkstatt/chat_agent.py"},
    )
    assert "chat_loop" in r


def test_grep_ohne_pattern() -> None:
    r = chat_tools.execute_tool("grep", {"pattern": ""})
    assert "Fehler" in r


def test_unknown_tool_liefert_fehlertext() -> None:
    r = chat_tools.execute_tool("write_file", {"path": "x", "content": "y"})
    assert "nicht in Registry" in r


def test_diagnose_liefert_json() -> None:
    r = chat_tools.execute_tool("diagnose", {})
    assert "bekannte_fehlerklassen" in r


def test_read_status_liefert_inhalt() -> None:
    r = chat_tools.execute_tool("read_status", {})
    assert "STATUS.md" in r or "PROGRESS.md" in r


def test_git_log_funktioniert() -> None:
    r = chat_tools.execute_tool("git_log", {"n": 3})
    assert len(r) > 0
    assert "Fehler" not in r[:80]


def test_mode_write_aktiviert_write_tools_nicht() -> None:
    """Heute gibt es keine write-Tools — Registry bleibt stabil."""
    schemas = chat_tools.openai_schemas(mode="write")
    assert len(schemas) == 10


def test_execute_tool_mit_mode_write_bei_read_tool() -> None:
    r = chat_tools.execute_tool("diagnose", {}, mode="write")
    assert "bekannte_fehlerklassen" in r



def test_chat_tools_isolate_project_roots(tmp_path) -> None:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    alpha.mkdir()
    beta.mkdir()
    (alpha / "secret.txt").write_text("alpha", encoding="utf-8")
    (beta / "secret.txt").write_text("beta", encoding="utf-8")

    assert chat_tools.execute_tool(
        "read_file", {"path": "secret.txt"},
        project_dir=alpha, project_name="alpha",
    ) == "alpha"
    assert chat_tools.execute_tool(
        "read_file", {"path": "secret.txt"},
        project_dir=beta, project_name="beta",
    ) == "beta"


def test_audit_query_rejects_other_project_run_id(tmp_path) -> None:
    tmp_path.mkdir(exist_ok=True)
    result = chat_tools.execute_tool(
        "audit_query", {"run_id": "beta-run-123"},
        project_dir=tmp_path, project_name="alpha",
    )
    assert "gehoert nicht zum aktiven Projekt" in result



def test_read_file_utf8_output_is_capped_even_with_large_end(tmp_path):
    datei = tmp_path / "large.txt"
    datei.write_text("ä" * (chat_tools._MAX_READ_BYTES + 10), encoding="utf-8")

    result = chat_tools.execute_tool(
        "read_file", {"path": "large.txt", "start": 0, "end": 1_000_000},
        project_dir=tmp_path,
    )

    assert result
    assert len(result.encode("utf-8")) <= chat_tools._MAX_READ_BYTES


def test_read_file_validiert_offsets_und_haelt_bereich_semantik(tmp_path):
    (tmp_path / "small.txt").write_text("alpha", encoding="utf-8")
    assert chat_tools.execute_tool(
        "read_file", {"path": "small.txt", "start": 1, "end": 4},
        project_dir=tmp_path,
    ) == "lph"
    assert "ungueltiger" in chat_tools.execute_tool(
        "read_file", {"path": "small.txt", "start": -1}, project_dir=tmp_path,
    )
    assert "ganze Zahlen" in chat_tools.execute_tool(
        "read_file", {"path": "small.txt", "start": "x"}, project_dir=tmp_path,
    )


def test_next_op_liest_aktives_projekt_und_startet_nichts(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Blockiert von:** —\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n",
        encoding="utf-8",
    )

    result = chat_tools.execute_tool(
        "next_op", {}, project_dir=tmp_path, project_name="demo",
    )

    assert '"zustand": "selected"' in result
    assert '"id": "OP-321"' in result
    assert '"quelle": "docs/STATUS.md"' in result



def test_next_op_resolves_completed_dependency_from_project_progress(
    tmp_path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-322: Arbeit nach erledigtem OP\n"
        "- **Status:** open\n"
        "- **Blockiert von:** OP-201\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_322.py\n",
        encoding="utf-8",
    )
    (tmp_path / "PROGRESS.md").write_text(
        "### 2026-11-07 — OP-201 abgeschlossen: Paket-Registrierung\n",
        encoding="utf-8",
    )

    result = chat_tools.execute_tool(
        "next_op", {}, project_dir=tmp_path, project_name="demo",
    )

    assert '"zustand": "selected"' in result
    assert '"id": "OP-322"' in result



def test_next_op_resolves_completed_dependency_from_status_autolog(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "- 2026-11-09 | OP-381c | done | Gate-Modal fertig.\n\n"
        "### OP-323: Folgearbeit\n"
        "- **Status:** open\n"
        "- **Blockiert von:** OP-381c\n"
        "- **Akzeptanzkriterien:** Ergebnis ist nachweisbar.\n"
        "- **Tests:** pytest -q tests/test_323.py\n",
        encoding="utf-8",
    )

    result = chat_tools.execute_tool(
        "next_op", {}, project_dir=tmp_path, project_name="demo",
    )

    assert '"zustand": "selected"' in result
    assert '"id": "OP-323"' in result


def test_loop_action_tool_only_persists_proposal_and_revalidates_op(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import chat_session

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n",
        encoding="utf-8",
    )
    db = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db)
    result = chat_tools.execute_tool(
        "request_loop_action", {"action": "start", "op_id": "OP-321"},
        project_dir=tmp_path, project_name="demo", session_id="session-1",
    )
    import json
    proposal = json.loads(result)
    assert proposal["zustand"] == "proposal"
    assert proposal["arguments"] == {"op_id": "OP-321"}
    assert "OP-321" in proposal["task_preview"]
    events = chat_session.ChatSession("demo", "session-1", db_pfad=db).load()
    assert [event["kind"] for event in events] == ["loop_action_proposed"]


def test_loop_action_proposal_requires_session_and_never_executes(tmp_path) -> None:
    import json

    result = chat_tools.execute_tool(
        "request_loop_action", {"action": "stop"}, project_dir=tmp_path,
    )
    assert json.loads(result)["zustand"] == "error"


@pytest.mark.parametrize(
    ("status_fields", "expected_detail"),
    [
        (
            """- **Status:** done
- **Akzeptanzkriterien:** Ergebnis belegbar.
- **Tests:** pytest -q tests/test_321.py
""",
            "nicht startfaehig",
        ),
        (
            """- **Status:** open
- **Akzeptanzkriterien:** Ergebnis belegbar.
""",
            "Tests oder ein pruefbarer Nachweis fehlen",
        ),
        (
            """- **Status:** open
- **Blockiert von:** OP-999
- **Akzeptanzkriterien:** Ergebnis belegbar.
- **Tests:** pytest -q tests/test_321.py
""",
            "Unbekannte oder widerspruechliche Blocker",
        ),
    ],
)
def test_loop_action_requires_startable_explicit_op(
    tmp_path, monkeypatch, status_fields: str, expected_detail: str,
) -> None:
    import json

    from werkstatt import chat_session

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n" + status_fields,
        encoding="utf-8",
    )
    db = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db)

    result = chat_tools.execute_tool(
        "request_loop_action", {"action": "start", "op_id": "OP-321"},
        project_dir=tmp_path, project_name="demo", session_id="session-2",
    )
    proposal = json.loads(result)

    assert proposal["zustand"] == "needs_input"
    assert expected_detail in proposal["detail"]
    assert not db.exists()


def test_pytest_run_requires_debugger_mode_and_project_path(
    tmp_path, monkeypatch,
) -> None:
    from types import SimpleNamespace

    calls = []
    monkeypatch.setattr(
        chat_tools.subprocess,
        "run",
        lambda *args, **kwargs: (
            calls.append((args, kwargs))
            or SimpleNamespace(returncode=0, stdout="2 passed", stderr="")
        ),
    )
    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_ok(): pass\n", encoding="utf-8")

    blocked = chat_tools.execute_tool(
        "pytest_run", {"path": "tests/test_sample.py"}, project_dir=tmp_path,
    )
    assert "erfordert mode='debugger'" in blocked

    result = chat_tools.execute_tool(
        "pytest_run", {"path": "tests/test_sample.py", "test": "test_ok"},
        mode="debugger", project_dir=tmp_path,
    )
    assert '"exit_code": 0' in result
    assert calls[0][0][0][0] == chat_tools.sys.executable
    assert str(test_file) in calls[0][0][0]
    assert calls[0][0][0][-2:] == ["-k", "test_ok"]
    assert calls[0][1]["timeout"] == 120
    assert "ausserhalb" in chat_tools.execute_tool(
        "pytest_run", {"path": "../outside.py"},
        mode="debugger", project_dir=tmp_path,
    )


def test_write_temp_test_is_confined_and_session_audited(tmp_path, monkeypatch) -> None:
    import json

    from werkstatt import chat_session

    monkeypatch.setattr(
        chat_session, "_db_pfad", lambda _project: tmp_path / "chat.db",
    )
    result = chat_tools.execute_tool(
        "write_temp_test", {"content": "def test_example(): pass\n"},
        mode="debugger", project_dir=tmp_path, project_name="demo",
        session_id="session-3",
    )
    data = json.loads(result)

    assert data["zustand"] == "created"
    path = tmp_path / data["path"]
    assert path.parent == tmp_path / ".werkstatt" / "temp_tests"
    assert path.is_file()
    assert not (tmp_path / "tests").exists()
    events = chat_session.ChatSession(
        "demo", "session-3", db_pfad=tmp_path / "chat.db",
    ).load()
    assert events[-1]["kind"] == "debug_temp_test_created"
    assert events[-1]["payload"]["path"] == data["path"]


def test_write_temp_test_rejects_large_content(tmp_path) -> None:
    result = chat_tools.execute_tool(
        "write_temp_test",
        {"content": "x" * 50_001},
        mode="debugger", project_dir=tmp_path,
    )
    assert "50 KB" in result
    assert not (tmp_path / ".werkstatt" / "temp_tests").exists()
