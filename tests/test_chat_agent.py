"""Tests fuer werkstatt.web.chat_agent (OP-084 + OP-085).

LLM-First-Architektur: die meisten Tests mocken _deepseek_chat und
prüfen den Tool-Loop. Fast-Path (!cmd, starte Loop) wird direkt getestet.
"""
from __future__ import annotations

import json

import pytest

from werkstatt.web import chat_agent, shell


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "STATUS.md").write_text(
        "### OP-100: Test-OP Eins\n- **Status:** open\n\n"
        "### OP-101: Test-OP Zwei\n- **Status:** open\n\n"
        "## Erledigt (Auto-Log)\n",
        encoding="utf-8",
    )
    (tmp_path / "test.py").write_text(
        "def foo():\n    return 42\n", encoding="utf-8"
    )
    chat_agent.init(tmp_path)
    monkeypatch.setattr(shell, "_AKTIVE_PTYS", {})
    yield tmp_path
    shell._AKTIVE_PTYS.clear()


def _mock_response(content: str = "", tool_calls: list | None = None) -> dict:
    """Baut eine DeepSeek-Response."""
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"choices": [{"message": msg}]}


def _tool_call(name: str, args: dict, call_id: str = "tc1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


# --- Fast-Path ---

def test_bang_prefix_shell(monkeypatch, tmp_project):
    """!-Prefix erzwingt Shell."""
    class FakeSession:
        def __init__(self):
            self.cmds = []
        def inject(self, cmd):
            self.cmds.append(cmd)
            return True
    fake = FakeSession()
    monkeypatch.setattr(shell, "_AKTIVE_PTYS", {"werkstatt": fake})
    a = chat_agent.verarbeite("!ls -la")
    assert "$ ls -la" in a
    assert fake.cmds == ["ls -la"]


def test_bang_mehrzeiler_subprocess(tmp_project):
    """! mit Mehrzeiler -> subprocess, Exit-Code sichtbar."""
    a = chat_agent.verarbeite("!echo A\necho B")
    assert "Exit: 0" in a
    assert "A" in a


def test_starte_loop_fast_path(monkeypatch, tmp_project):
    """'starte Loop mit OP-101' -> deterministischer Start."""
    started = []
    class FakeProc:
        pid = 9999
    def fake_popen(cmd, **kw):
        started.append(cmd)
        return FakeProc()
    monkeypatch.setattr(chat_agent.subprocess, "Popen", fake_popen)
    a = chat_agent.verarbeite("starte Loop mit OP-101")
    assert "Loop gestartet" in a
    assert "OP-101" in a
    assert len(started) == 1


# --- LLM-First mit Tools ---

def test_llm_direkt_ohne_tool(monkeypatch, tmp_project):
    """Freie Frage -> LLM antwortet ohne Tools."""
    def fake_chat(messages, tools=None):
        return _mock_response("Hallo, ich bin da.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("hallo")
    assert a == "Hallo, ich bin da."


def test_llm_ruft_list_open_ops(monkeypatch, tmp_project):
    """'nächste offene OP' -> LLM ruft list_open_ops, antwortet mit einer OP."""
    calls = []
    def fake_chat(messages, tools=None):
        calls.append((messages, tools))
        if len(calls) == 1:
            # LLM will Tool list_open_ops
            return _mock_response(tool_calls=[_tool_call("list_open_ops", {})])
        # Zweite Runde: LLM hat Tool-Result, antwortet
        return _mock_response("Die nächste offene OP ist OP-100.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("Was ist die nächste offene OP")
    assert "OP-100" in a
    # Tools wurden gesendet
    assert calls[0][1] is not None
    # Tool-Result in messages der zweiten Runde
    assert any(m.get("role") == "tool" for m in calls[1][0])


def test_llm_ruft_read_file(monkeypatch, tmp_project):
    """'was steht in test.py' -> read_file."""
    calls = []
    def fake_chat(messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            return _mock_response(tool_calls=[_tool_call("read_file", {"path": "test.py"})])
        # Prüfen dass Tool-Result in messages
        tool_msg = next((m for m in messages if m.get("role") == "tool"), None)
        assert tool_msg is not None
        assert "return 42" in tool_msg["content"]
        return _mock_response("In test.py steht eine Funktion foo() die 42 zurückgibt.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("was steht in test.py")
    assert "foo" in a


def test_llm_ruft_grep(monkeypatch, tmp_project):
    """'suche return 42' -> grep."""
    calls = []
    def fake_chat(messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            return _mock_response(tool_calls=[_tool_call("grep", {"pattern": "return 42"})])
        return _mock_response("Gefunden in test.py:2.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("suche return 42")
    assert "test.py" in a


def test_llm_ruft_shell_exec(monkeypatch, tmp_project):
    """'git status' via Tool -> shell_exec, Exit sichtbar."""
    calls = []
    def fake_chat(messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            return _mock_response(tool_calls=[_tool_call("shell_exec", {"cmd": "echo HELLO"})])
        tool_msg = next((m for m in messages if m.get("role") == "tool"), None)
        assert "HELLO" in tool_msg["content"]
        return _mock_response("Befehl lief durch.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("echo HELLO")
    assert "lief durch" in a


def test_llm_tool_error_wird_gefangen(monkeypatch, tmp_project):
    """Tool-Crash -> Fehlertext an LLM, keine Exception."""
    calls = []
    def fake_chat(messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            return _mock_response(tool_calls=[_tool_call("read_file", {"path": "nixda.py"})])
        tool_msg = next((m for m in messages if m.get("role") == "tool"), None)
        assert "existiert nicht" in tool_msg["content"]
        return _mock_response("Datei existiert nicht.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("lies nixda.py")
    assert "existiert nicht" in a


def test_llm_kein_api_key(monkeypatch, tmp_project):
    """Ohne DEEPSEEK_API_KEY -> Fehlermeldung, kein Crash."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    def fake_chat(messages, tools=None):
        raise RuntimeError("DEEPSEEK_API_KEY nicht gesetzt.")
    monkeypatch.setattr(chat_agent, "_deepseek_chat", fake_chat)
    a = chat_agent.verarbeite("hallo")
    assert "LLM-Fehler" in a


def test_tool_read_file_traversal_blocked(tmp_project):
    """read_file mit ../ -> Fehler."""
    r = chat_agent._tool_read_file({"path": "../../../etc/passwd"})
    assert "FEHLER" in r
    assert "ausserhalb" in r


def test_tool_read_file_fehlend(tmp_project):
    r = chat_agent._tool_read_file({"path": "nixda.py"})
    assert "FEHLER" in r


def test_tool_shell_exec_subprocess(tmp_project):
    """Ohne Session -> subprocess, Exit im Output."""
    r = chat_agent._tool_shell_exec({"cmd": "echo M1"})
    assert "Exit: 0" in r
    assert "M1" in r


def test_tool_shell_exec_mit_session(monkeypatch, tmp_project):
    class FakeSession:
        def __init__(self):
            self.cmds = []
        def inject(self, cmd):
            self.cmds.append(cmd)
            return True
    fake = FakeSession()
    monkeypatch.setattr(shell, "_AKTIVE_PTYS", {"werkstatt": fake})
    r = chat_agent._tool_shell_exec({"cmd": "ls"})
    assert "ausgefuehrt in aktiver Shell" in r
    assert fake.cmds == ["ls"]


def test_tool_measure_status(tmp_project):
    r = chat_agent._tool_measure_status({})
    assert "OP-100" in r
    assert "OP-101" in r
    assert "Projekt-Messung" in r


def test_tool_list_open_ops(tmp_project):
    r = chat_agent._tool_list_open_ops({})
    assert "2 offene OPs" in r
    assert "OP-100" in r
    assert "OP-101" in r


def test_tool_unbekannt(tmp_project):
    r = chat_agent._execute_tool("unbekannt", "{}")
    assert "unbekannt" in r
