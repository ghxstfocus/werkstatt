"""Tests fuer werkstatt/planner.py (Phase 5)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

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
    """GOLD: Scout + Architect (Prosa) + Planner (JSON). Drei Calls."""
    st = _state(tmp_path)

    _scout_json = json.dumps({
        "ziel": "Test",
        "relevante_dateien": [{"pfad": "a.py", "zeilen": [1], "warum": "test"}],
        "api_auszug": {},
        "vorgeschlagene_aenderungen": ["neue Funktion fix()"],
        "risiken": [],
        "auftrag_prosa": "Baue fix() in a.py",
    })
    _arch_prosa = (
        "## Interface\n"
        "Neue Funktion fix() in a.py.\n\n"
        "## Logik\n"
        "Validiert x > 0, ruft helper().\n\n"
        "## Integration\n"
        "In main() einbauen.\n\n"
        "## Tests\n"
        "test_fix() in tests/test_a.py."
    )
    _planner_json = json.dumps({
        "tasks": [{"id": "t1", "name": "A", "description": "B",
                   "action": "update", "task_files": ["a.py"]}],
        "tests": ["test_a"],
        "akzeptanzkriterien": ["done"],
    })

    class FakeReply:
        def __init__(self, content):
            self.ok = True
            self.content = content

    _responses = iter([
        FakeReply(_scout_json),
        FakeReply(_arch_prosa),
        FakeReply(_planner_json),
    ])

    def _fake_ask_llm(*args, **kwargs):
        return next(_responses)

    with patch("werkstatt.planner.ask_llm", side_effect=_fake_ask_llm):
        result = run_planner(st)
        assert result is True
        assert len(st.tasks) == 1


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


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (blocker/follow_up/ignore nicht mehr im Gold-Flow)")
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


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (action-Default kommt vom Planner-Split)")
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
    # M-317: action-Default ist "update" (nicht "write")
    assert st.tasks[0]["action"] == "update"
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

    captured = {"calls": []}

    def _mock_ask_llm(api_key, system, user_content, **kwargs):
        captured["calls"].append(user_content)
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
    # GOLD: captured["calls"][0]=Scout, [1]=Architect, [2]=Planner-Split.
    # PROGRESS.md-Inhalt geht in den Architect-Call (user_content).
    _alle = "\n".join(captured["calls"])
    assert "Projekt-Fortschritt" in _alle
    assert "Vorheriger Task 1" in _alle
    assert "Vorheriger Task 2" in _alle
    assert "builder_failed" in _alle


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (phasen kommen vom Planner-Split, nicht direkt aus JSON)")
def test_planner_speichert_phasen(tmp_path):
    """M-310: Planner speichert phasen in state."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "phasen": [
            {"id": "p1", "titel": "Vorbereitung", "parent_id": None,
             "tasks": ["t1"]},
        ],
        "tasks": [{"id": "t1", "name": "Task 1", "action": "write"}],
        "tests": ["test"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.phasen) == 1
    assert st.phasen[0]["id"] == "p1"
    assert st.phasen[0]["titel"] == "Vorbereitung"


def test_planner_action_create_update(tmp_path):
    """M-317: Planner akzeptiert action=create und action=update."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [
            {"id": "t1", "name": "Neu", "action": "create"},
            {"id": "t2", "name": "Update", "action": "update"},
        ],
        "tests": ["t"],
        "akzeptanzkriterien": ["a"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert st.tasks[0]["action"] == "create"
    assert st.tasks[1]["action"] == "update"
