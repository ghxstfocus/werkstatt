"""Tests fuer werkstatt.web.chat_agent (OP-084)."""
from __future__ import annotations

import subprocess

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
    (tmp_path / "test.py").write_text("def foo():\n    return 42\n", encoding="utf-8")
    chat_agent.init(tmp_path)
    monkeypatch.setattr(shell, "_AKTIVE_PTYS", {})
    yield tmp_path


def test_parse_open_ops(tmp_project):
    ops = chat_agent._open_ops()
    assert len(ops) == 2
    assert ops[0][0] == "OP-100"


def test_read_file(tmp_project):
    r = chat_agent._read_file("test.py")
    assert "return 42" in r


def test_read_file_traversal_blocked(tmp_project):
    r = chat_agent._read_file("../../../etc/passwd")
    assert "FEHLER" in r
    assert "ausserhalb" in r


def test_grep(tmp_project):
    r = chat_agent._grep("return 42")
    assert "test.py" in r


def test_pattern_offene_ops(tmp_project):
    a = chat_agent.verarbeite("welche OPs sind offen?")
    assert "OP-100" in a
    assert "OP-101" in a


def test_pattern_read_file(tmp_project):
    a = chat_agent.verarbeite("lies datei test.py")
    assert "return 42" in a


def test_pattern_miss_status(tmp_project):
    a = chat_agent.verarbeite("miss status")
    assert "Projekt-Messung" in a
    assert "OP-100" in a


def test_pattern_start_loop_op(monkeypatch, tmp_project):
    started = []
    class FakeProc:
        pid = 12345
    def fake_popen(cmd, **kwargs):
        started.append(cmd)
        return FakeProc()
    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    a = chat_agent.verarbeite("starte Loop mit OP-101")
    assert "Loop gestartet" in a
    assert "OP-101" in a
    assert len(started) == 1


def test_shell_exec_ohne_session(tmp_project):
    a = chat_agent.verarbeite("ls")
    assert "Keine aktive Shell-Session" in a


def test_shell_exec_mit_session(monkeypatch, tmp_project):
    class FakeSession:
        def __init__(self):
            self.cmds = []
        def inject(self, cmd):
            self.cmds.append(cmd)
            return True
    fake = FakeSession()
    monkeypatch.setattr(shell, "_AKTIVE_PTYS", {"werkstatt": fake})
    a = chat_agent.verarbeite("ls -la")
    assert "Befehl an Shell gesendet" in a
    assert fake.cmds == ["ls -la"]


def test_ist_shell_befehl(tmp_project):
    assert chat_agent._ist_shell_befehl("ls") is True
    assert chat_agent._ist_shell_befehl("git status") is True
    assert chat_agent._ist_shell_befehl("welche ops sind offen") is False
    assert chat_agent._ist_shell_befehl("? ls") is False


def test_fragezeichen_zwingt_chat(tmp_project):
    # `? ls` soll nicht als Shell-Befehl interpretiert werden
    # Wir koennen das nur indirekt pruefen: kein Shell-Exec-Error, weil
    # Pattern "ls" keine Chat-Antwort matched -> LLM-Fallback
    a = chat_agent.verarbeite("? ls")
    # Ohne DEEPSEEK_API_KEY gibt LLM einen Hinweis zurueck — nicht Shell
    assert "Keine aktive Shell-Session" not in a
