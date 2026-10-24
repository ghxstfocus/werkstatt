"""Tests fuer werkstatt/planner.py (Phase 5)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from werkstatt.planner import _preflight_scan, run_planner
from werkstatt.state import RunState


def _state(tmp_path):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={"a": "doc a"}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_planner_erstellt_plan(tmp_path):
    st = _state(tmp_path)
    fake_json = '{"tasks": [{"id": "t1", "name": "A", "description": "B", "akzeptanzkriterien": ["c"]}], "tests": ["test_a"], "akzeptanzkriterien": ["done"]}'
    
    class FakeReply:
        ok = True
        content = fake_json
    
    with patch("werkstatt.planner.ask_llm", return_value=FakeReply()):
        result = run_planner(st)
        assert result is True
        assert len(st.tasks) == 1
        assert st.tests == ["test_a"]
        assert st.akzeptanzkriterien == ["done"]


def test_planner_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    assert run_planner(st) is False


def test_planner_llm_fehler(tmp_path):
    st = _state(tmp_path)
    
    class FakeReply:
        ok = False
        error = "timeout"
    
    with patch("werkstatt.planner.ask_llm", return_value=FakeReply()):
        assert run_planner(st) is False


def test_klassifiziert_env():
    """M-299a: ModuleNotFoundError wird als 'env' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("pytest", "ModuleNotFoundError: No module named 'defusedxml'") == "env"


def test_klassifiziert_lint():
    """M-299a: ruff-Stage wird als 'lint' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("ruff", "error: unused import") == "lint"


def test_klassifiziert_syntax():
    """M-299a: py_compile wird als 'syntax' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("py_compile", "SyntaxError: invalid syntax") == "syntax"


def test_planner_blocker_follow_up_ignore(tmp_path):
    """M-299e: Planner klassifiziert Preflight-Fehler."""
    st = _state(tmp_path)
    st.aufgabe = "Test-Aufgabe"
    st.docs = {}
    st.preflight_fehler = [
        {"klasse": "syntax", "stage_id": "py_compile", "datei": None, "text": "SyntaxError"},
    ]
    st.follow_up_fehler = [
        {"klasse": "type", "stage_id": "mypy", "datei": None, "text": "unused-ignore"},
    ]

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{"id": "t1", "name": "Fix", "description": "Fix syntax", "akzeptanzkriterien": ["ok"]}],
        "tests": ["test_fix"],
        "akzeptanzkriterien": ["fix laeuft"],
        "blocker": [{"klasse": "syntax", "text": "SyntaxError"}],
        "follow_up": [{"klasse": "type", "text": "unused-ignore"}],
        "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.blocker_fehler) == 1
    assert st.blocker_fehler[0]["klasse"] == "syntax"
    assert len(st.follow_up_fehler) == 1
    assert st.follow_up_fehler[0]["klasse"] == "type"
    assert st.ignore_fehler == []


def test_preflight_scan_klassifiziert(tmp_path):
    """M-299e: _preflight_scan klassifiziert Stage-Fehler."""
    from subprocess import CompletedProcess

    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(json.dumps({
        "stages": [
            {"id": "py_compile", "command": ["false"]},
            {"id": "ruff", "command": ["false"]},
        ]
    }))

    def _mock_run(cmd, **kwargs):
        if "py_compile" in str(cmd):
            return CompletedProcess(cmd, 1, "", "SyntaxError: invalid syntax")
        return CompletedProcess(cmd, 1, "", "ruff: unused import")

    with patch("subprocess.run", side_effect=_mock_run):
        fehler = _preflight_scan(st)

    assert len(fehler) == 2
    klassen = {f["klasse"] for f in fehler}
    assert "syntax" in klassen
    assert "lint" in klassen


def test_planner_deklariert_task_files(tmp_path):
    """M-306b: Planner speichert task_files aus Plan."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Repariere"
    st.docs = {}
    st.preflight_fehler = [
        {"klasse": "type", "stage_id": "mypy", "datei": "core/a.py", "text": "err"},
    ]

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{
            "id": "t1", "name": "Fix a.py", "description": "...",
            "action": "write",
            "task_files": ["core/a.py"],
            "akzeptanzkriterien": ["ok"],
        }],
        "tests": ["t1"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [{"klasse": "type", "text": "err"}],
        "follow_up": [],
        "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["core/a.py"]


def test_planner_action_missing(tmp_path):
    """M-306d: Planner-Task ohne action-Feld -> Default write + Audit."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{"id": "t1", "name": "Task ohne action"}],
        "tests": ["test"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply), \
         patch("werkstatt.planner.audit") as mock_audit:
        rc = run_planner(st)

    assert rc is True
    # action wurde auf write gesetzt
    assert st.tasks[0]["action"] == "write"
    # Audit wurde aufgerufen
    assert any(
        c[0][0] == "planner_action_missing"
        for c in mock_audit.call_args_list
    )

def test_planner_liest_progress(tmp_path):
    """M-307b-3 (N2): Planner-Prompt enthaelt PROGRESS.md-Inhalt."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    # PROGRESS.md mit 2 Bloecken anlegen
    (tmp_path / "PROGRESS.md").write_text(
        "# Fortschritt: test\n\n"
        "## 2026-10-24T10:00:00 -- Vorheriger Task 1\n"
        "- **Status:** done\n"
        "- **Dateien:** a.py\n\n"
        "## 2026-10-24T10:05:00 -- Vorheriger Task 2\n"
        "- **Status:** failed\n"
        "- **Info:** builder_failed\n",
        encoding="utf-8",
    )

    st = _state(tmp_path)
    st.aufgabe = "Test-Aufgabe"
    st.docs = {}

    captured = {}

    def _mock_ask_llm(api_key, system, user_content, **kwargs):
        captured["user_content"] = user_content
        reply = MagicMock()
        reply.ok = True
        reply.content = json.dumps({
            "tasks": [{"id": "t1", "name": "Task 1"}],
            "tests": ["test"],
            "akzeptanzkriterien": ["akz"],
            "blocker": [], "follow_up": [], "ignore": [],
        })
        return reply

    with patch("werkstatt.planner.ask_llm", side_effect=_mock_ask_llm):
        rc = run_planner(st)

    assert rc is True
    prompt = captured["user_content"]
    assert "Projekt-Fortschritt" in prompt
    assert "Vorheriger Task 1" in prompt
    assert "Vorheriger Task 2" in prompt
    assert "builder_failed" in prompt
