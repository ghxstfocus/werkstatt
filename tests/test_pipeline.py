"""Tests fuer /opt/werkstatt/pipeline.py.

Prueft die kritischen Pfade ohne echte LLM-Calls.
Kein DEEPSEEK_API_KEY erforderlich.
"""

from __future__ import annotations

import sys

# Werkstatt in den Import-Pfad
sys.path.insert(0, "/opt/werkstatt")

import pytest

import pipeline

# =====================================================================
# load_project_config
# =====================================================================

class TestLoadProjectConfig:
    def test_loads_valid_config(self) -> None:
        config = pipeline.load_project_config("security-ai")
        assert config["project"] == "homelab-security-ai"
        assert config["project_dir"] == "/opt/security-ai"
        assert config["agents_dir"] == "/opt/werkstatt/agents"
        assert "always_run" in config
        assert "py_compile" in config["always_run"]

    def test_fails_on_unknown_project(self) -> None:
        with pytest.raises(SystemExit) as exc:
            pipeline.load_project_config("gibt-es-nicht")
        assert exc.value.code == 1

    def test_fails_on_empty_name(self) -> None:
        with pytest.raises(SystemExit) as exc:
            pipeline.load_project_config("")
        assert exc.value.code == 1

    def test_fails_on_path_traversal(self) -> None:
        with pytest.raises(SystemExit) as exc:
            pipeline.load_project_config("../etc/passwd")
        assert exc.value.code == 1

    def test_fails_on_slash_in_name(self) -> None:
        with pytest.raises(SystemExit) as exc:
            pipeline.load_project_config("foo/bar")
        assert exc.value.code == 1


# =====================================================================
# parse_commands (Auflage 2039)
# =====================================================================

class TestParseCommands:
    def test_parses_valid_command(self) -> None:
        text = "COMMAND: RUN test_count"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert cmds[0]["id"] == "test_count"
        assert cmds[0]["arg"] == ""

    def test_parses_valid_command_with_arg(self) -> None:
        text = "COMMAND: RUN read_file core/main.py"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert cmds[0]["id"] == "read_file"
        assert cmds[0]["arg"] == "core/main.py"

    def test_ignores_lines_without_command_prefix(self) -> None:
        text = "Kein Befehl hier.\nNur Text."
        assert pipeline.parse_commands(text) == []

    def test_ignores_non_run_commands(self) -> None:
        text = "COMMAND: STOP test_count"
        assert pipeline.parse_commands(text) == []

    def test_parses_multiple_commands(self) -> None:
        text = "COMMAND: RUN test_count\nCOMMAND: RUN ruff"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 2
        assert cmds[0]["id"] == "test_count"
        assert cmds[1]["id"] == "ruff"

    def test_arg_is_always_str(self) -> None:
        # Auch wenn etwas Numerisches in der Zeile steht: arg ist str
        text = "COMMAND: RUN read_file 12345"
        cmds = pipeline.parse_commands(text)
        assert len(cmds) == 1
        assert isinstance(cmds[0]["arg"], str)
        assert cmds[0]["arg"] == "12345"


# =====================================================================
# classify_verdict
# =====================================================================

class TestClassifyVerdict:
    def test_go(self) -> None:
        assert pipeline.classify_verdict("GO") == "GO"

    def test_go_with_leading_whitespace(self) -> None:
        assert pipeline.classify_verdict("   GO\nBegruendung: ...") == "GO"

    def test_no_go(self) -> None:
        assert pipeline.classify_verdict("NO-GO\nGrund: ...") == "NO-GO"

    def test_eskalation(self) -> None:
        assert pipeline.classify_verdict("ESKALATION\nFrage: ...") == "ESKALATION"

    def test_commit_go(self) -> None:
        assert pipeline.classify_verdict("COMMIT-GO") == "COMMIT-GO"

    def test_commit_no_go(self) -> None:
        assert pipeline.classify_verdict("COMMIT-NO-GO") == "COMMIT-NO-GO"

    def test_command(self) -> None:
        assert pipeline.classify_verdict("COMMAND: RUN test_count") == "COMMAND"

    def test_unknown(self) -> None:
        assert pipeline.classify_verdict("") == "UNKLAR"

    def test_unknown_with_irrelevant_text(self) -> None:
        assert pipeline.classify_verdict("Das ist keine Antwort.") == "UNKLAR"

    def test_go_after_many_inhalt_lines(self) -> None:
        # Verdict ist erst nach 20 inhaltlichen Zeilen -> UNKLAR.
        text = "Zeile\n" * 20 + "GO"
        assert pipeline.classify_verdict(text) == "UNKLAR"

    def test_go_after_few_empty_lines(self) -> None:
        # Leere Zeilen zaehlen nicht -> GO ist frueh genug
        text = "\n\n\nGO"
        assert pipeline.classify_verdict(text) == "GO"


