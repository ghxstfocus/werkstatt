"""Tests fuer OP-231: read-only Tool-Registry."""
from __future__ import annotations

from werkstatt import chat_tools

FORBIDDEN = {"write_file", "apply_patch", "git_commit",
             "shell_exec", "start_loop"}


def test_verbotene_tools_fehlen() -> None:
    for name in FORBIDDEN:
        assert name not in chat_tools.CHAT_TOOLS


def test_acht_soll_tools_vorhanden() -> None:
    erwartet = {
        "read_file", "grep", "git_log", "git_diff",
        "audit_query", "pytest_collect", "diagnose", "read_status",
    }
    assert set(chat_tools.CHAT_TOOLS) == erwartet


def test_alle_tools_mode_read() -> None:
    for spec in chat_tools.CHAT_TOOLS.values():
        assert spec["mode"] == "read"


def test_openai_schemas_anzahl() -> None:
    schemas = chat_tools.openai_schemas()
    assert len(schemas) == 8
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
    assert len(schemas) == 8


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
