"""Tests fuer OP-231: chat_loop mit Mock-LLM."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from werkstatt import chat_agent
from werkstatt.chat_session import ChatSession


@pytest.fixture
def session(tmp_path: Path) -> ChatSession:
    return ChatSession("demo", "sess-1", db_pfad=tmp_path / "chat.db")


@pytest.fixture
def fake_llm(monkeypatch):
    antworten: list[dict[str, Any]] = []

    def _set(*items: dict[str, Any]) -> None:
        antworten.clear()
        antworten.extend(items)

    def _fake(messages, tools=None):
        if not antworten:
            raise AssertionError("fake_llm: keine Antwort mehr")
        return {"choices": [{"message": antworten.pop(0)}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _fake)
    return _set


def test_prompt_directs_recent_append_only_reads_to_tail_evidence():
    assert "read_file mit tail_chars" in chat_agent._SYSTEM_PROMPT
    assert "Eine gekuerzte oder partielle Ausgabe belegt niemals" in chat_agent._SYSTEM_PROMPT
    assert "Behaupte Vollstaendigkeit nur fuer den tatsaechlich gelesenen Bereich" in chat_agent._SYSTEM_PROMPT


def test_prompt_hands_implementation_requests_to_the_loop():
    prompt = chat_agent._SYSTEM_PROMPT
    assert "OP oder einen konkreten Projektauftrag bearbeiten" in prompt
    assert "rufe danach\nrequest_loop_action" in prompt
    assert "den Auftrag zu kopieren" in prompt
    assert "der Loop vor Schreibarbeit sein\nPlan-Gate zeigt" in prompt
    assert "Bei einer reinen Plan-/Analysefrage ohne Umsetzungswunsch" in prompt
    assert "niemals, einen Startvorschlag angelegt zu haben" in prompt
    assert 'zustand="proposal"' in prompt


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Bearbeite OP-372 vollstaendig nach den AK.", "OP-372"),
        ("Bitte OP-372 fixen und testen.", "OP-372"),
        ("Kannst du erklaeren, was OP-372 bedeutet?", None),
        ("Was macht OP-372?", None),
        ("Welche OP waere ein guter Test?", None),
        ("Bearbeite OP-372; OP-373 ist blockiert.", None),
    ],
)
def test_explicit_op_execution_intent_is_distinguished_from_questions(
    message: str, expected: str | None,
) -> None:
    assert chat_agent._explicit_op_execution_request(message) == expected


def test_chat_loop_can_handoff_explicit_op_implementation_request(
    session: ChatSession,
    fake_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from werkstatt import chat_session

    monkeypatch.setattr(
        chat_session,
        "_db_pfad",
        lambda _project: session.db_pfad,
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n",
        encoding="utf-8",
    )
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "start-op-321",
                "type": "function",
                "function": {
                    "name": "request_loop_action",
                    "arguments": json.dumps({
                        "action": "start",
                        "op_id": "OP-321",
                    }),
                },
            }],
        },
        {
            "role": "assistant",
            "content": "Der Loop-Start fuer OP-321 wartet auf deine Bestaetigung.",
        },
    )

    answer = chat_agent.chat_loop(
        session,
        "Bearbeite OP-321 nach den Akzeptanzkriterien.",
        project_dir=tmp_path,
    )

    assert "Startvorschlag fuer OP-321 ist im Chat" in answer
    proposal = next(
        event for event in session.load()
        if event["kind"] == "loop_action_proposed"
    )
    assert proposal["payload"]["arguments"] == {"op_id": "OP-321"}


def test_ambiguous_op_execution_request_asks_before_model_or_handoff(
    session: ChatSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected_model_call(*_args, **_kwargs):
        raise AssertionError("Mehrdeutiger OP-Auftrag darf nicht ans Modell gehen")

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _unexpected_model_call)

    answer = chat_agent.chat_loop(
        session,
        "Bearbeite OP-321; OP-322 ist blockiert.",
    )

    assert "OP-321, OP-322" in answer
    assert "Welche davon" in answer
    assert "keinen Startvorschlag angelegt" in answer
    assert not any(
        event["kind"] == "loop_action_proposed" for event in session.load()
    )


def test_explicit_op_request_retries_missing_tool_handoff(
    session: ChatSession,
    fake_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from werkstatt import chat_session

    monkeypatch.setattr(
        chat_session,
        "_db_pfad",
        lambda _project: session.db_pfad,
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n",
        encoding="utf-8",
    )
    fake_llm(
        {"role": "assistant", "content": "Ich habe keine Schreibwerkzeuge."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "start-op-321",
                "type": "function",
                "function": {
                    "name": "request_loop_action",
                    "arguments": json.dumps({
                        "action": "start",
                        "op_id": "OP-321",
                    }),
                },
            }],
        },
        {"role": "assistant", "content": "Vorschlag angelegt."},
    )
    results: list[dict[str, Any]] = []

    answer = chat_agent.chat_loop(
        session,
        "Bearbeite OP-321 vollstaendig.",
        project_dir=tmp_path,
        on_tool_result=lambda _name, content: results.append(json.loads(content)),
    )

    assert "Startvorschlag fuer OP-321 ist im Chat" in answer
    assert results[0]["zustand"] == "proposal"
    proposals = [
        event for event in session.load()
        if event["kind"] == "loop_action_proposed"
    ]
    assert len(proposals) == 1
    assert proposals[0]["payload"]["arguments"] == {"op_id": "OP-321"}


def test_explicit_op_request_never_claims_proposal_without_tool_evidence(
    session: ChatSession,
    fake_llm,
    tmp_path: Path,
) -> None:
    fake_llm(
        {"role": "assistant", "content": "Ich habe den Vorschlag erstellt."},
        {"role": "assistant", "content": "Vorschlag ist erstellt."},
    )

    answer = chat_agent.chat_loop(
        session,
        "Bearbeite OP-321 vollstaendig.",
        project_dir=tmp_path,
    )

    assert "keinen bestaetigten Loop-Startvorschlag erzeugt" in answer
    assert "Es wurde nichts gestartet" in answer
    assert not any(
        event["kind"] == "loop_action_proposed" for event in session.load()
    )


def test_explicit_op_request_rejects_handoff_for_different_op(
    session: ChatSession,
    fake_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from werkstatt import chat_session

    monkeypatch.setattr(
        chat_session,
        "_db_pfad",
        lambda _project: session.db_pfad,
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "STATUS.md").write_text(
        "### OP-321: Eindeutige Arbeit\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n"
        "\n"
        "### OP-322: Andere Arbeit\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Anderes Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_322.py\n",
        encoding="utf-8",
    )
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "start-op-322",
                "type": "function",
                "function": {
                    "name": "request_loop_action",
                    "arguments": json.dumps({
                        "action": "start",
                        "op_id": "OP-322",
                    }),
                },
            }],
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "start-op-321",
                "type": "function",
                "function": {
                    "name": "request_loop_action",
                    "arguments": json.dumps({
                        "action": "start",
                        "op_id": "OP-321",
                    }),
                },
            }],
        },
        {"role": "assistant", "content": "Start angefragt."},
    )
    results: list[dict[str, Any]] = []

    answer = chat_agent.chat_loop(
        session,
        "Bearbeite OP-321 vollstaendig.",
        project_dir=tmp_path,
        on_tool_result=lambda _name, content: results.append(json.loads(content)),
    )

    assert results[0]["zustand"] == "invalid"
    assert results[1]["zustand"] == "proposal"
    assert "Startvorschlag fuer OP-321 ist im Chat" in answer
    proposals = [
        event for event in session.load()
        if event["kind"] == "loop_action_proposed"
    ]
    assert len(proposals) == 1
    assert proposals[0]["payload"]["arguments"] == {"op_id": "OP-321"}


def test_chat_loop_reads_latest_append_only_entry_from_tail_evidence(
    session, tmp_path: Path, monkeypatch,
) -> None:
    path = tmp_path / "PROGRESS.md"
    path.write_text(
        "".join(f"historischer Eintrag {i:03d}\n" for i in range(80))
        + "2026-11-13 — neuester belegter Eintrag\n",
        encoding="utf-8",
    )
    calls = 0

    def _tail_then_answer(messages, tools=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            assert "tail_chars" in json.dumps(tools, ensure_ascii=False)
            assert "partielle Ausgabe belegt niemals" in messages[0]["content"]
            return {"choices": [{"message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "tail-1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({
                            "path": "PROGRESS.md",
                            "tail_chars": 128,
                        }),
                    },
                }],
            }}]}
        evidence = messages[-1]["content"]
        assert "Dateiende-Auszug:" in evidence
        assert "neuester belegter Eintrag" in evidence
        assert "historischer Eintrag 000" not in evidence
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Der neueste belegte Eintrag ist vom 2026-11-13.",
        }}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _tail_then_answer)
    answer = chat_agent.chat_loop(
        session,
        "Lies den neuesten Eintrag in PROGRESS.md.",
        project_dir=tmp_path,
    )

    assert answer == "Der neueste belegte Eintrag ist vom 2026-11-13."
    assert calls == 2


def test_chat_loop_ohne_tool(session, fake_llm) -> None:
    fake_llm({"role": "assistant", "content": "Hallo!"})
    antwort = chat_agent.chat_loop(session, "Hi")
    assert antwort == "Hallo!"
    evs = session.load()
    assert [e["kind"] for e in evs] == ["user", "assistant"]
    assert evs[0]["payload"]["text"] == "Hi"
    assert evs[1]["payload"]["text"] == "Hallo!"


def test_chat_loop_mit_tool_call(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "pyproject.toml"}),
                },
            }],
        },
        {"role": "assistant", "content": "Datei gelesen."},
    )
    antwort = chat_agent.chat_loop(session, "Was steht drin?")
    assert "gelesen" in antwort
    kinds = [e["kind"] for e in session.load()]
    assert kinds == ["user", "tool_call", "tool_result", "assistant"]
    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert tr["payload"]["tool_call_id"] == "c1"
    assert tr["payload"]["name"] == "read_file"
    assert len(tr["payload"]["content"]) > 0


def test_repeated_tool_cycle_detects_alternating_stagnation() -> None:
    assert chat_agent._repeated_tool_cycle(["a", "b", "a", "b"]) == ("a", "b")
    assert chat_agent._repeated_tool_cycle(["a", "b", "a"]) is None
    assert chat_agent._repeated_tool_cycle(["a", "a"]) == ("a",)


def test_chat_loop_beendet_wiederkehrenden_abwechselnden_toolzyklus(
    session, fake_llm, tmp_path: Path,
) -> None:
    def _tool_call(name: str, call_id: str) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": "{}"},
            }],
        }

    tools = {
        "read_a": {
            "description": "Read fixture A.",
            "parameters": {"type": "object", "properties": {}},
            "fn": lambda _args: "Evidence A",
            "mode": "read",
        },
        "read_b": {
            "description": "Read fixture B.",
            "parameters": {"type": "object", "properties": {}},
            "fn": lambda _args: "Evidence B",
            "mode": "read",
        },
    }
    fake_llm(
        _tool_call("read_a", "a1"),
        _tool_call("read_b", "b1"),
        _tool_call("read_a", "a2"),
        _tool_call("read_b", "b2"),
        _tool_call("read_a", "a3"),
        _tool_call("read_b", "b3"),
        {"role": "assistant", "content": "Belegte Antwort mit offenem Punkt."},
    )

    answer = chat_agent.chat_loop(
        session, "Pruefe diesen Auftrag", tools=tools, project_dir=tmp_path,
    )

    assert answer == "Belegte Antwort mit offenem Punkt."
    assert session.load()[-1]["payload"]["text"] == answer


def test_chat_loop_stagnation_liefert_belegte_antwort(session, fake_llm) -> None:
    wieder = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "cx",
            "type": "function",
            "function": {"name": "diagnose", "arguments": "{}"},
        }],
    }
    fake_llm(
        wieder, wieder, wieder,
        {"role": "assistant", "content": "Ich habe den Status geprueft."},
    )
    antwort = chat_agent.chat_loop(session, "Pruefe den Status")

    assert antwort == "Ich habe den Status geprueft."
    assert "max_rounds" not in antwort
    assert session.load()[-1]["payload"]["text"] == antwort


def test_chat_loop_standard_laeuft_ueber_fuenf_toolrunden(
    session, fake_llm, tmp_path: Path,
) -> None:
    tool_calls = []
    for index in range(6):
        name = f"status-{index}.txt"
        (tmp_path / name).write_text(f"Beleg {index}", encoding="utf-8")
        tool_calls.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": f"read-{index}",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": name}),
                },
            }],
        })
    fake_llm(
        *tool_calls,
        {"role": "assistant", "content": "Alle sechs Belege sind gelesen."},
    )

    antwort = chat_agent.chat_loop(
        session, "Pruefe den Fortschritt", project_dir=tmp_path,
    )

    assert antwort == "Alle sechs Belege sind gelesen."
    results = [event for event in session.load() if event["kind"] == "tool_result"]
    assert len(results) == 6
    assert {event["payload"]["content"] for event in results} == {
        f"Beleg {index}" for index in range(6)
    }


def test_chat_loop_unbekanntes_tool(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "bad",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": json.dumps({"path": "x"}),
                },
            }],
        },
        {"role": "assistant", "content": "Konnte nicht schreiben."},
    )
    chat_agent.chat_loop(session, "schreib")
    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert "nicht in Registry" in tr["payload"]["content"]


def test_chat_loop_ungueltiges_json_im_tool_call(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "u1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": "KEIN JSON",
                },
            }],
        },
        {"role": "assistant", "content": "ok"},
    )
    antwort = chat_agent.chat_loop(session, "x")
    assert antwort == "ok"


def test_on_chunk_callback_wird_gerufen(session, fake_llm) -> None:
    fake_llm({"role": "assistant", "content": "Antwort"})
    chunks: list[str] = []
    chat_agent.chat_loop(session, "x", on_chunk=chunks.append)
    assert chunks == ["Antwort"]


def test_on_tool_callbacks(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "pyproject.toml"}),
                },
            }],
        },
        {"role": "assistant", "content": "done"},
    )
    calls: list[tuple[str, dict]] = []
    results: list[tuple[str, str]] = []
    chat_agent.chat_loop(
        session, "x",
        on_tool_call=lambda n, a: calls.append((n, a)),
        on_tool_result=lambda n, r: results.append((n, r)),
    )
    assert calls and calls[0][0] == "read_file"
    assert calls[0][1] == {"path": "pyproject.toml"}
    assert results and results[0][0] == "read_file"
    assert len(results[0][1]) > 0


def test_baue_messages_aus_session(session) -> None:
    session.append("user", {"text": "a"})
    session.append("assistant", {"text": "b"})
    session.append("job_turn", {
        "job_id": "job-1",
        "user_text": "c",
        "assistant_text": "d",
    })
    msgs = chat_agent._baue_messages(session.load())
    assert msgs == [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
        {"role": "assistant", "content": "d"},
    ]

def test_chat_tool_uses_explicit_project_root(session, fake_llm, tmp_path) -> None:
    (tmp_path / "project-only.txt").write_text(
        "ausgewaehltes Projekt", encoding="utf-8",
    )
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "project-read",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "project-only.txt"}),
                },
            }],
        },
        {"role": "assistant", "content": "gelesen"},
    )

    chat_agent.chat_loop(
        session, "lies die Datei",
        project_dir=tmp_path,
    )

    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert tr["payload"]["content"] == "ausgewaehltes Projekt"


def test_system_prompt_routes_next_work_questions_through_selector() -> None:
    assert "next_op" in chat_agent._SYSTEM_PROMPT
    assert "Bei Mehrdeutigkeit fragst du" in chat_agent._SYSTEM_PROMPT
    assert "veraendert nichts" in chat_agent._SYSTEM_PROMPT


def test_system_prompt_requires_exact_op_evidence_before_planning() -> None:
    assert "read_status mit genau dieser op_id" in chat_agent._SYSTEM_PROMPT
    assert "STATUS-Auszug" in chat_agent._SYSTEM_PROMPT
    assert "nie durch Erinnerung" in chat_agent._SYSTEM_PROMPT
    assert "passende akzeptierte ADRs" in chat_agent._SYSTEM_PROMPT
    assert "explizit genannten Pfade" in chat_agent._SYSTEM_PROMPT
    assert "nicht nach einem Modulnamen" in chat_agent._SYSTEM_PROMPT
    assert "verifizierter positiver Treffer wiegt staerker" in chat_agent._SYSTEM_PROMPT
    assert "lies" in chat_agent._SYSTEM_PROMPT and "read_file" in chat_agent._SYSTEM_PROMPT

def test_system_prompt_requires_verified_file_line_citations() -> None:
    assert "grep" in chat_agent._SYSTEM_PROMPT
    assert "Zeichen-Offsets und keine Zeilennummern" in chat_agent._SYSTEM_PROMPT
    assert "Erfinde keine Zeilenangaben" in chat_agent._SYSTEM_PROMPT

def test_chat_loop_cancelled_before_request_does_not_call_llm(session) -> None:
    with pytest.raises(chat_agent.ChatCancelled):
        chat_agent.chat_loop(
            session, "Abbrechen", cancel_check=lambda: True,
        )

    assert session.load() == []

def test_chat_stream_stops_when_cancel_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = pytest.importorskip("requests")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    checks = 0

    def _cancel() -> bool:
        nonlocal checks
        checks += 1
        return checks >= 3

    class _Response:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            yield b"data: {}"
            yield b"data: {}"

    response = _Response()
    monkeypatch.setattr(requests, "post", lambda *_args, **_kwargs: response)

    with pytest.raises(chat_agent.ChatCancelled):
        chat_agent._deepseek_chat_stream([], cancel_check=_cancel)

    assert response.closed is True



def test_debugger_mode_is_recorded_and_adds_debugger_only_tools(
    session, fake_llm, monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def _capture(messages, tools=None):
        requests_seen.append((messages, tools or []))
        return {"choices": [{"message": {"role": "assistant", "content": "Diagnose."}}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _capture)
    chat_agent.chat_loop(session, "Untersuche den Fehler", mode="debugger")

    system_prompt = requests_seen[0][0][0]["content"]
    tool_names = {
        item["function"]["name"] for item in requests_seen[0][1]
    }
    user_event = next(event for event in session.load() if event["kind"] == "user")
    assert "write_temp_test" in system_prompt
    assert "pytest_run" in tool_names
    assert "read_file" in tool_names
    assert user_event["payload"]["mode"] == "debugger"


def test_chat_loop_explizites_rundenbudget_liefert_abschluss(
    session: ChatSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "status.txt").write_text("Run-Status: bereit", encoding="utf-8")
    requests_seen: list[tuple[list[dict[str, Any]], list[dict[str, Any]] | None]] = []

    def _fake_llm(messages, tools=None, cancel_check=None):
        requests_seen.append((messages, tools))
        if len(requests_seen) == 1:
            return {"choices": [{"message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "read-status",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "status.txt"}),
                    },
                }],
            }}]}
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Der belegte Status ist bereit.",
        }}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _fake_llm)
    antwort = chat_agent.chat_loop(
        session, "Pruefe den Status", max_rounds=1, project_dir=tmp_path,
    )

    assert antwort == "Der belegte Status ist bereit."
    assert len(requests_seen) == 2
    assert requests_seen[0][1] is not None
    assert requests_seen[1][1] is None
    assert "Obergrenze angekommen" in requests_seen[1][0][-1]["content"]
    assert session.load()[-1]["payload"]["text"] == antwort


def test_chat_loop_default_laeuft_ueber_fuenf_werkzeugrunden_weiter(
    session: ChatSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Der normale Chat-Turn hat keine pauschale Fuenf-Runden-Grenze."""
    calls = 0
    tools = {
        "probe": {
            "description": "Liefert den angefragten Beleg.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
            },
            "fn": lambda args: f"Beleg {args['n']}",
            "mode": "read",
        },
    }

    def _fake_llm(messages, tools=None, cancel_check=None):
        nonlocal calls
        calls += 1
        if calls <= 7:
            return {"choices": [{"message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": f"probe-{calls}",
                    "type": "function",
                    "function": {
                        "name": "probe",
                        "arguments": json.dumps({"n": calls}),
                    },
                }],
            }}]}
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Sieben Belege geprueft; der Auftrag ist beantwortet.",
        }}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _fake_llm)
    answer = chat_agent.chat_loop(
        session, "Pruefe sieben Belege", tools=tools, project_dir=tmp_path,
    )

    assert calls == 8
    assert answer == "Sieben Belege geprueft; der Auftrag ist beantwortet."
    assert sum(event["kind"] == "tool_call" for event in session.load()) == 7