# =====================================================================
# parse_auflagen (Auflage 2034)
# =====================================================================

class TestParseAuflagen:
    def test_parses_a_prefix(self) -> None:
        text = "Auflage A1: RBAC pruefen.\nAuflage A2: CSRF pruefen."
        auflagen = pipeline.parse_auflagen(text)
        assert len(auflagen) == 2
        assert "A1" in auflagen[0]
        assert "A2" in auflagen[1]

    def test_parses_number_without_prefix(self) -> None:
        text = "Auflage 2015: ToolError umstellen."
        auflagen = pipeline.parse_auflagen(text)
        assert len(auflagen) == 1
        assert "2015" in auflagen[0]

    def test_ignores_unrelated_text(self) -> None:
        assert pipeline.parse_auflagen("Kein Auflage-Format hier.") == []

    def test_ignores_empty(self) -> None:
        assert pipeline.parse_auflagen("") == []


# =====================================================================
# trim_output (Auflage 2041)
# =====================================================================

class TestTrimOutput:
    def test_short_text_unchanged(self) -> None:
        text = "kurz"
        assert pipeline.trim_output(text, grenze=100) == text

    def test_long_text_truncated(self) -> None:
        text = "x" * 200
        result = pipeline.trim_output(text, grenze=100)
        assert len(result) < 200
        assert "gekuerzt" in result
        assert result.startswith("x" * 100)

    def test_exact_boundary(self) -> None:
        text = "x" * 100
        assert pipeline.trim_output(text, grenze=100) == text


# =====================================================================
# parse_commit_paket
# =====================================================================

class TestParseCommitPaket:
    def test_parses_full_paket(self) -> None:
        text = (
            "COMMIT-MESSAGE:\n"
            "fix(workbench): 2015 - Test\n"
            "Ausgangslage: x\n"
            "ENDE COMMIT-MESSAGE\n"
            "BETROFFENE DATEIEN:\n"
            "  - docs/PHASES.md\n"
            "  - docs/SECURITY_REVIEW_LOG.md\n"
            "ENDE BETROFFENE DATEIEN\n"
            "DOKU-PATCHES:\n"
            "  - pfad: docs/PHASES.md\n"
            "    anker: ALT\n"
            "    ersatz: NEU\n"
            "ENDE DOKU-PATCHES"
        )
        paket = pipeline.parse_commit_paket(text)
        assert paket["message"].startswith("fix(workbench)")
        assert len(paket["dateien"]) == 2
        assert "docs/PHASES.md" in paket["dateien"]
        assert len(paket["doku_patches"]) == 1
        assert paket["doku_patches"][0]["pfad"] == "docs/PHASES.md"
        assert paket["doku_patches"][0]["anker"] == "ALT"
        assert paket["doku_patches"][0]["ersatz"] == "NEU"

    def test_empty_text(self) -> None:
        paket = pipeline.parse_commit_paket("")
        assert paket["message"] == ""
        assert paket["dateien"] == []
        assert paket["doku_patches"] == []


# =====================================================================
# parse_empfehlung
# =====================================================================

class TestParseEmpfehlung:
    def test_parses_all_fields(self) -> None:
        text = (
            "EMPFEHLUNG TESTS: ja\n"
            "EMPFEHLUNG ART: integration\n"
            "EMPFEHLUNG PRIORITAET: RBAC zuerst"
        )
        emp = pipeline.parse_empfehlung(text)
        assert emp["tests"] == "ja"
        assert emp["art"] == "integration"
        assert emp["prioritaet"] == "RBAC zuerst"

    def test_empty(self) -> None:
        emp = pipeline.parse_empfehlung("")
        assert emp["tests"] == ""
        assert emp["art"] == ""
        assert emp["prioritaet"] == ""