def test_chat_loop_abbruch_nach_werkzeugschritt_bleibt_replaybar(
    session: ChatSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "status.txt").write_text("Run-Status: bereit", encoding="utf-8")
    cancel_checks = 0
    llm_calls = 0

    def _cancel() -> bool:
        nonlocal cancel_checks
        cancel_checks += 1
        return cancel_checks >= 4

    def _fake_llm(messages, tools=None, cancel_check=None):
        nonlocal llm_calls
        llm_calls += 1
        return {"choices": [{"message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "read-status",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "status.txt"}),
                },
            }],
        }}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _fake_llm)
    with pytest.raises(chat_agent.ChatCancelled):
        chat_agent.chat_loop(
            session,
            "Pruefe den Status",
            project_dir=tmp_path,
            cancel_check=_cancel,
        )

    assert llm_calls == 1
    events = session.load()
    assert [event["kind"] for event in events] == [
        "user", "tool_call", "tool_result",
    ]
    assert events[-1]["payload"]["content"] == "Run-Status: bereit"


def test_chat_history_omits_old_tool_traces_but_keeps_current_evidence() -> None:
    events = [
        {"kind": "user", "payload": {"text": "alte Frage"}},
        {"kind": "tool_call", "payload": {"tool_calls": [{"id": "old", "function": {"name": "read_file", "arguments": "{}"}}]}},
        {"kind": "tool_result", "payload": {"tool_call_id": "old", "content": "ALTE ROHAUSGABE"}},
        {"kind": "assistant", "payload": {"text": "Alter Befund"}},
        {"kind": "user", "payload": {"text": "aktuelle Frage"}},
        {"kind": "tool_call", "payload": {"tool_calls": [{"id": "new", "function": {"name": "read_file", "arguments": "{}"}}]}},
        {"kind": "tool_result", "payload": {"tool_call_id": "new", "content": "AKTUELLER BELEG"}},
    ]
    original = [dict(event) for event in events]

    messages = chat_agent._baue_messages(events)
    serialized = json.dumps(messages, ensure_ascii=False)

    assert "ALTE ROHAUSGABE" not in serialized
    assert "Alter Befund" in serialized
    assert "AKTUELLER BELEG" in serialized
    assert events == original


def test_chat_history_truncation_obeys_character_budget(monkeypatch) -> None:
    monkeypatch.setattr(chat_agent, "_CHAT_HISTORY_CHAR_BUDGET", 80)
    events = [
        {"kind": "user", "payload": {"text": "U" * 500}},
        {"kind": "assistant", "payload": {"text": "A" * 500}},
        {"kind": "user", "payload": {"text": "aktuelle Aufgabe"}},
    ]

    messages = chat_agent._baue_messages(events)
    prior = [message for message in messages[:-1] if message.get("role") != "system"]

    assert sum(len(str(message.get("content") or "")) for message in prior) <= 80
    assert messages[-1] == {"role": "user", "content": "aktuelle Aufgabe"}
    assert chat_agent._CHAT_HISTORY_COMPACT_NOTE in messages[0]["content"]


def test_active_tool_context_is_bounded_and_latest_evidence_survives() -> None:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "do the work"},
    ]
    for index in range(8):
        tool_id = f"tool-{index}"
        messages.extend([
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": f"file-{index}.py"}),
                    },
                }],
            },
            {
                "role": "tool",
                "tool_call_id": tool_id,
                "content": f"BEGIN-{index} " + ("x" * 5000) + f" END-{index}",
            },
        ])
    original = json.loads(json.dumps(messages))

    compacted = chat_agent._begrenze_aktiven_turn(messages, 1)
    active = compacted[2:]
    active_size = sum(chat_agent._message_size(message) for message in active)
    serialized = json.dumps(compacted, ensure_ascii=False)

    assert active_size <= chat_agent._CHAT_ACTIVE_TOOL_CHAR_BUDGET
    assert "END-7" in serialized
    assert "BEGIN-0" in serialized
    assert messages == original
    assert len(compacted) < len(messages)

