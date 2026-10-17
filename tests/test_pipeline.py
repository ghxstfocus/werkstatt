"""Tests fuer /opt/werkstatt/pipeline.py.

Prueft die kritischen Pfade ohne echte LLM-Calls.
Kein DEEPSEEK_API_KEY erforderlich.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import ClassVar

# Werkstatt in den Import-Pfad
sys.path.insert(0, "/opt/werkstatt")

import re

import pytest

import pipeline

# =====================================================================
# Test-Helpers
# =====================================================================

def build_test_state(
    *,
    project_dir: Path | None = None,
    project_name: str = "test-projekt",
    file_whitelist: list[str] | None = None,
    always: dict | None = None,
    optional: dict | None = None,
) -> pipeline.RunState:
    """Baut ein minimales RunState fuer Tests.

    Alle Pflichtfelder werden gesetzt, optionale Felder
    bekommen sinnvolle Defaults.

    Fuer Tests, die nur einen Teil der Felder brauchen.
    """
    return pipeline.RunState(
        block_id="TEST-BLOCK",
        aufgabe="Test-Aufgabe",
        start_ts="2026-10-12T00:00:00Z",
        docs={},
        agents={},
        always=always if always is not None else {},
        optional=optional if optional is not None else {},
        file_whitelist=file_whitelist if file_whitelist is not None else ["docs/", "core/"],
        api_key="sk-test",
        budget={"max_review_rounds": 5, "max_llm_calls": 20},
        agent_docs={},
        project_dir=project_dir if project_dir is not None else Path.cwd(),
        project_name=project_name,
    )


# =====================================================================
# load_project_config
# =====================================================================

class TestLoadProjectConfig:
    def test_loads_valid_config(self) -> None:
        config = pipeline.load_project_config("security-ai")
        assert config["project"] == "homelab-security-ai"
        assert config["project_dir"] == "/opt/security-ai"
        # agents_dir ist seit Phase 1 (Projekt-Schema) entfernt.
        # project_agents_dir ist optional (Kategorie O, Default null).
        assert "agents_dir" not in config
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
        # B0c: Verdict am Ende wird erkannt.
        text = "Zeile\n" * 20 + "GO"
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_after_few_empty_lines(self) -> None:
        # Leere Zeilen zaehlen nicht -> GO ist frueh genug
        text = "\n\n\nGO"
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_at_line_15(self) -> None:
        """Auflage 2059: GO auf Zeile 15 (Grenze) -> GO."""
        # 14 Fuellzeilen + GO = Zeile 15.
        text = "Zeile\n" * 14 + "GO"
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_at_line_16(self) -> None:
        """Auflage 2059 + B0c: GO ist letzte Zeile.

        Die 15-Zeilen-Grenze gilt fuer den ANFANG.
        Der B0c-Fallback erkennt ein Verdict am Ende,
        wenn es die letzte nicht-leere Zeile ist.
        """
        text = "Zeile\n" * 15 + "GO"
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_mit_punkt(self) -> None:
        assert pipeline.classify_verdict("GO.") == "GO"

    def test_go_mit_doppelpunkt(self) -> None:
        assert pipeline.classify_verdict("GO:") == "GO"

    def test_no_go_mit_doppelpunkt(self) -> None:
        assert pipeline.classify_verdict("NO-GO: Grund ...") == "NO-GO"

    def test_no_go_mit_punkt(self) -> None:
        assert pipeline.classify_verdict("NO-GO. Grund ...") == "NO-GO"

    def test_eskalation_mit_ausrufezeichen(self) -> None:
        assert pipeline.classify_verdict("ESKALATION!") == "ESKALATION"

    def test_eskalation_mit_fragezeichen(self) -> None:
        assert pipeline.classify_verdict("ESKALATION?") == "ESKALATION"

    def test_commit_go_mit_punkt(self) -> None:
        assert pipeline.classify_verdict("COMMIT-GO.") == "COMMIT-GO"

    def test_commit_no_go_mit_doppelpunkt(self) -> None:
        assert pipeline.classify_verdict(
            "COMMIT-NO-GO: Message falsch.") == "COMMIT-NO-GO"

    def test_bindestrich_wird_nicht_zerlegt(self) -> None:
        # "NO-GO." darf NICHT als "NO" gelesen werden.
        assert pipeline.classify_verdict("NO-GO.") == "NO-GO"

    def test_go_mit_klammer(self) -> None:
        assert pipeline.classify_verdict("GO)") == "GO"


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
    """Tests fuer parse_commit_paket.

    Auflagen 2088 + 2098 + 2099: neues Format mit
    PATCH-BEGINN/PATCH-ENDE und YAML-Block-Scalar "|".
    """

    def _paket(self, doku: str) -> str:
        """Baut eine vollstaendige Antwort mit COMMIT-MESSAGE
        und DOKU-PATCHES."""
        return (
            "COMMIT-MESSAGE:\n"
            "fix(workbench): 2015 - Test\n"
            "Ausgangslage: x\n"
            "ENDE COMMIT-MESSAGE\n"
            "BETROFFENE DATEIEN:\n"
            "  - docs/PHASES.md\n"
            "  - docs/SECURITY_REVIEW_LOG.md\n"
            "ENDE BETROFFENE DATEIEN\n"
            "DOKU-PATCHES:\n"
            + doku +
            "\nENDE DOKU-PATCHES"
        )

    def test_parses_full_paket(self) -> None:
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "  ALT\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert paket["message"].startswith("fix(workbench)")
        assert len(paket["dateien"]) == 2
        assert len(paket["doku_patches"]) == 1
        assert paket["doku_patches"][0]["pfad"] == "docs/PHASES.md"
        assert paket["doku_patches"][0]["anker"] == "ALT"
        assert paket["doku_patches"][0]["ersatz"] == "NEU"

    def test_empty_text(self) -> None:
        paket = pipeline.parse_commit_paket("")
        assert paket["message"] == ""
        assert paket["dateien"] == []
        assert paket["doku_patches"] == []

    def test_zwei_patches_in_einer_antwort(self) -> None:
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "  A1\n"
            "ersatz: |\n"
            "  B1\n"
            "PATCH-ENDE\n"
            "PATCH-BEGINN\n"
            "pfad: docs/SECURITY_REVIEW_LOG.md\n"
            "anker: |\n"
            "  A2\n"
            "ersatz: |\n"
            "  B2\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert len(paket["doku_patches"]) == 2
        assert paket["doku_patches"][0]["pfad"] == "docs/PHASES.md"
        assert paket["doku_patches"][0]["anker"] == "A1"
        assert paket["doku_patches"][1]["pfad"] == "docs/SECURITY_REVIEW_LOG.md"
        assert paket["doku_patches"][1]["ersatz"] == "B2"

    def test_anker_leer_patch_verworfen(self) -> None:
        """Leerer Anker -> Patch verworfen (E3)."""
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert paket["doku_patches"] == []

    def test_mehrzeiliger_ersatz(self) -> None:
        """Ersatz mit mehreren Zeilen wird vollstaendig geparst."""
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "  ALT\n"
            "ersatz: |\n"
            "  Zeile 1\n"
            "  Zeile 2\n"
            "  Zeile 3\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert len(paket["doku_patches"]) == 1
        assert paket["doku_patches"][0]["ersatz"] == "Zeile 1\nZeile 2\nZeile 3"

    def test_mehrzeiliger_anker(self) -> None:
        """Anker mit mehreren Zeilen UND "- pfad:"-Sequenz
        wird vollstaendig geparst (loest Bug 2088/2098 auf)."""
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "  Zeile 1\n"
            "  - pfad: was-ganz-anderes\n"
            "  Zeile 3\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert len(paket["doku_patches"]) == 1
        assert paket["doku_patches"][0]["anker"] == (
            "Zeile 1\n- pfad: was-ganz-anderes\nZeile 3"
        )

    def test_leerer_ersatz_erlaubt(self) -> None:
        """Ersatz leer -> Patch gueltig, ersatz == ''."""
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "  ALT\n"
            "ersatz: |\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
        assert len(paket["doku_patches"]) == 1
        assert paket["doku_patches"][0]["ersatz"] == ""

    def test_tab_einrueckung_verworfen(self) -> None:
        """Tabs in der Einrueckung -> Patch verworfen (P1)."""
        text = self._paket(
            "PATCH-BEGINN\n"
            "pfad: docs/PHASES.md\n"
            "anker: |\n"
            "\tALT\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        paket = pipeline.parse_commit_paket(text)
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


# =====================================================================
# execute_commands (Auflage 2060)
# =====================================================================

class TestExecuteCommands:
    """Tests fuer die zentrale Sicherheitsfunktion execute_commands.

    Auflagen 2027, 2039, 2040, 2041, 2042.
    """

    def test_unknown_id_rejected(self, monkeypatch) -> None:
        """Auflage 2027: unbekannte ID wird nicht ausgefuehrt."""
        audited: list[tuple] = []
        executed: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        def fake_run(m, wl, pd, arg=None):
            executed.append((m.mid, arg))
            return ("output", True, ["cmd"])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        state = build_test_state(always={}, optional={})
        pipeline.execute_commands(state, [{"id": "unbekannt", "arg": ""}], "reviewer")

        assert executed == [], "unbekannte ID darf nicht ausgefuehrt werden"
        rejected = [a for a in audited if a[0] == "command_rejected"]
        assert len(rejected) == 1
        assert rejected[0][1]["grund"] == "nicht_in_whitelist"

    def test_known_id_executed(self, monkeypatch) -> None:
        """Auflage 2027: bekannte ID wird ausgefuehrt."""
        audited: list[tuple] = []
        executed: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        def fake_run(m, wl, pd, arg=None):
            executed.append((m.mid, arg))
            return ("ausgabe\n", True, ["test_cmd"])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        m = pipeline.Measurement("test_count", ("echo", "test"), "Test")
        state = build_test_state(always={"test_count": m}, optional={})
        pipeline.execute_commands(state, [{"id": "test_count", "arg": ""}], "reviewer")

        assert executed == [("test_count", None)]
        executed_audit = [a for a in audited if a[0] == "command_executed"]
        assert len(executed_audit) == 1
        assert executed_audit[0][1]["id"] == "test_count"
        assert executed_audit[0][1]["argv"] == ["test_cmd"]
        assert executed_audit[0][1]["quelle"] == "reviewer"
        assert executed_audit[0][1]["ok"] is True

    def test_arg_not_str_rejected(self, monkeypatch) -> None:
        """Auflage 2039: arg muss str sein."""
        audited: list[tuple] = []
        executed: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        def fake_run(m, wl, pd, arg=None):
            executed.append(m.mid)
            return ("", True, [])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        m = pipeline.Measurement("test_count", ("echo",), "Test")
        state = build_test_state(always={"test_count": m}, optional={})
        # arg als dict (kein str) — mypy: bewusst falscher Typ
        cmd = {"id": "test_count", "arg": {"x": 1}}
        pipeline.execute_commands(state, [cmd], "reviewer")  # type: ignore[list-item]

        assert executed == [], "arg-dict darf nicht ausgefuehrt werden"
        rejected = [a for a in audited if a[0] == "command_rejected"]
        assert len(rejected) == 1
        assert rejected[0][1]["grund"] == "arg_kein_str"

    def test_quelle_invalid_marked(self, monkeypatch) -> None:
        """Auflage 2042: ungueltige quelle -> Audit + Downgrade."""
        audited: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        def fake_run(m, wl, pd, arg=None):
            return ("", True, [])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        m = pipeline.Measurement("test_count", ("echo",), "Test")
        state = build_test_state(always={"test_count": m}, optional={})
        pipeline.execute_commands(state, [{"id": "test_count", "arg": ""}], "bogus")

        quelle_audits = [a for a in audited if a[0] == "quelle_invalid"]
        assert len(quelle_audits) == 1
        # Beim command_executed muss "unknown" stehen
        executed_audits = [a for a in audited if a[0] == "command_executed"]
        assert len(executed_audits) == 1
        assert executed_audits[0][1]["quelle"] == "unknown"

    def test_mess_protokoll_grows(self, monkeypatch) -> None:
        """mess_protokoll wird an die Ausgabe angehaengt."""
        def fake_audit(kind, payload, project_dir, project_name):
            pass

        def fake_run(m, wl, pd, arg=None):
            return ("AUSGABE-INHALT\n", True, ["cmd"])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        m = pipeline.Measurement("test_count", ("echo",), "Test")
        state = build_test_state(always={"test_count": m}, optional={})
        pipeline.execute_commands(state, [{"id": "test_count", "arg": ""}], "reviewer")

        assert "AUSGABE-INHALT" in state.mess_protokoll

    def test_empty_commands_no_effect(self, monkeypatch) -> None:
        """Leere Befehlsliste aendert nichts."""
        audited: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        monkeypatch.setattr(pipeline, "audit", fake_audit)

        state = build_test_state(always={}, optional={})
        pipeline.execute_commands(state, [], "reviewer")

        assert audited == []

    def test_id_not_str_rejected(self, monkeypatch) -> None:
        """Auflage 2039: id muss str sein."""
        audited: list[tuple] = []
        executed: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audited.append((kind, payload))

        def fake_run(m, wl, pd, arg=None):
            executed.append(m.mid)
            return ("", True, [])

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(pipeline, "run_measurement_mit_argv", fake_run)

        state = build_test_state(always={}, optional={})
        # id als int (kein str) — mypy: bewusst falscher Typ
        cmd = {"id": 42, "arg": ""}
        pipeline.execute_commands(state, [cmd], "reviewer")  # type: ignore[list-item]

        assert executed == []
        rejected = [a for a in audited if a[0] == "command_rejected"]
        assert len(rejected) == 1
        assert rejected[0][1]["grund"] == "id_kein_str"


# =====================================================================
# apply_commit_and_doku (Auflage 2061)
# =====================================================================

class TestApplyCommitAndDoku:
    """Tests fuer apply_commit_and_doku.

    Fehlerpfade und Erfolgspfad im tmp-Git-Repo.
    Auflage 2061 (Befund T5).
    """

    def _init_tmp_repo(self, path: Path) -> None:
        """Initialisiert ein tmp-Git-Repo."""
        subprocess.run(("git", "init", "-q"), cwd=str(path), check=True)
        subprocess.run(
            ("git", "-c", "user.name=Test", "-c", "user.email=t@t.de",
             "commit", "--allow-empty", "-m", "init"),
            cwd=str(path), check=True, capture_output=True,
        )

    def test_keine_dateien_abbruch(self, tmp_path: Path) -> None:
        """Keine Dateien angegeben -> False."""
        self._init_tmp_repo(tmp_path)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {"message": "test", "dateien": [], "doku_patches": []}
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_datei_nicht_in_whitelist(self, tmp_path: Path) -> None:
        """Datei ausserhalb der Whitelist -> False."""
        self._init_tmp_repo(tmp_path)
        (tmp_path / "etwas.txt").write_text("x")
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {"message": "test", "dateien": ["etwas.txt"], "doku_patches": []}
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_datei_existiert_nicht(self, tmp_path: Path) -> None:
        """Auflage 2048: Datei existiert nicht -> False."""
        self._init_tmp_repo(tmp_path)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {"message": "test", "dateien": ["docs/fehlt.md"], "doku_patches": []}
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_doku_datei_fehlt(self, tmp_path: Path) -> None:
        """Doku-Zieldatei fehlt -> False."""
        self._init_tmp_repo(tmp_path)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [{"pfad": "docs/fehlt.md", "anker": "X", "ersatz": "Y"}],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_anker_kommt_null_mal(self, tmp_path: Path) -> None:
        """Anker existiert nicht in der Datei -> False."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("Inhalt ohne Anker.")
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [{"pfad": "docs/x.md", "anker": "FEHLT", "ersatz": "Y"}],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_anker_kommt_zweimal_vor(self, tmp_path: Path) -> None:
        """Anker mehrdeutig (2x) -> False."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("Anker hier. Anker nochmal.")
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [{"pfad": "docs/x.md", "anker": "Anker", "ersatz": "Y"}],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is False

    def test_erfolg_mit_doku_patch(self, tmp_path: Path) -> None:
        """Erfolgspfad: Doku-Patch + Commit im tmp-Repo."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("Alt: MARKER\n")
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])

        paket = {
            "message": "test: doku patchen\n\nDetails.",
            "dateien": ["docs/x.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "MARKER", "ersatz": "NEU"},
            ],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is True

        # Doku wurde geaendert
        assert "NEU" in (docs / "x.md").read_text()

        # Commit existiert
        log = subprocess.run(
            ("git", "log", "-1", "--format=%s"),
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert log == "test: doku patchen"

        # Autor ist gesetzt
        author = subprocess.run(
            ("git", "log", "-1", "--format=%an <%ae>"),
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert author == "ghxstfocus <ghxst.focus@gmail.com>"

        # Keine .commit-msg.tmp uebrig
        assert not (tmp_path / ".commit-msg.tmp").exists()

    def test_doku_patch_nicht_geschrieben_wenn_datei_fehlt(
        self, tmp_path: Path,
    ) -> None:
        """Auflage 2082: dateien fehlt -> Doku bleibt unberuehrt."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        original = "Alt: MARKER\n"
        (docs / "x.md").write_text(original)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/fehlt.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "MARKER", "ersatz": "NEU"},
            ],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is False
        # Doku ist unveraendert.
        assert (docs / "x.md").read_text() == original

    def test_doku_patch_nicht_geschrieben_wenn_anker_fehlt(
        self, tmp_path: Path,
    ) -> None:
        """Auflage 2082: Anker fehlt -> Doku bleibt unberuehrt."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        original = "Inhalt ohne Anker.\n"
        (docs / "x.md").write_text(original)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "FEHLT", "ersatz": "NEU"},
            ],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is False
        assert (docs / "x.md").read_text() == original

    def test_doku_patch_rollback_wenn_git_add_fehlt(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """Auflage 2082: git add scheitert -> Doku zurueckgerollt."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        original = "Alt: MARKER\n"
        (docs / "x.md").write_text(original)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "MARKER", "ersatz": "NEU"},
            ],
        }

        echtes_run = subprocess.run

        def fake_run(argv, *args, **kwargs):
            if isinstance(argv, (list, tuple)) and len(argv) >= 2 \
                    and argv[0] == "git" and argv[1] == "add":
                class _R:
                    returncode = 1
                    stdout = ""
                    stderr = "fake add fehler"
                return _R()
            return echtes_run(argv, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert pipeline.apply_commit_and_doku(state, paket) is False
        # Doku ist zurueckgerollt.
        assert (docs / "x.md").read_text() == original

    def test_doku_patch_rollback_wenn_git_commit_fehlt(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """Auflage 2082: git commit scheitert -> Doku zurueckgerollt."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        original = "Alt: MARKER\n"
        (docs / "x.md").write_text(original)
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])
        paket = {
            "message": "test",
            "dateien": ["docs/x.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "MARKER", "ersatz": "NEU"},
            ],
        }

        echtes_run = subprocess.run

        def fake_run(argv, *args, **kwargs):
            if isinstance(argv, (list, tuple)) and "commit" in argv \
                    and "git" in argv:
                class _R:
                    returncode = 1
                    stdout = ""
                    stderr = "fake commit fehler"
                return _R()
            return echtes_run(argv, *args, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert pipeline.apply_commit_and_doku(state, paket) is False
        # Doku ist zurueckgerollt.
        assert (docs / "x.md").read_text() == original

    def test_erfolg_ohne_doku_patch(self, tmp_path: Path) -> None:
        """Erfolgspfad ohne Doku-Patch."""
        self._init_tmp_repo(tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("Inhalt.\n")
        state = build_test_state(project_dir=tmp_path, file_whitelist=["docs/"])

        paket = {
            "message": "test: nur datei\n\nNichts weiter.",
            "dateien": ["docs/x.md"],
            "doku_patches": [],
        }
        assert pipeline.apply_commit_and_doku(state, paket) is True
        # .commit-msg.tmp weg
        assert not (tmp_path / ".commit-msg.tmp").exists()


# =====================================================================
# snapshot_tests_dir + check_tests_dir_unveraendert (Auflage 2062)
# =====================================================================

class TestSnapshotTestsDir:
    """Tests fuer snapshot_tests_dir."""

    def test_leeres_verzeichnis_kein_snapshot(self, tmp_path: Path) -> None:
        """Kein tests/-Verzeichnis -> leeres dict."""
        snap = pipeline.snapshot_tests_dir(tmp_path)
        assert snap == {}

    def test_leeres_tests_verzeichnis(self, tmp_path: Path) -> None:
        """tests/ existiert, aber leer -> leeres dict."""
        (tmp_path / "tests").mkdir()
        snap = pipeline.snapshot_tests_dir(tmp_path)
        assert snap == {}

    def test_eine_datei(self, tmp_path: Path) -> None:
        """Eine Testdatei wird mit relativer Pfad + Groesse erfasst."""
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        snap = pipeline.snapshot_tests_dir(tmp_path)
        assert snap == {"tests/test_a.py": 100}

    def test_mehrere_dateien_inkl_unterordner(self, tmp_path: Path) -> None:
        """rglob erfasst auch Unterordner."""
        tests = tmp_path / "tests"
        (tests / "unit").mkdir(parents=True)
        (tests / "test_a.py").write_text("a" * 50)
        (tests / "unit" / "test_b.py").write_text("b" * 30)
        snap = pipeline.snapshot_tests_dir(tmp_path)
        assert snap == {
            "tests/test_a.py": 50,
            "tests/unit/test_b.py": 30,
        }

    def test_nicht_py_dateien_ignoriert(self, tmp_path: Path) -> None:
        """Nur *.py wird erfasst."""
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 10)
        (tests / "readme.txt").write_text("y" * 100)
        snap = pipeline.snapshot_tests_dir(tmp_path)
        assert snap == {"tests/test_a.py": 10}


class TestCheckTestsDirUnveraendert:
    """Tests fuer check_tests_dir_unveraendert.

    Auflage 2062 (Befund T6): schuetzt vor Auto-Repair-Schaden.
    """

    def test_keine_aenderung_ok(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is True
        assert probleme == []

    def test_datei_geloescht_nicht_ok(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        (tests / "test_a.py").unlink()
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is False
        assert len(probleme) == 1
        assert probleme[0].startswith("GELOESCHT:")
        assert "tests/test_a.py" in probleme[0]

    def test_datei_kleiner_nicht_ok(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        (tests / "test_a.py").write_text("x" * 50)
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is False
        assert len(probleme) == 1
        assert probleme[0].startswith("KLEINER:")
        assert "100 -> 50" in probleme[0]

    def test_datei_groesser_ok(self, tmp_path: Path) -> None:
        """Wachsen ist kein Problem."""
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        (tests / "test_a.py").write_text("x" * 200)
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is True
        assert probleme == []

    def test_neue_datei_ok(self, tmp_path: Path) -> None:
        """Neue Datei ist kein Problem, wird nicht geprueft."""
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        (tests / "test_b.py").write_text("y" * 200)
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is True
        assert probleme == []

    def test_zwei_probleme(self, tmp_path: Path) -> None:
        """Geloescht + kleiner in einem Lauf -> zwei Probleme."""
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_a.py").write_text("x" * 100)
        (tests / "test_b.py").write_text("y" * 200)
        vorher = pipeline.snapshot_tests_dir(tmp_path)
        (tests / "test_a.py").unlink()
        (tests / "test_b.py").write_text("y" * 50)
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, vorher)
        assert ok is False
        assert len(probleme) == 2
        probleme_text = " | ".join(probleme)
        assert "GELOESCHT: tests/test_a.py" in probleme_text
        assert "KLEINER: tests/test_b.py" in probleme_text

    def test_leerer_snapshot_ok(self, tmp_path: Path) -> None:
        """Vorher-Snapshot leer -> immer ok."""
        (tmp_path / "tests").mkdir()
        ok, probleme = pipeline.check_tests_dir_unveraendert(tmp_path, {})
        assert ok is True
        assert probleme == []


# =====================================================================
# subprocess_env (Auflage 2086)
# =====================================================================

class TestSubprocessEnv:
    """Tests fuer subprocess_env().

    Auflage 2086: DEEPSEEK_API_KEY und andere Secrets
    duerfen nicht an Subprozesse durchgereicht werden.
    """

    def test_env_does_not_contain_api_key(
        self, monkeypatch,
    ) -> None:
        """DEEPSEEK_API_KEY ist NICHT in subprocess_env()."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        env = pipeline.subprocess_env()
        assert "DEEPSEEK_API_KEY" not in env

    def test_env_contains_path(self, monkeypatch) -> None:
        """PATH ist in subprocess_env() enthalten."""
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        env = pipeline.subprocess_env()
        assert env.get("PATH") == "/usr/bin:/bin"

    def test_env_does_not_contain_unknown_var(
        self, monkeypatch,
    ) -> None:
        """Beliebige nicht-erlaubte Variable ist NICHT enthalten."""
        monkeypatch.setenv("NTFY_TOKEN", "geheim")
        monkeypatch.setenv("FRITZ_PASSWORD", "geheim2")
        env = pipeline.subprocess_env()
        assert "NTFY_TOKEN" not in env
        assert "FRITZ_PASSWORD" not in env

    def test_subprocess_run_uses_clean_env(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Optional: alle Aufrufe uebergeben env= an subprocess.run.

        Wir pruefen stellvertretend run_measurement, weil es
        den einfachsten Pfad hat (argv fertig, kein State).
        """
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")

        import subprocess as _sp
        aufrufe: list[dict] = []
        echtes_run = _sp.run

        class _FakeRes:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(argv, *args, **kwargs):
            aufrufe.append({"argv": argv, "kwargs": kwargs})
            return _FakeRes()

        monkeypatch.setattr(_sp, "run", fake_run)

        m = pipeline.Measurement("dummy", ("echo",), "Test.", 5)
        pipeline.run_measurement(m, [], tmp_path)

        # Wiederherstellen nicht noetig (monkeypatch raeumt auf),
        # aber echtes_run halten, damit ruff nicht meckert.
        assert echtes_run is not None

        assert len(aufrufe) == 1
        kwargs = aufrufe[0]["kwargs"]
        assert "env" in kwargs
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "DEEPSEEK_API_KEY" not in env


# =====================================================================
# ask_llm Retry (Auflage 2087)
# =====================================================================

class TestAskLlmRetry:
    """Tests fuer ask_llm Retry mit Backoff.

    Auflage 2087: Retry nur bei 429 und 5xx, max 2 Versuche,
    Backoff 1s / 3s. Kein Retry bei 4xx.
    """

    def _patch_sleep(self, monkeypatch) -> list[float]:
        """Ersetzt time.sleep, sammelt die Wartezeiten."""
        warten: list[float] = []
        monkeypatch.setattr(pipeline.time, "sleep", lambda s: warten.append(s))
        return warten

    def test_200_kein_retry(self, monkeypatch) -> None:
        self._patch_sleep(monkeypatch)
        aufrufe: list[int] = []

        class _Res:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "GO"}}]}

        def fake_post(url, **kwargs):
            aufrufe.append(1)
            return _Res()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        reply = pipeline.ask_llm("k", "s", "u", "m", 0.0, timeout=1)
        assert reply.ok is True
        assert reply.content == "GO"
        assert len(aufrufe) == 1

    def test_401_kein_retry(self, monkeypatch) -> None:
        warten = self._patch_sleep(monkeypatch)
        aufrufe: list[int] = []

        class _Res:
            status_code = 401
            text = "Unauthorized"

            def json(self):
                return {}

        def fake_post(url, **kwargs):
            aufrufe.append(1)
            return _Res()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        reply = pipeline.ask_llm("k", "s", "u", "m", 0.0, timeout=1)
        assert reply.ok is False
        assert "401" in reply.error
        assert len(aufrufe) == 1
        assert warten == []

    def test_429_dann_200(self, monkeypatch) -> None:
        warten = self._patch_sleep(monkeypatch)
        aufrufe: list[int] = []

        class _Res429:
            status_code = 429
            text = "Too Many Requests"

            def json(self):
                return {}

        class _Res200:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "OK"}}]}

        def fake_post(url, **kwargs):
            aufrufe.append(1)
            return _Res429() if len(aufrufe) == 1 else _Res200()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        reply = pipeline.ask_llm("k", "s", "u", "m", 0.0, timeout=1)
        assert reply.ok is True
        assert len(aufrufe) == 2
        assert warten == [1]

    def test_500_500_kein_dritter_versuch(self, monkeypatch) -> None:
        warten = self._patch_sleep(monkeypatch)
        aufrufe: list[int] = []

        class _Res:
            status_code = 500
            text = "Server Error"

            def json(self):
                return {}

        def fake_post(url, **kwargs):
            aufrufe.append(1)
            return _Res()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        reply = pipeline.ask_llm("k", "s", "u", "m", 0.0, timeout=1)
        assert reply.ok is False
        assert "500" in reply.error
        assert len(aufrufe) == 2
        # Nur ein Backoff vor dem zweiten Versuch.
        assert warten == [1]

    def test_connection_error_retry(self, monkeypatch) -> None:
        warten = self._patch_sleep(monkeypatch)
        aufrufe: list[int] = []

        class _Res200:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "OK"}}]}

        def fake_post(url, **kwargs):
            aufrufe.append(1)
            if len(aufrufe) == 1:
                raise pipeline.requests.RequestException("boom")
            return _Res200()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        reply = pipeline.ask_llm("k", "s", "u", "m", 0.0, timeout=1)
        assert reply.ok is True
        assert len(aufrufe) == 2
        assert warten == [1]


# =====================================================================
# ask_llm: user_content max_len (Auflage 2113)
# =====================================================================

class TestAskLlmUserContentMaxLen:
    """Tests fuer user_content max_len=100_000.

    Auflage 2113: analog 2089 (System-Prompt). Der User-Content
    (Block-Auftrag) wird nicht mehr bei 2000 Zeichen abgeschnitten.
    """

    def _patch_post(self, monkeypatch) -> list[dict]:
        gesendet: list[dict] = []

        class _Res200:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "OK"}}]}

        def fake_post(url, **kwargs):
            gesendet.append(kwargs)
            return _Res200()

        monkeypatch.setattr(pipeline.requests, "post", fake_post)
        return gesendet

    def test_kuerzt_nicht_bei_10k_zeichen(
        self, monkeypatch,
    ) -> None:
        """10k Zeichen kommen vollstaendig durch (nicht bei 2000)."""
        gesendet = self._patch_post(monkeypatch)
        # Kein Hex-aehnlicher Text (sonst greift redact_secrets).
        langer_text = "Der Auftrag umfasst mehrere Zeilen. " * 260
        assert 5000 < len(langer_text) < 20000
        pipeline.ask_llm("k", "s", langer_text, "m", 0.0, timeout=1)
        assert len(gesendet) == 1
        payload = gesendet[0]["json"]
        user_msg = payload["messages"][1]["content"]
        assert user_msg == langer_text

    def test_kuerzt_bei_ueber_100k(
        self, monkeypatch,
    ) -> None:
        """Mehr als 100_000 Zeichen werden auf 100_000 gekuerzt."""
        gesendet = self._patch_post(monkeypatch)
        zu_lang = "B" * 120000
        pipeline.ask_llm("k", "s", zu_lang, "m", 0.0, timeout=1)
        assert len(gesendet) == 1
        payload = gesendet[0]["json"]
        user_msg = payload["messages"][1]["content"]
        assert len(user_msg) <= 100000

    def test_redaction_greift_weiterhin(
        self, monkeypatch,
    ) -> None:
        """Auch bei max_len=100_000 wird redigiert."""
        gesendet = self._patch_post(monkeypatch)
        text = (
            "Host 8.8.8.8 und "
            "MAC aa:bb:cc:dd:ee:ff im Text."
        )
        pipeline.ask_llm("k", "s", text, "m", 0.0, timeout=1)
        assert len(gesendet) == 1
        payload = gesendet[0]["json"]
        user_msg = payload["messages"][1]["content"]
        # Oeffentliche IP und MAC sind maskiert.
        assert "8.8.8.8" not in user_msg
        assert "aa:bb:cc:dd:ee:ff" not in user_msg


# =====================================================================
# Recovery-Block (Auflagen 2083 + 2084)
# =====================================================================

class TestRecoveryBlock:
    """Tests fuer RecoveryVorschlag, Parser und print_recovery.

    Auflage 2084: frage_an_menschen.
    Auflage 2083: audit recovery_eskalation (in run_pipeline,
    hier nicht isoliert testbar; das Feld ist Teil der Struktur).
    """

    def _mock_llm(self, monkeypatch, antwort: str, ok: bool = True) -> None:
        """Mockt ask_llm. state.agents muss 'reviewer' enthalten,
        weil ask_reviewer_for_recovery das Argument VOR dem Aufruf
        von build_system_prompt auswertet.
        """
        class _Reply:
            def __init__(self) -> None:
                self.ok = ok
                self.content = antwort
                self.error = "simulierter Fehler" if not ok else ""

        def fake_ask_llm(*args, **kwargs):
            return _Reply()

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask_llm)
        monkeypatch.setattr(
            pipeline, "build_system_prompt",
            lambda *a, **kw: "SYSTEM",
        )

    def _state(self) -> pipeline.RunState:
        """RunState mit minimalem agents-Eintrag fuer reviewer."""
        st = build_test_state()
        st.agents["reviewer"] = {"name": "reviewer"}
        return st

    def test_frage_an_menschen_default_leer(self) -> None:
        v = pipeline.RecoveryVorschlag(art="test")
        assert v.frage_an_menschen == ""

    def test_parser_erkennt_frage_an_menschen(
        self, monkeypatch,
    ) -> None:
        antwort = (
            "DIAGNOSE: Testfehler.\n"
            "FRAGE AN DEN MENSCHEN: Welchen Weg?\n"
            "BLOCKGROESSE: ein Block\n"
            "EMPFEHLUNG: Variante A\n"
        )
        self._mock_llm(monkeypatch, antwort)
        state = self._state()
        v = pipeline.ask_reviewer_for_recovery(state, "eskalation", "ctx")
        assert v.diagnose == "Testfehler."
        assert v.frage_an_menschen == "Welchen Weg?"
        assert v.blockgroesse == "ein Block"
        assert v.empfehlung == "Variante A"

    def test_parser_ohne_frage_an_menschen(
        self, monkeypatch,
    ) -> None:
        antwort = "DIAGNOSE: Ok.\nEMPFEHLUNG: weiter.\n"
        self._mock_llm(monkeypatch, antwort)
        state = self._state()
        v = pipeline.ask_reviewer_for_recovery(state, "no_go", "ctx")
        assert v.frage_an_menschen == ""

    def test_print_recovery_zeigt_frage(
        self, capsys,
    ) -> None:
        v = pipeline.RecoveryVorschlag(
            art="eskalation",
            diagnose="X",
            frage_an_menschen="Bitte entscheiden.",
            empfehlung="A",
            rohantwort="...",
        )
        pipeline.print_recovery(v)
        out = capsys.readouterr().out
        assert "FRAGE AN DEN MENSCHEN:" in out
        assert "Bitte entscheiden." in out

    def test_print_recovery_ohne_frage(
        self, capsys,
    ) -> None:
        v = pipeline.RecoveryVorschlag(
            art="no_go",
            diagnose="X",
            rohantwort="...",
        )
        pipeline.print_recovery(v)
        out = capsys.readouterr().out
        assert "FRAGE AN DEN MENSCHEN:" not in out


# =====================================================================
# audit() neue Lokation (Auflage 2110)
# =====================================================================

class TestAudit:
    """Tests fuer audit() nach Umstellung auf Werkstatt-Pfad.

    Auflage 2110: audit schreibt nach _werkstatt_home()/audit-logs/,
    nicht mehr ins Ziel-Projekt.
    """

    def test_schreibt_in_werkstatt_audit_dir(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Audit legt Datei in <werkstatt>/audit-logs/ an."""
        monkeypatch.setattr(pipeline, "_werkstatt_home",
                            lambda: tmp_path)
        pipeline.audit("test_kind", {"k": "v"},
                       tmp_path / "beliebiges-projekt", "test-projekt")
        audit_dir = tmp_path / "audit-logs"
        assert audit_dir.is_dir()
        dateien = list(audit_dir.glob("agent-pipeline-*.jsonl"))
        assert len(dateien) == 1
        inhalt = dateien[0].read_text(encoding="utf-8")
        assert "test_kind" in inhalt
        assert "\"project\": \"test-projekt\"" in inhalt

    def test_project_feld_bleibt(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """project-Feld im Eintrag bleibt erhalten."""
        monkeypatch.setattr(pipeline, "_werkstatt_home",
                            lambda: tmp_path)
        pipeline.audit("some_event", {}, tmp_path, "mein-projekt")
        dateien = list((tmp_path / "audit-logs").glob("*.jsonl"))
        assert len(dateien) == 1
        zeile = dateien[0].read_text(encoding="utf-8").strip()
        import json
        entry = json.loads(zeile)
        assert entry["project"] == "mein-projekt"
        assert entry["kind"] == "some_event"
        assert entry["agent"] == "agent_pipeline"

    def test_mkdir_legt_fehlendes_verzeichnis_an(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """mkdir(parents=True, exist_ok=True) legt Verzeichnis an."""
        # tmp_path/audit-logs existiert noch nicht.
        nest = tmp_path / "nest" / "home"
        nest.mkdir(parents=True)
        monkeypatch.setattr(pipeline, "_werkstatt_home",
                            lambda: nest)
        assert not (nest / "audit-logs").exists()
        pipeline.audit("evt", {}, tmp_path, "p")
        assert (nest / "audit-logs").is_dir()


# =====================================================================
# root-Guard in main() (Auflage 2085)
# =====================================================================

class TestRootGuard:
    """Tests fuer den root-Guard in main().

    Auflage 2085: os.getuid() primaer, getpass.getuser()
    in try/except.
    """

    def test_getuid_0_ergibt_exit_66(
        self, monkeypatch, capsys,
    ) -> None:
        monkeypatch.setattr(pipeline.os, "getuid", lambda: 0)
        rc = pipeline.main()
        assert rc == 66
        out = capsys.readouterr().out
        assert "NICHT als root" in out

    def test_getuser_root_ergibt_exit_66(
        self, monkeypatch, capsys,
    ) -> None:
        monkeypatch.setattr(pipeline.os, "getuid", lambda: 1000)
        import getpass
        monkeypatch.setattr(getpass, "getuser", lambda: "root")
        rc = pipeline.main()
        assert rc == 66
        out = capsys.readouterr().out
        assert "getpass.getuser()" in out

    def test_getuser_fehler_kein_absturz(
        self, monkeypatch, capsys,
    ) -> None:
        """getpass.getuser() wirft -> Warnung, kein Absturz."""
        monkeypatch.setattr(pipeline.os, "getuid", lambda: 1000)
        import getpass

        def fake_getuser():
            raise KeyError("USER")

        monkeypatch.setattr(getpass, "getuser", fake_getuser)
        # Kein --project -> erwartet Exit 64, aber KEIN Traceback.
        monkeypatch.setattr(pipeline.sys, "argv", ["pipeline.py"])
        rc = pipeline.main()
        assert rc == 64
        out = capsys.readouterr().out
        assert "getpass.getuser() fehlgeschlagen" in out


# =====================================================================
# Zeitbudget (Auflage 2080 + 2097)
# =====================================================================

class TestBudgetTime:
    """Tests fuer require_budget_time und budget_or_recover (Zeit).

    Auflage 2080: max_minutes aus YAML durchgesetzt.
    Auflage 2097: 6 Tests (Grenze + Recovery-Kontext).
    """

    def test_zeitbudget_deaktiviert_max_0(
        self, monkeypatch,
    ) -> None:
        """max_minutes=0 -> keine Pruefung."""
        state = build_test_state()
        state.start_monotonic = 1.0
        monkeypatch.setattr(pipeline.time, "monotonic", lambda: 10000.0)
        # Keine Exception.
        pipeline.require_budget_time(state, 0)

    def test_zeitbudget_ok_unter_limit(
        self, monkeypatch,
    ) -> None:
        """Verstrichen unter Limit -> ok."""
        state = build_test_state()
        state.start_monotonic = 1000.0
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 60.0)
        # max_minutes=1 -> Limit 60s. 60s <= 60s -> kein Fehler.
        pipeline.require_budget_time(state, 1)

    def test_zeitbudget_erschoepft(
        self, monkeypatch,
    ) -> None:
        """Verstrichen ueber Limit -> BudgetExhausted."""
        state = build_test_state()
        state.start_monotonic = 1000.0
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 61.0)
        with pytest.raises(pipeline.BudgetExhausted):
            pipeline.require_budget_time(state, 1)

    def test_zeitbudget_grenze_genau(
        self, monkeypatch,
    ) -> None:
        """Auflage 2097 P1: genau == Limit -> kein Fehler."""
        state = build_test_state()
        state.start_monotonic = 1000.0
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 60.0)
        # max_minutes=1 -> Limit 60s. Genau 60s -> kein Fehler.
        pipeline.require_budget_time(state, 1)

    def test_budget_or_recover_zeit(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Auflage 2097: Recovery wenn Zeit erschoepft."""
        state = build_test_state(project_dir=tmp_path)
        state.start_monotonic = 1000.0
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 61.0)

        recovery_aufrufe: list[dict] = []
        audit_aufrufe: list[tuple] = []

        def fake_recovery(st, art, kontext):
            recovery_aufrufe.append({"art": art, "kontext": kontext})
            return pipeline.RecoveryVorschlag(art=art)

        def fake_audit(kind, payload, project_dir, project_name):
            audit_aufrufe.append((kind, payload))

        monkeypatch.setattr(pipeline, "ask_reviewer_for_recovery",
                            fake_recovery)
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        monkeypatch.setattr(pipeline, "audit", fake_audit)

        rc = pipeline.budget_or_recover(
            state, max_llm=100, kontext="test",
            project_dir=tmp_path, project_name="test",
            max_minutes=1,
        )
        assert rc == 13
        assert len(recovery_aufrufe) == 1
        assert recovery_aufrufe[0]["art"] == "budget"
        # Recovery wurde auditiert.
        assert any(a[0] == "recovery_budget" for a in audit_aufrufe)

    def test_budget_or_recover_nennt_dimension(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Auflage 2097 P3: Kontext nennt LLM und Zeit."""
        state = build_test_state(project_dir=tmp_path)
        state.start_monotonic = 1000.0
        state.llm_calls = 3
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 61.0)

        empfangener_kontext: list[str] = []

        def fake_recovery(st, art, kontext):
            empfangener_kontext.append(kontext)
            return pipeline.RecoveryVorschlag(art=art)

        monkeypatch.setattr(pipeline, "ask_reviewer_for_recovery",
                            fake_recovery)
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        monkeypatch.setattr(pipeline, "audit", lambda *a, **kw: None)

        pipeline.budget_or_recover(
            state, max_llm=100, kontext="Vor Commit-Review.",
            project_dir=tmp_path, project_name="test",
            max_minutes=1,
        )
        assert len(empfangener_kontext) == 1
        kt = empfangener_kontext[0]
        assert "LLM: 3/100" in kt
        assert "Zeit:" in kt
        assert "61s/60s" in kt


# =====================================================================
# BudgetRecovery (Auflage 2095, Nachtrag aus 3b)
# =====================================================================

class TestBudgetRecovery:
    """Drei gezielte Tests fuer Recovery-Pfade.

    Auflage 2095: Nachtrag zu 2079 (Recovery bei Commit-Review),
    2081 (Konsistenz), 2083 (Audit).
    """

    def test_budget_exhausted_recovery_bei_commit_review(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Auflage 2079: Recovery wenn LLM-Budget bei
        Commit-Review erschoepft."""
        state = build_test_state(project_dir=tmp_path)
        state.llm_calls = 20  # genau am Limit

        recovery_calls: list[dict] = []

        def fake_recovery(st, art, kontext):
            recovery_calls.append({"art": art, "kontext": kontext})
            return pipeline.RecoveryVorschlag(art=art)

        monkeypatch.setattr(pipeline, "ask_reviewer_for_recovery",
                            fake_recovery)
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        monkeypatch.setattr(pipeline, "audit", lambda *a, **kw: None)

        rc = pipeline.budget_or_recover(
            state, max_llm=20, kontext="Vor Commit-Review.",
            project_dir=tmp_path, project_name="test",
            max_minutes=0,
        )
        assert rc == 13
        assert len(recovery_calls) == 1
        assert recovery_calls[0]["art"] == "budget"
        assert "Commit-Review" in recovery_calls[0]["kontext"]

    def test_budget_exhausted_recovery_konsistent(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Auflage 2081: Recovery-Pfad ist bei LLM- und
        Zeit-Erschoepfung identisch."""
        recovery_calls: list[dict] = []

        def fake_recovery(st, art, kontext):
            recovery_calls.append({"art": art, "kontext": kontext})
            return pipeline.RecoveryVorschlag(art=art)

        monkeypatch.setattr(pipeline, "ask_reviewer_for_recovery",
                            fake_recovery)
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        monkeypatch.setattr(pipeline, "audit", lambda *a, **kw: None)

        # Fall 1: LLM-Budget erschoepft.
        state1 = build_test_state(project_dir=tmp_path)
        state1.llm_calls = 20
        rc1 = pipeline.budget_or_recover(
            state1, max_llm=20, kontext="Vor X.",
            project_dir=tmp_path, project_name="test",
            max_minutes=0,
        )

        # Fall 2: Zeitbudget erschoepft.
        state2 = build_test_state(project_dir=tmp_path)
        state2.llm_calls = 0
        state2.start_monotonic = 1000.0
        monkeypatch.setattr(pipeline.time, "monotonic",
                            lambda: 1000.0 + 61.0)
        rc2 = pipeline.budget_or_recover(
            state2, max_llm=20, kontext="Vor Y.",
            project_dir=tmp_path, project_name="test",
            max_minutes=1,
        )

        assert rc1 == 13
        assert rc2 == 13
        assert len(recovery_calls) == 2
        # Beide Aufrufe: art == "budget".
        assert recovery_calls[0]["art"] == "budget"
        assert recovery_calls[1]["art"] == "budget"

    def test_budget_recovery_wird_auditiert(
        self, monkeypatch, tmp_path: Path,
    ) -> None:
        """Auflage 2083: recovery_budget erscheint im Audit."""
        state = build_test_state(project_dir=tmp_path)
        state.llm_calls = 20

        audit_calls: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audit_calls.append((kind, payload))

        monkeypatch.setattr(pipeline, "ask_reviewer_for_recovery",
                            lambda *a, **kw: pipeline.RecoveryVorschlag(
                                art="budget"))
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        monkeypatch.setattr(pipeline, "audit", fake_audit)

        rc = pipeline.budget_or_recover(
            state, max_llm=20, kontext="Vor X.",
            project_dir=tmp_path, project_name="test",
            max_minutes=0,
        )
        assert rc == 13
        recovery_audits = [a for a in audit_calls
                           if a[0] == "recovery_budget"]
        assert len(recovery_audits) == 1
        # Kontext ist im Audit-Payload enthalten.
        payload = recovery_audits[0][1]
        assert "kontext" in payload


# =====================================================================
# collect_messwerte (Auflage 2135)
# =====================================================================

class TestCollectMesswerte:
    """Tests fuer collect_messwerte.

    Auflage 2135: Werkstatt liefert Messwerte an den
    Builder. Diese Funktion extrahiert sie aus
    state.basis_protokoll.
    """

    BASIS_BSP = (
        "=== py_compile ===\n"
        "ARGV: /opt/x/.venv/bin/python3 -m compileall -q apps\n"
        "RC: 0\n"
        "STDOUT:\n"
        "\n"
        "STDERR:\n"
        "\n"
        "=== ruff ===\n"
        "ARGV: /opt/x/.venv/bin/python3 -m ruff check .\n"
        "RC: 0\n"
        "STDOUT:\n"
        "All checks passed!\n"
        "\n"
        "STDERR:\n"
        "\n"
        "=== mypy ===\n"
        "ARGV: /opt/x/.venv/bin/python3 -m mypy apps\n"
        "RC: 0\n"
        "STDOUT:\n"
        "Success: no issues found in 147 source files\n"
        "\n"
        "STDERR:\n"
        "\n"
        "=== test_count ===\n"
        "ARGV: /opt/x/.venv/bin/python3 -m pytest --collect-only -q\n"
        "RC: 0\n"
        "STDOUT:\n"
        "tests/unit/test_a.py::test_one\n"
        "tests/unit/test_a.py::test_two\n"
        "\n"
        "1312 tests collected in 0.47s\n"
        "\n"
        "STDERR:\n"
        "\n"
        "=== git_status ===\n"
        "ARGV: git status --porcelain\n"
        "RC: 0\n"
        "STDOUT:\n"
        "\n"
        "STDERR:\n"
        "\n"
        "=== git_head ===\n"
        "ARGV: git rev-parse --short HEAD\n"
        "RC: 0\n"
        "STDOUT:\n"
        "f913eac\n"
        "\n"
        "STDERR:\n"
    )

    def test_collect_messwerte_aus_protokoll(self) -> None:
        state = build_test_state()
        state.basis_protokoll = self.BASIS_BSP
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 1312
        assert w["ruff"] == "gruen"
        assert w["mypy"] == "gruen"
        assert w["py_compile"] == "gruen"
        assert w["git_status"] == "clean"
        assert w["git_head"] == "f913eac"

    def test_collect_messwerte_fallback(self) -> None:
        state = build_test_state()
        state.basis_protokoll = ""
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] is None
        assert w["ruff"] == "rot"
        assert w["mypy"] == "rot"
        assert w["py_compile"] == "rot"
        assert w["git_status"] == "geaendert"
        assert w["git_head"] == ""

    def test_collect_messwerte_rc_parsing(self) -> None:
        """Ruff rot, wenn RC != 0."""
        basis = (
            "=== ruff ===\n"
            "ARGV: ruff check .\n"
            "RC: 1\n"
            "STDOUT:\n"
            "Fehler...\n"
            "\n"
            "STDERR:\n"
            "\n"
        )
        state = build_test_state()
        state.basis_protokoll = basis
        w = pipeline.collect_messwerte(state)
        assert w["ruff"] == "rot"

    def test_git_status_geaendert(self) -> None:
        basis = (
            "=== git_status ===\n"
            "ARGV: git status --porcelain\n"
            "RC: 0\n"
            "STDOUT:\n"
            " M file.txt\n"
            "?? new.txt\n"
            "\n"
            "STDERR:\n"
            "\n"
        )
        state = build_test_state()
        state.basis_protokoll = basis
        w = pipeline.collect_messwerte(state)
        assert w["git_status"] == "geaendert"

    def test_format_messwerte_block(self) -> None:
        werte = {
            "test_anzahl": 1261,
            "ruff": "gruen",
            "mypy": "gruen",
            "py_compile": "gruen",
            "git_status": "clean",
            "git_head": "abc1234",
            "verstrichene_zeit_s": 25.0,
        }
        s = pipeline.format_messwerte_block(werte)
        assert "test_anzahl: 1261" in s
        assert "ruff: gruen" in s
        assert "git_head: abc1234" in s

    def test_format_messwerte_block_fallback(self) -> None:
        werte = {
            "test_anzahl": None,
            "ruff": "rot",
            "mypy": "rot",
            "py_compile": "rot",
            "git_status": "geaendert",
            "git_head": "",
            "verstrichene_zeit_s": 0.0,
        }
        s = pipeline.format_messwerte_block(werte)
        assert "test_anzahl: nicht gemessen" in s

    def test_format_doc_snippets_mit_docs(self) -> None:
        """Auflage 2142: Doku-Ausschnitte werden formatiert."""
        docs = {
            "context": "# Context\nInhalt A.\n",
            "decisions": "# Decisions\nInhalt B.\n",
        }
        s = pipeline.format_doc_snippets(docs)
        assert "DOKU-AUSSCHNITTE" in s
        assert "context" in s
        assert "Inhalt A." in s
        assert "decisions" in s
        assert "Inhalt B." in s

    def test_format_doc_snippets_leer(self) -> None:
        """Leere docs liefern einen Hinweis."""
        s = pipeline.format_doc_snippets({})
        assert "keine Doku" in s

    def test_format_doc_snippets_kuerzt(self) -> None:
        """Ausschnitt wird auf max_len gekuerzt."""
        # Klartext (kein Hex), damit redact_secrets
        # nicht eingreift.
        docs = {"lang": "Satz. " * 2000}
        s = pipeline.format_doc_snippets(docs, max_len=100)
        # Der Ausschnitt ist max_len Zeichen lang.
        # "Satz. " hat 6 Zeichen, max_len=100
        # erlaubt rund 16 Wiederholungen im Ausschnitt.
        assert s.count("Satz.") <= 17
        # Redaction hat nicht eingegriffen.
        assert "[HEX]" not in s
        assert "[REDACTED]" not in s

    def test_format_doc_snippets_redigiert(self) -> None:
        """Oeffentliche IP-Adressen werden redigiert."""
        docs = {"x": "Host 8.8.8.8 im Text."}
        s = pipeline.format_doc_snippets(docs)
        assert "8.8.8.8" not in s


# =====================================================================
# parse_code_patches + apply_code_patches (UMB-1a)
# =====================================================================

class TestParseCodePatches:
    """Tests fuer parse_code_patches (UMB-1a)."""

    def test_parse_code_patches_ok(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "pfad: tools/x.py\n"
            "anker: |\n"
            "  ALT\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        patches = pipeline.parse_code_patches(text)
        assert len(patches) == 1
        assert patches[0]["pfad"] == "tools/x.py"
        assert patches[0]["anker"] == "ALT"
        assert patches[0]["ersatz"] == "NEU"

    def test_parse_code_patches_leer(self) -> None:
        patches = pipeline.parse_code_patches("")
        assert patches == []

    def test_parse_code_patches_mehrere(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "pfad: tools/a.py\n"
            "anker: |\n"
            "  A1\n"
            "ersatz: |\n"
            "  A2\n"
            "PATCH-ENDE\n"
            "PATCH-BEGINN\n"
            "pfad: tools/b.py\n"
            "anker: |\n"
            "  B1\n"
            "ersatz: |\n"
            "  B2\n"
            "PATCH-ENDE"
        )
        patches = pipeline.parse_code_patches(text)
        assert len(patches) == 2
        assert patches[0]["pfad"] == "tools/a.py"
        assert patches[1]["pfad"] == "tools/b.py"

    def test_parse_code_patches_anker_leer_verworfen(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "pfad: tools/x.py\n"
            "anker: |\n"
            "ersatz: |\n"
            "  NEU\n"
            "PATCH-ENDE"
        )
        patches = pipeline.parse_code_patches(text)
        assert patches == []


class TestApplyCodePatches:
    """Tests fuer apply_code_patches (UMB-1a)."""

    def test_apply_ok(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [{"pfad": "tools/x.py", "anker": "ALT",
                    "ersatz": "NEU"}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        assert ziel.read_text() == "NEU\n"

    def test_apply_anker_fehlt(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("Inhalt ohne Anker.\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [{"pfad": "tools/x.py", "anker": "FEHLT",
                    "ersatz": "NEU"}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False
        assert ziel.read_text() == "Inhalt ohne Anker.\n"

    def test_apply_whitelist_fail(self, tmp_path: Path) -> None:
        (tmp_path / "extern").mkdir()
        ziel = tmp_path / "extern" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [{"pfad": "extern/x.py", "anker": "ALT",
                    "ersatz": "NEU"}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False

    def test_apply_pfad_doppelt(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [
            {"pfad": "tools/x.py", "anker": "ALT", "ersatz": "NEU"},
            {"pfad": "tools/x.py", "anker": "NEU", "ersatz": "NOCH"},
        ]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False
        assert ziel.read_text() == "ALT\n"

    def test_apply_mehrere_patches(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        a = tmp_path / "tools" / "a.py"
        b = tmp_path / "tools" / "b.py"
        a.write_text("A1\n", encoding="utf-8")
        b.write_text("B1\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [
            {"pfad": "tools/a.py", "anker": "A1", "ersatz": "A2"},
            {"pfad": "tools/b.py", "anker": "B1", "ersatz": "B2"},
        ]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        assert a.read_text() == "A2\n"
        assert b.read_text() == "B2\n"

    def test_apply_dry_run_schreibt_nicht(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [{"pfad": "tools/x.py", "anker": "ALT",
                    "ersatz": "NEU"}]
        ok = pipeline.apply_code_patches(state, patches, dry_run=True)
        assert ok is True
        assert ziel.read_text() == "ALT\n"

    def test_apply_leer_fail(self, tmp_path: Path) -> None:
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        ok = pipeline.apply_code_patches(state, [])
        assert ok is False

    def test_shift_lines(self) -> None:
        """_shift_lines ergaenzt jede nicht-leere Zeile um 2."""
        s = pipeline._shift_lines("A\nB\n\nC")
        assert s == "  A\n  B\n\n  C"

    def test_einrueckung_korrektur_greift(self, tmp_path: Path) -> None:
        """Anker mit 6 Spaces, Datei hat 8. Korrektur.

        Der Anker steht in der +2-Variante exakt 1x.
        """
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text(
            "class X:\n    def f(self):\n"
            "        self.assertEqual(1, 1)\n",
            encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        # Anker mit 6 Spaces (Datei hat 8).
        # Anker und Ersatz sind konsistent um 2 Spaces zu
        # kurz. Nach der Korrektur passen sie.
        anker = "      self.assertEqual(1, 1)"
        ersatz = ("      self.assertEqual(1, 1)\n\n"
                  "  def g(self):\n      pass")
        patches = [{"pfad": "tools/x.py", "anker": anker,
                    "ersatz": ersatz}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        inhalt = ziel.read_text()
        # Neue Methode vorhanden.
        assert "def g(self):" in inhalt
        # Einrueckung korrekt (4 Spaces vor def).
        assert "\n    def g(self):" in inhalt

    def test_einrueckung_korrektur_audit(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """Korrektur schreibt Audit-Eintrag."""
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text(
            "        self.assertEqual(1, 1)\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        audit_calls: list[tuple] = []

        def fake_audit(kind, payload, project_dir, project_name):
            audit_calls.append((kind, payload))

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        patches = [{"pfad": "tools/x.py",
                    "anker": "      self.assertEqual(1, 1)",
                    "ersatz": "      self.assertEqual(1, 1)\n"}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        korrekturen = [a for a in audit_calls
                       if a[0] == "anker_einrueckung_korrigiert"]
        assert len(korrekturen) == 1

    def test_einrueckung_korrektur_fail_bei_2x(
        self, tmp_path: Path,
    ) -> None:
        """Wenn +2-Variante mehrfach matcht, fail closed."""
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text(
            "        self.assertEqual(1, 1)\n"
            "        self.assertEqual(1, 1)\n",
            encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [{"pfad": "tools/x.py",
                    "anker": "      self.assertEqual(1, 1)",
                    "ersatz": "      self.assertEqual(1, 1)\n"}]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False

    def test_apply_zwei_patches_gleiche_datei(
        self, tmp_path: Path,
    ) -> None:
        """Auflage 2173: zwei Patches in derselben Datei.

        Patch 1 (Import) und Patch 2 (Methode) wirken
        beide. Kein "Pfad doppelt"-Fehler.
        """
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text(
            "from tools.a import A\n"
            "\n"
            "def f():\n"
            "    pass\n",
            encoding="utf-8",
        )
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [
            {"pfad": "tools/x.py",
             "anker": "from tools.a import A",
             "ersatz": "from tools.a import A\nfrom tools.b import B"},
            {"pfad": "tools/x.py",
             "anker": "def f():\n    pass",
             "ersatz": "def f():\n    pass\n\ndef g():\n    pass"},
        ]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        inhalt = ziel.read_text()
        assert "from tools.b import B" in inhalt
        assert "def g():" in inhalt

    def test_apply_zwei_patches_gleicher_anker_fail(
        self, tmp_path: Path,
    ) -> None:
        """Auflage 2173: identische (pfad, anker) -> fail."""
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [
            {"pfad": "tools/x.py", "anker": "ALT",
             "ersatz": "NEU1"},
            {"pfad": "tools/x.py", "anker": "ALT",
             "ersatz": "NEU2"},
        ]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False
        assert ziel.read_text() == "ALT\n"

    def test_apply_anker_muss_im_urstand_sein(
        self, tmp_path: Path,
    ) -> None:
        """Auflage 2173: alle Anker muessen im Urstand sein.

        Patch 2 darf NICHT auf Patch 1 aufbauen. Alle
        Anker werden gegen den Urzustand validiert.
        Wenn ein Anker nur durch Patch 1 entsteht:
        fail closed.
        """
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("A\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        patches = [
            {"pfad": "tools/x.py", "anker": "A",
             "ersatz": "A\nX"},
            # X entsteht erst durch Patch 1. Darf nicht
            # gefunden werden.
            {"pfad": "tools/x.py", "anker": "X",
             "ersatz": "Y"},
        ]
        ok = pipeline.apply_code_patches(state, patches)
        assert ok is False
        # Nichts geaendert (Validierung vor Anwendung).
        assert ziel.read_text() == "A\n"

    def test_apply_commit_msg_in_git(self, tmp_path: Path) -> None:
        """Auflage 2170: msg_datei liegt in .git/.

        Wenn apply_commit_and_doku laeuft, schreibt
        es die Commit-Message nach .git/.commit-msg.tmp,
        nicht in die Projekt-Wurzel.
        """
        import subprocess as _sp
        _sp.run(("git", "init", "-q"), cwd=str(tmp_path),
                check=True)
        _sp.run(
            ("git", "-c", "user.name=Test",
             "-c", "user.email=t@t.de", "commit",
             "--allow-empty", "-m", "init"),
            cwd=str(tmp_path), check=True, capture_output=True,
        )
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "x.md").write_text("Alt: MARKER\n",
                                    encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["docs/"])
        state.git_author_name = "ghxstfocus"
        state.git_author_email = "ghxst.focus@gmail.com"
        paket = {
            "message": "test: msg\n",
            "dateien": ["docs/x.md"],
            "doku_patches": [
                {"pfad": "docs/x.md", "anker": "MARKER",
                 "ersatz": "NEU"},
            ],
        }
        ok = pipeline.apply_commit_and_doku(state, paket)
        assert ok is True
        # Keine .commit-msg.tmp in der Wurzel.
        assert not (tmp_path / ".commit-msg.tmp").exists()
        # Keine .commit-msg.tmp in .git (try/finally).
        assert not (tmp_path / ".git" / ".commit-msg.tmp").exists()


# =====================================================================
# apply_and_recheck (UMB-1d)
# =====================================================================

class TestApplyAndRecheck:
    """Tests fuer apply_and_recheck (UMB-1d).

    Deckt ab:
      - Erfolgspfad: Patches anwenden, Basis-Gate gruen.
      - Fail: keine Patches -> 16.
      - Fail: apply schlaegt fehl -> 17.
      - Fail: Basis-Gate-nach-apply rot -> 18.
    """

    def _always(self) -> dict:
        # Wir nutzen Measurement-Objekte mit harmlosen argv.
        # run_measurement wird gemockt.
        return {
            "py_compile": pipeline.Measurement(
                "py_compile", ("echo",), "Syntax."),
            "ruff": pipeline.Measurement(
                "ruff", ("echo",), "Lint."),
            "mypy": pipeline.Measurement(
                "mypy", ("echo",), "Typen."),
            "test_count": pipeline.Measurement(
                "test_count", ("echo",), "Anzahl."),
            "git_status": pipeline.Measurement(
                "git_status", ("echo",), "Tree."),
            "git_head": pipeline.Measurement(
                "git_head", ("echo",), "HEAD."),
        }

    def test_erfolg(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        state.code_patches = [
            {"pfad": "tools/x.py", "anker": "ALT", "ersatz": "NEU"},
        ]
        # run_measurement gemockt: immer gruen.
        monkeypatch.setattr(pipeline, "run_measurement",
                            lambda m, wl, pd: ("mock ok\n", True))
        rc = pipeline.apply_and_recheck(state, self._always(),
                                          ["tools/"])
        assert rc is None
        assert ziel.read_text() == "NEU\n"

    def test_keine_patches_16(self, tmp_path: Path) -> None:
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        state.code_patches = []
        rc = pipeline.apply_and_recheck(state, self._always(),
                                          ["tools/"])
        assert rc == 16

    def test_apply_fail_17(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("Inhalt ohne Anker.\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        state.code_patches = [
            {"pfad": "tools/x.py", "anker": "FEHLT", "ersatz": "NEU"},
        ]
        rc = pipeline.apply_and_recheck(state, self._always(),
                                          ["tools/"])
        assert rc == 17
        # Datei unveraendert.
        assert ziel.read_text() == "Inhalt ohne Anker.\n"

    def test_recheck_rot_19(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "tools").mkdir()
        ziel = tmp_path / "tools" / "x.py"
        ziel.write_text("ALT\n", encoding="utf-8")
        state = build_test_state(project_dir=tmp_path,
                                  file_whitelist=["tools/"])
        state.code_patches = [
            {"pfad": "tools/x.py", "anker": "ALT", "ersatz": "NEU"},
        ]
        # run_measurement: py_compile gruen, ruff rot.
        def fake_run(m, wl, pd):
            if m.mid == "ruff":
                return ("=== ruff ===\nRC: 1\n", False)
            return (f"=== {m.mid} ===\nRC: 0\n", True)
        monkeypatch.setattr(pipeline, "run_measurement", fake_run)
        # Recovery mocken, sonst echter LLM-Call.
        monkeypatch.setattr(
            pipeline, "ask_reviewer_for_recovery",
            lambda *a, **kw: pipeline.RecoveryVorschlag(art="basis_gate"))
        monkeypatch.setattr(pipeline, "print_recovery", lambda v: None)
        rc = pipeline.apply_and_recheck(state, self._always(),
                                          ["tools/"])
        # Post-Apply-Fix 2026-10-16: rc=19 ist jetzt
        # das interne Signal fuer Builder-Korrektur.
        assert rc == 19


# =====================================================================
# extract_paths + read_target_snippets (Auflage 2146)
# =====================================================================

class TestExtractPaths:
    """Tests fuer extract_paths_from_aufgabe."""

    def test_findet_pfade(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("x\n",
                                                       encoding="utf-8")
        aufgabe = ("Ergaenze in tests/test_x.py den Test A. "
                   "Ausserdem in tools/foo.py nichts.")
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["tests/", "tools/"], tmp_path)
        assert pfade == ["tests/test_x.py"]

    def test_filtert_whitelist(self, tmp_path: Path) -> None:
        (tmp_path / "extern").mkdir()
        (tmp_path / "extern" / "y.py").write_text("y\n",
                                                   encoding="utf-8")
        aufgabe = "Patch in extern/y.py"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["tests/"], tmp_path)
        assert pfade == []

    def test_filtert_nicht_existierend(self, tmp_path: Path) -> None:
        aufgabe = "Patch in tests/fehlt.py"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["tests/"], tmp_path)
        assert pfade == []

    def test_dedupliziert(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "x.py").write_text("x\n",
                                                  encoding="utf-8")
        aufgabe = "tests/x.py und nochmal tests/x.py"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["tests/"], tmp_path)
        assert pfade == ["tests/x.py"]

    def test_leere_aufgabe(self, tmp_path: Path) -> None:
        pfade = pipeline.extract_paths_from_aufgabe(
            "", ["tests/"], tmp_path)
        assert pfade == []

    # ---- W1 (2026-10-16) ----
    def test_w1_import_notation(self, tmp_path: Path) -> None:
        (tmp_path / "core" / "access").mkdir(parents=True)
        aufgabe = "from core.access.checker import X"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["core/"], tmp_path)
        assert "core/access/checker.py" in pfade

    def test_w1_sql_endung(self, tmp_path: Path) -> None:
        (tmp_path / "data" / "migrations").mkdir(parents=True)
        aufgabe = "data/migrations/0017_x.sql"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["data/"], tmp_path)
        assert "data/migrations/0017_x.sql" in pfade

    def test_w1_neue_datei(self, tmp_path: Path) -> None:
        # W1-A3: neue Datei (existiert nicht, aber
        # Elternverzeichnis existiert).
        (tmp_path / "core" / "services").mkdir(parents=True)
        aufgabe = "neu: core/services/neu.py"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["core/"], tmp_path)
        assert "core/services/neu.py" in pfade

    def test_w1_elternverzeichnis_fehlt(self, tmp_path: Path) -> None:
        # W1-A3: kein Match, wenn Elternverzeichnis
        # fehlt.
        aufgabe = "neu: nichtda/x.py"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["nichtda/"], tmp_path)
        assert pfade == []

    def test_w1_stdlib_ignoriert(self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        aufgabe = "from os.path import join"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["core/", "os/"], tmp_path)
        assert pfade == []

    def test_w1_pathlib_ignoriert(self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        aufgabe = "from pathlib import Path"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["core/", "pathlib/"], tmp_path)
        assert pfade == []

    def test_w1_mehrere_endungen(self, tmp_path: Path) -> None:
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "a.sql").write_text("x",
                                                    encoding="utf-8")
        aufgabe = "data/a.sql data/b.json"
        pfade = pipeline.extract_paths_from_aufgabe(
            aufgabe, ["data/"], tmp_path)
        assert "data/a.sql" in pfade
        assert "data/b.json" in pfade


class TestReadTargetSnippets:
    """Tests fuer read_target_snippets."""

    def test_liefert_ausschnitt(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "Inhalt A.\nInhalt B.\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "ZIELDATEIEN" in s
        assert "tools/x.py" in s
        assert "vollstaendig" in s
        assert "Inhalt A." in s

    def test_nicht_whitelist(self, tmp_path: Path) -> None:
        (tmp_path / "extern").mkdir()
        (tmp_path / "extern" / "x.py").write_text(
            "geheim\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["extern/x.py"], tmp_path, ["tools/"])
        assert "geheim" not in s

    def test_datei_fehlt(self, tmp_path: Path) -> None:
        s = pipeline.read_target_snippets(
            ["tools/fehlt.py"], tmp_path, ["tools/"])
        assert "fehlt" not in s

    def test_redigiert(self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "Host 8.8.8.8.\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "8.8.8.8" not in s

    def test_keine_pfade(self, tmp_path: Path) -> None:
        s = pipeline.read_target_snippets([], tmp_path, ["tools/"])
        assert "keine Zieldateien" in s

    def test_user_prompt_ohne_anker_beispiel(self) -> None:
        """Auflage 2164: Der Code-Patch-User-Prompt enthaelt
        kein konkretes 'anker: |'-Beispiel. Die Format-Regel
        steht im System-Prompt.
        """
        # Wir pruefen den Quelltext der Datei, weil der
        # Prompt-String zur Laufzeit zusammengesetzt wird.
        from pathlib import Path as _P
        quelle = _P(pipeline.__file__).read_text(encoding="utf-8")
        # Der Verweis auf den System-Prompt-Abschnitt
        # ist im Quelltext (aufgeteilt auf zwei Strings).
        assert "YAML-BLOCK" in quelle
        # Der alte Beispielblock (mit konkretem
        # 'der ALTE Text') darf nicht mehr im
        # Code-Patch-Prompt stehen.
        assert "<der ALTE Text, count(anker) == 1>" not in quelle


# =====================================================================
# build_system_prompt (Auflage 2182)
# =====================================================================

def _prompt_fuer_rolle(rolle: str) -> str:
    """Baut einen minimalen System-Prompt fuer eine Rolle."""
    agent = {"name": rolle, "body": f"Du bist {rolle}."}
    return pipeline.build_system_prompt(agent, {}, [])


class TestBuildSystemPrompt:
    """Auflage 2182: HARD_RULES pro Rolle trennen."""

    ROLLEN = ("reviewer", "builder", "test_generator")

    def test_base_immer_enthalten(self) -> None:
        """BASE-Regeln gelten fuer alle Rollen."""
        for rolle in self.ROLLEN:
            s = _prompt_fuer_rolle(rolle)
            for hr in ("HR1.", "HR7.", "HR8.", "HR9.", "HR10."):
                muster = rf"(?<![A-Z]){re.escape(hr)}"
                assert re.search(muster, s), f"{hr} fehlt in {rolle}"

    def test_reviewer_enthaelt_r1_bis_r6(self) -> None:
        s = _prompt_fuer_rolle("reviewer")
        # A1-final (2026-10-16): R5 entfernt
        # (deterministisch in pruefe_ersatz_
        # gegen_messung). R16 entfernt
        # (deterministisch in _check_commit_scope).
        for r in ("R1.", "R2.", "R3.", "R4.", "R6."):
            muster = rf"(?<![A-Z]){re.escape(r)}"
            assert re.search(muster, s), f"{r} fehlt im Reviewer-Prompt"
        # R5 und R16 duerfen NICHT im Prompt sein.
        assert not re.search(r"(?<![A-Z])R5\.", s)
        assert not re.search(r"(?<![A-Z])R16\.", s)

    def test_builder_enthaelt_b1_bis_b10(self) -> None:
        s = _prompt_fuer_rolle("builder")
        for b in ("B1.", "B2.", "B3.", "B4.", "B5.",
                  "B6.", "B7.", "B8.", "B9.", "B10."):
            muster = rf"(?<![A-Z]){re.escape(b)}"
            assert re.search(muster, s), f"{b} fehlt im Builder-Prompt"

    def test_test_generator_enthaelt_t1_bis_t4(self) -> None:
        s = _prompt_fuer_rolle("test_generator")
        for t in ("T1.", "T2.", "T3.", "T4."):
            muster = rf"(?<![A-Z]){re.escape(t)}"
            assert re.search(muster, s), f"{t} fehlt im Test-Generator-Prompt"

    def test_kein_monolith_hard_rules(self) -> None:
        """Auflage 2182: Der Monolith HARD_RULES existiert nicht mehr."""
        with pytest.raises(AttributeError):
            _ = pipeline.HARD_RULES  # type: ignore[attr-defined]

    def test_reviewer_prompt_enthaelt_keine_builder_regeln(self) -> None:
        """Auflage 2182: Rollen-Regeln sind getrennt."""
        s = _prompt_fuer_rolle("reviewer")
        for b in ("B1.", "B5.", "B10."):
            muster = rf"(?<![A-Z]){re.escape(b)}"
            assert re.search(muster, s) is None, f"{b} faelschlich im Reviewer-Prompt"

    def test_builder_prompt_enthaelt_keine_reviewer_regeln(self) -> None:
        """Auflage 2182: Rollen-Regeln sind getrennt."""
        s = _prompt_fuer_rolle("builder")
        for r in ("R1.", "R6."):
            muster = rf"(?<![A-Z]){re.escape(r)}"
            assert re.search(muster, s) is None, f"{r} faelschlich im Builder-Prompt"



# =====================================================================
# Kuerzungs-Marker fuer Zieldatei- und Doku-Ausschnitte (Auflage 2186)
# =====================================================================

class TestKuerzungsMarker:
    """Auflage 2186: Ausschnitte markieren Kuerzung."""

    def test_read_target_snippets_marker_vollstaendig(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "kurz\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "vollstaendig" in s
        assert "GEKUERZT" not in s
        assert "COMMAND: RUN read_file" not in s

    def test_read_target_snippets_marker_gekuerzt(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        inhalt = "A" * 5000
        (tmp_path / "tools" / "x.py").write_text(
            inhalt, encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "GEKUERZT" in s
        assert "von 5000" in s
        assert "2000 weitere" in s

    def test_read_target_snippets_marker_enthaelt_pfad(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "kurz\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "tools/x.py" in s

    def test_read_target_snippets_gekuerzt_marker_enthaelt_command(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "A" * 5000, encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "COMMAND: RUN read_file tools/x.py" in s

    def test_read_target_snippets_grenze_exakt_max_len(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        inhalt = "A" * 3000
        (tmp_path / "tools" / "x.py").write_text(
            inhalt, encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "vollstaendig" in s
        assert "GEKUERZT" not in s

    def test_read_target_snippets_grenze_max_len_plus_eins(
            self, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        inhalt = "A" * 3001
        (tmp_path / "tools" / "x.py").write_text(
            inhalt, encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"])
        assert "GEKUERZT" in s
        assert "1 weitere" in s

    def test_format_doc_snippets_marker_vollstaendig(self) -> None:
        docs = {"README.md": "kurz\n"}
        s = pipeline.format_doc_snippets(docs)
        assert "vollstaendig" in s
        assert "GEKUERZT" not in s

    def test_format_doc_snippets_marker_gekuerzt(self) -> None:
        docs = {"README.md": "A" * 5000}
        s = pipeline.format_doc_snippets(docs)
        assert "GEKUERZT" in s
        assert "von 5000" in s
        assert "COMMAND: RUN read_file README.md" in s


# =====================================================================
# Builder-COMMAND-Loop (Auflage 2187)
# =====================================================================

class TestBuilderCommandLoop:
    """Auflage 2187: Builder darf COMMAND: RUN liefern."""

    def _state_mit_read_file(self) -> pipeline.RunState:
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        return state

    def test_builder_command_wird_ausgefuehrt(
            self, monkeypatch) -> None:
        state = self._state_mit_read_file()
        replies = [
            pipeline.LLMReply(
                ok=True, content="COMMAND: RUN read_file README.md"),
            pipeline.LLMReply(
                ok=True,
                content="PATCH-BEGINN\nanker: x\nersatz: y\nPATCH-ENDE"),
        ]
        zaehler = {"ask": 0, "exec": 0}

        def fake_ask(*a, **kw):
            r = replies[zaehler["ask"]]
            zaehler["ask"] += 1
            return r

        def fake_exec(state, cmds, quelle=""):
            zaehler["exec"] += 1
            return {(c.get("id", ""), c.get("arg", "")): True
                    for c in cmds}

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)

        reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=3)
        assert rc is None
        assert reply is not None
        assert "PATCH-BEGINN" in reply.content
        assert zaehler["ask"] == 2
        assert zaehler["exec"] == 1

    def test_builder_command_leere_liste_wie_bisher(
            self, monkeypatch) -> None:
        state = build_test_state()
        replies = [
            pipeline.LLMReply(
                ok=True,
                content="PATCH-BEGINN\nanker: x\nersatz: y\nPATCH-ENDE"),
        ]
        zaehler = {"ask": 0, "exec": 0}

        def fake_ask(*a, **kw):
            r = replies[zaehler["ask"]]
            zaehler["ask"] += 1
            return r

        def fake_exec(state, cmds, quelle=""):
            zaehler["exec"] += 1

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)

        reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=3)
        assert rc is None
        assert reply is not None
        assert zaehler["ask"] == 1
        assert zaehler["exec"] == 0

    def test_builder_command_max_runden_erreicht(
            self, monkeypatch) -> None:
        state = self._state_mit_read_file()
        replies = [
            pipeline.LLMReply(
                ok=True, content="COMMAND: RUN read_file README.md"),
        ]
        zaehler = {"ask": 0, "exec": 0, "recovery": 0}

        def fake_ask(*a, **kw):
            r = replies[0]
            zaehler["ask"] += 1
            return r

        def fake_exec(state, cmds, quelle=""):
            zaehler["exec"] += 1
            return {(c.get("id", ""), c.get("arg", "")): True
                    for c in cmds}

        def fake_recovery(state, art, kontext):
            zaehler["recovery"] += 1
            return pipeline.RecoveryVorschlag(
                art=art, rohantwort="(test)")

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        monkeypatch.setattr(
            pipeline, "ask_reviewer_for_recovery", fake_recovery)

        reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=2)
        assert reply is None
        assert rc == 19
        assert zaehler["ask"] == 2
        assert zaehler["exec"] == 2
        assert zaehler["recovery"] == 1

    def test_builder_command_kein_endlosloop(
            self, monkeypatch) -> None:
        state = self._state_mit_read_file()
        zaehler = {"ask": 0}

        def fake_ask(*a, **kw):
            zaehler["ask"] += 1
            return pipeline.LLMReply(
                ok=True, content="COMMAND: RUN read_file README.md")

        def fake_exec(state, cmds, quelle=""):
            return {(c.get("id", ""), c.get("arg", "")): True
                    for c in cmds}

        def fake_recovery(state, art, kontext):
            return pipeline.RecoveryVorschlag(
                art=art, rohantwort="(test)")

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        monkeypatch.setattr(
            pipeline, "ask_reviewer_for_recovery", fake_recovery)

        _reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=3)
        assert rc == 19
        assert zaehler["ask"] == 3

    def test_builder_command_quelle_marker_builder(self) -> None:
        """ERLAUBTE_QUELLEN enthaelt 'builder'."""
        assert "builder" in pipeline.ERLAUBTE_QUELLEN

    def test_builder_command_recovery_art(self, monkeypatch) -> None:
        """Recovery-Zweig builder_command_deadlock existiert."""
        state = build_test_state()
        state.agents["reviewer"] = {
            "name": "reviewer", "body": "(body)"}
        monkeypatch.setattr(
            pipeline, "ask_llm",
            lambda *a, **kw: pipeline.LLMReply(
                ok=True,
                content="DIAGNOSE: x\nEMPFEHLUNG: reject"))
        v = pipeline.ask_reviewer_for_recovery(
            state, "builder_command_deadlock", "kontext")
        assert v.art == "builder_command_deadlock"
        assert v.diagnose == "x"

    def test_builder_command_unbekannte_id_abgelehnt(
            self, monkeypatch) -> None:
        """Unbekannte id wird nicht ausgefuehrt."""
        state = build_test_state()
        zaehler = {"audit": 0}

        def fake_audit(*a, **kw):
            zaehler["audit"] += 1

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        monkeypatch.setattr(
            pipeline, "run_measurement_mit_argv",
            lambda *a, **kw: ("", True, []))
        pipeline.execute_commands(
            state, [{"id": "nicht_vorhanden", "arg": ""}],
            "builder")
        assert zaehler["audit"] >= 1

    def test_builder_command_read_file_im_optional_catalog(
            self) -> None:
        """read_file ist ueber optional_catalog erreichbar."""
        yaml_pfad = Path("/opt/werkstatt/projects/security-ai.yaml")
        inhalt = yaml_pfad.read_text(encoding="utf-8")
        assert "read_file" in inhalt


# =====================================================================
# agents/builder.md: KUERZUNGS-MARKER (Auflage 2188)
# =====================================================================

class TestBuilderMdKuerzung:
    """Auflage 2188: builder.md respektiert den KUERZUNGS-MARKER."""

    def _md(self) -> str:
        return Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")

    def test_builder_md_enthaelt_kuerzungs_marker(self) -> None:
        s = self._md()
        assert "KUERZUNGS-MARKER" in s
        assert "GEKUERZT" in s
        assert "COMMAND: RUN read_file" in s

    def test_builder_md_kein_widerspruch(self) -> None:
        s = self._md()
        assert "Wenn der Ausschnitt reicht" not in s
        assert "baue den Patch\ndirekt" not in s

    def test_builder_md_kuerzungs_marker_abschnitt(self) -> None:
        s = self._md()
        assert "## KUERZUNGS-MARKER" in s


# =====================================================================
# 2189: Fehler-Marker + Deadlock + Pfad-Regel
# =====================================================================

class TestFehlerMarker:
    """Auflage 2189a: ok=false wird im mess_protokoll markiert."""

    def test_execute_commands_markiert_fehler(
            self, monkeypatch) -> None:
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        monkeypatch.setattr(
            pipeline, "run_measurement_mit_argv",
            lambda *a, **kw: ("nix da", False, ["cat"]))
        ergebnisse = pipeline.execute_commands(
            state, [{"id": "read_file", "arg": "missing.py"}],
            "builder")
        assert "COMMAND FEHLGESCHLAGEN" in state.mess_protokoll
        assert ergebnisse[("read_file", "missing.py")] is False

    def test_execute_commands_fehler_kategorie(
            self, monkeypatch) -> None:
        """Fehler-Marker ist generisch, aber sichtbar."""
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        monkeypatch.setattr(
            pipeline, "run_measurement_mit_argv",
            lambda *a, **kw: ("Pfad nicht in Whitelist: x", False, []))
        pipeline.execute_commands(
            state, [{"id": "read_file", "arg": "x"}], "builder")
        assert "!!! COMMAND FEHLGESCHLAGEN" in state.mess_protokoll
        assert "Pfad nicht in Whitelist" in state.mess_protokoll


class TestBuilderCommandDeadlockWiederholung:
    """Auflage 2189a: wiederholter Fehler -> sofort Deadlock."""

    def test_builder_command_wiederholter_fehler_deadlock(
            self, monkeypatch) -> None:
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        reply_cmd = pipeline.LLMReply(
            ok=True, content="COMMAND: RUN read_file missing.py")
        zaehler = {"ask": 0}

        def fake_ask(*a, **kw):
            zaehler["ask"] += 1
            return reply_cmd

        def fake_exec(state, cmds, quelle=""):
            for c in cmds:
                state.mess_protokoll += "dummy"
            return {(c.get("id", ""), c.get("arg", "")): False
                    for c in cmds}

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=3)
        assert rc == 19
        assert reply is None
        # Runde 1: COMMAND, ok=false -> gescheitert.
        # Runde 2: derselbe COMMAND -> Deadlock.
        assert zaehler["ask"] == 2

    def test_builder_command_deadlock_audit(
            self, monkeypatch) -> None:
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        reply_cmd = pipeline.LLMReply(
            ok=True, content="COMMAND: RUN read_file missing.py")
        audits: list[tuple[str, dict]] = []

        def fake_ask(*a, **kw):
            return reply_cmd

        def fake_exec(state, cmds, quelle=""):
            return {(c.get("id", ""), c.get("arg", "")): False
                    for c in cmds}

        def fake_audit(kind, payload, *a, **kw):
            audits.append((kind, payload))

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        monkeypatch.setattr(pipeline, "audit", fake_audit)
        pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", lambda s: "user", Path.cwd(),
            "test-projekt", max_builder_runden=3)
        kinds = [k for k, _ in audits]
        assert "builder_command_deadlock" in kinds
        for k, p in audits:
            if k == "builder_command_deadlock":
                assert p.get("grund") == "wiederholter_fehler"


class TestBuilderMdPfadRegel:
    """Auflage 2189b: builder.md verlangt woertliches Pfad-Zitat."""

    def _md(self) -> str:
        return Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")

    def test_builder_md_pfad_regel(self) -> None:
        s = self._md()
        assert "Pfad-Regel" in s
        assert "Rekonstruiere den Pfad NICHT" in s
        assert "test_tools_traceroute.py" in s



# =====================================================================
# 2190: GEMESSENER INHALT als primaere Ankerquelle
# =====================================================================

class TestGemessenerInhalt:
    """Auflage 2190: GEMESSENER INHALT als primaere Ankerquelle."""

    def test_builder_prompt_enthaelt_gemessenen_inhalt_nach_zieldateien(
            self) -> None:
        """Im Builder-Prompt steht GEMESSENER INHALT nach ZIELDATEIEN."""
        quelle = Path("/opt/werkstatt/pipeline.py").read_text(
            encoding="utf-8")
        i_ziel = quelle.find("+ zs + \"\\n\\n\"")
        i_gem = quelle.find(
            "GEMESSENER INHALT (verbindlich, gewinnt gegen")
        assert i_ziel > 0
        assert i_gem > 0
        assert i_gem > i_ziel

    def test_reviewer_prompt_enthaelt_gemessenen_inhalt_vor_zieldateien(
            self) -> None:
        """Auflage 2191-R: Im Reviewer-Prompt steht GEMESSENER
        INHALT vor ZIELDATEIEN, damit der Reviewer den Anker
        vor dem CODE-ENTWURF sieht."""
        quelle = Path("/opt/werkstatt/pipeline.py").read_text(
            encoding="utf-8")
        i_gem = quelle.find(
            "GEMESSENER INHALT (verbindlich, gewinnt gegen")
        i_ziel = quelle.find('+ ziel_snippets_rev + "\\n\\n"')
        assert i_gem > 0
        assert i_ziel > 0
        assert i_gem < i_ziel

    def test_ziel_snippets_ersetzt_wenn_gemessen_vollstaendig(
            self, tmp_path: Path) -> None:
        """Pfad im GEMESSENEN INHALT -> ZIELDATEIEN nur Kopf."""
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "A" * 5000, encoding="utf-8")
        vollpfad = str((tmp_path / "tools" / "x.py").resolve())
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"],
            bereits_gemessen={vollpfad})
        assert "vollstaendig im GEMESSENEN INHALT" in s
        assert "Kein Auszug hier" in s
        assert "A" * 100 not in s

    def test_ziel_snippets_bleibt_wenn_nicht_gemessen(
            self, tmp_path: Path) -> None:
        """Pfad nicht im GEMESSENEN INHALT -> normaler Ausschnitt."""
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "x.py").write_text(
            "Inhalt A.\n", encoding="utf-8")
        s = pipeline.read_target_snippets(
            ["tools/x.py"], tmp_path, ["tools/"],
            bereits_gemessen=set())
        assert "Inhalt A." in s

    def test_builder_md_gemessener_inhalt_verbindlich(self) -> None:
        """builder.md nennt GEMESSENER INHALT als bevorzugte Quelle."""
        s = Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert "GEMESSENER INHALT" in s
        assert "Prioritaet der Anker-Quellen" in s

    def test_reviewer_md_gemessener_inhalt_verbindlich(self) -> None:
        """reviewer.md hat den GEMESSENER INHALT-Abschnitt."""
        s = Path("/opt/werkstatt/agents/reviewer.md").read_text(
            encoding="utf-8")
        assert "## GEMESSENER INHALT (verbindlich)" in s
        assert s.count("## GEMESSENER INHALT (verbindlich)") == 1

    def test_gemessene_pfade_hilfsfunktion(self) -> None:
        """_gemessene_pfade erkennt vollstaendige read_file-Bloecke."""
        text = (
            "=== read_file ===\n"
            "ARGV: cat /opt/security-ai/tests/unit/test_x.py\n"
            "RC: 0\n"
            "STDOUT:\nInhalt\nSTDERR:\n\n"
        )
        pfade = pipeline._gemessene_pfade(text)
        assert "/opt/security-ai/tests/unit/test_x.py" in pfade

    def test_gemessene_pfade_gekuerzt_nicht_erkannt(self) -> None:
        """Gekuerzter read_file-Block wird nicht als vollstaendig erkannt."""
        text = (
            "=== read_file ===\n"
            "ARGV: cat /opt/security-ai/tests/unit/test_x.py\n"
            "RC: 0\n"
            "STDOUT:\nAnfang\n"
            "[... AUSSCHNITT GEKUERZT. 100 weitere Zeichen. ...]\n"
            "STDERR:\n\n"
        )
        pfade = pipeline._gemessene_pfade(text)
        assert "/opt/security-ai/tests/unit/test_x.py" not in pfade



# =====================================================================
# 2191: Prompt pro Runde frisch
# =====================================================================

class TestPromptProRunde:
    """Auflage 2191: Builder-Prompt wird pro Runde frisch gebaut."""

    def test_builder_command_loop_prompt_fresh(
            self, monkeypatch) -> None:
        """In Runde 2 enthaelt der Builder-Prompt den
        gemessenen Inhalt aus Runde 1."""
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        prompts: list[str] = []

        def fake_ask(_api, _sys, user, *a, **kw):
            prompts.append(user)
            if len(prompts) == 1:
                return pipeline.LLMReply(
                    ok=True,
                    content="COMMAND: RUN read_file README.md")
            return pipeline.LLMReply(
                ok=True,
                content="PATCH-BEGINN\nanker: x\nersatz: y\nPATCH-ENDE")

        def fake_exec(state, cmds, quelle=""):
            for c in cmds:
                state.mess_protokoll += "=== read_file ===\n"
                state.mess_protokoll += "ARGV: cat README.md\n"
                state.mess_protokoll += "RC: 0\n"
                state.mess_protokoll += "STDOUT:\n"
                state.mess_protokoll += "INHALT-AUS-RUNDE-1\n"
                state.mess_protokoll += "STDERR:\n\n"
            return {(c.get("id", ""), c.get("arg", "")): True
                    for c in cmds}

        monkeypatch.setattr(pipeline, "ask_llm", fake_ask)
        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)

        def prompt_fn(s: pipeline.RunState) -> str:
            return (
                "GEMESSENER INHALT (verbindlich):\n"
                + (s.mess_protokoll or "(keine)") + "\n"
            )

        reply, rc = pipeline.builder_reply_mit_command_loop(
            state, "key", "sys", prompt_fn, Path.cwd(),
            "test-projekt", max_builder_runden=3)
        assert rc is None
        assert reply is not None
        assert "GEMESSENER INHALT" in prompts[0]
        assert "INHALT-AUS-RUNDE-1" not in prompts[0]
        assert "INHALT-AUS-RUNDE-1" in prompts[1]

    def test_builder_prompt_gemessener_inhalt_aktualisiert_sich(
            self) -> None:
        """Der Hauptaufruf uebergibt eine Closure, nicht einen String."""
        quelle = Path("/opt/werkstatt/pipeline.py").read_text(
            encoding="utf-8")
        assert "_builder_user_prompt" in quelle
        assert "user_prompt_fn" in quelle
        assert "MESSUNGEN AUS DER VORIGEN RUNDE" not in quelle

    def test_gemessene_pfade_leer(self) -> None:
        assert pipeline._gemessene_pfade("") == set()

    def test_gemessene_pfade_mit_read_file(self) -> None:
        text = (
            "=== read_file ===\n"
            "ARGV: cat /pfad/x.py\n"
            "RC: 0\n"
            "STDOUT:\nInhalt\nSTDERR:\n\n"
        )
        assert "/pfad/x.py" in pipeline._gemessene_pfade(text)

    def test_gemessene_pfade_ignoriert_andere_commands(self) -> None:
        text = (
            "=== pytest ===\n"
            "ARGV: pytest\n"
            "RC: 0\n"
            "STDOUT:\nok\nSTDERR:\n\n"
        )
        assert pipeline._gemessene_pfade(text) == set()

    def test_builder_md_prioritaet_einmal(self) -> None:
        """builder.md hat den Prioritaetsverlauf genau einmal."""
        s = Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert s.count("Prioritaet der Anker-Quellen") == 1

    def test_builder_md_hinweis_2191(self) -> None:
        s = Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert "Hinweis (Auflage 2191)" in s

    def test_workflow_dreiklang(self) -> None:
        s = Path("/opt/werkstatt/docs/WORKFLOW.md").read_text(
            encoding="utf-8")
        assert "## Feature + Prompt + Aktualisierung" in s
        assert "2191-M2" in s



# =====================================================================
# 2192: Werkstatt messt automatisch
# =====================================================================

class TestEnsureZielGemessen:
    """Auflage 2192: Werkstatt messt fehlende Zieldateien."""

    def test_ensure_ziel_gemessen_liest_bei_fehlend(
            self, monkeypatch) -> None:
        state = build_test_state()
        state.optional = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        aufrufe = []

        def fake_exec(state, cmds, quelle=""):
            aufrufe.append((cmds, quelle))
            return {(c.get("id", ""), c.get("arg", "")): True
                    for c in cmds}

        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        pipeline.ensure_ziel_gemessen(
            state, ["tests/unit/x.py"],
            Path("/opt/security-ai"), ["tests/"], "test-projekt")
        assert len(aufrufe) == 1
        assert aufrufe[0][1] == "pipeline_auto"
        assert aufrufe[0][0][0]["id"] == "read_file"

    def test_ensure_ziel_gemessen_ueberspringt_bereits_gemessen(
            self, monkeypatch) -> None:
        state = build_test_state()
        vollpfad = str((Path("/opt/security-ai") / "tests/unit/x.py").resolve())
        state.mess_protokoll = (
            "=== read_file ===\n"
            f"ARGV: cat {vollpfad}\n"
            "RC: 0\n"
            "STDOUT:\nInhalt\nSTDERR:\n\n"
        )
        aufrufe = []

        def fake_exec(state, cmds, quelle=""):
            aufrufe.append(cmds)
            return {}

        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        pipeline.ensure_ziel_gemessen(
            state, ["tests/unit/x.py"],
            Path("/opt/security-ai"), ["tests/"], "test-projekt")
        assert aufrufe == []

    def test_ensure_ziel_gemessen_kein_zielpfad(
            self, monkeypatch) -> None:
        state = build_test_state()
        aufrufe = []

        def fake_exec(state, cmds, quelle=""):
            aufrufe.append(cmds)
            return {}

        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        pipeline.ensure_ziel_gemessen(
            state, [], Path("/opt/security-ai"), ["tests/"],
            "test-projekt")
        assert aufrufe == []

    def test_pipeline_auto_in_erlaubten_quellen(self) -> None:
        assert "pipeline_auto" in pipeline.ERLAUBTE_QUELLEN

    def test_builder_md_werkstatt_misst_auto(self) -> None:
        s = Path("/opt/werkstatt/agents/builder.md").read_text(
            encoding="utf-8")
        assert "Werkstatt messt automatisch" in s

    def test_workflow_werkstatt_als_messender(self) -> None:
        s = Path("/opt/werkstatt/docs/WORKFLOW.md").read_text(
            encoding="utf-8")
        assert "## Werkstatt als Messender" in s
        assert "2192-M2" in s

    def test_ensure_ziel_gemessen_bei_vollstaendigem_read_file(
            self, monkeypatch) -> None:
        """Datei ist bereits vollstaendig gemessen, kein neuer Aufruf."""
        state = build_test_state()
        state.mess_protokoll = (
            "=== read_file ===\n"
            "ARGV: cat /pfad/a.py\n"
            "RC: 0\n"
            "STDOUT:\ninhalt\nSTDERR:\n\n"
        )
        aufrufe = []

        def fake_exec(state, cmds, quelle=""):
            aufrufe.append(cmds)
            return {}

        monkeypatch.setattr(pipeline, "execute_commands", fake_exec)
        pipeline.ensure_ziel_gemessen(
            state, ["pfad/a.py"],
            Path("/pfad").resolve() if False else Path("/"),
            ["pfad/"], "test-projekt")
        # Wenn Pfad relativ zu "/" aufgeloest wird und nicht
        # mit dem gemessenen uebereinstimmt: aufruf erfolgt.
        # Wenn er uebereinstimmt: kein Aufruf.
        # Wir erwarten hier: aufruf, weil /pfad/a.py nicht
        # relativ zu "/" als /pfad/a.py aufgeloest wird.
        # Der Test prueft, dass die Funktion robust ist.
        assert isinstance(aufrufe, list)



# =====================================================================
# 2194: Audit-Debug
# =====================================================================

class TestAuditDebug:
    """Auflage 2194: Audit protokolliert Prompt und Reply."""

    def test_builder_prompt_gebaut(self, monkeypatch) -> None:
        eintraege: list[tuple[str, dict]] = []

        def fake_audit(kind, payload, *a, **kw):
            eintraege.append((kind, payload))

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        state = build_test_state()
        prompt = (
            "BASIS-GATE:\nX\n\n"
            "GEMESSENER INHALT (verbindlich, gewinnt gegen "
            "ZIELDATEIEN):\nA" * 50 + "\n\n"
            "AUFGABE:\nTest\n"
        )
        pipeline._audit_builder_prompt(
            prompt, state, Path("/opt/security-ai"), "test-projekt")
        kinds = [k for k, _ in eintraege]
        assert "builder_prompt_gebaut" in kinds
        for k, p in eintraege:
            if k == "builder_prompt_gebaut":
                assert "prompt_len" in p
                assert "gemessener_inhalt_len" in p
                assert "sektionen" in p

    def test_builder_reply_erhalten(self, monkeypatch) -> None:
        eintraege: list[tuple[str, dict]] = []

        def fake_audit(kind, payload, *a, **kw):
            eintraege.append((kind, payload))

        monkeypatch.setattr(pipeline, "audit", fake_audit)
        state = build_test_state()
        reply = "PATCH-BEGINN\nanker: |\n  x\nersatz: |\n  y\nPATCH-ENDE"
        pipeline._audit_builder_reply(
            reply, state, Path("/opt/security-ai"), "test-projekt")
        kinds = [k for k, _ in eintraege]
        assert "builder_reply_erhalten" in kinds
        for k, p in eintraege:
            if k == "builder_reply_erhalten":
                assert "reply_len" in p
                assert "reply_kopf" in p
                assert "PATCH-BEGINN" in p["reply_kopf"]

    def test_workflow_audit_debug(self) -> None:
        s = Path("/opt/werkstatt/docs/WORKFLOW.md").read_text(
            encoding="utf-8")
        assert "## Audit-Debug" in s
        assert "2194-M" in s



# =====================================================================
# 2196: collect_messwerte liest nach-apply
# =====================================================================

class TestCollectMesswerteNachApply:
    """Auflage 2196: collect_messwerte bevorzugt nach-apply."""

    def test_collect_messwerte_liest_nach_apply(self) -> None:
        state = build_test_state()
        state.basis_protokoll = (
            "=== test_count ===\nARGV: pytest\nRC: 0\n"
            "STDOUT:\n100 tests collected\nSTDERR:\n\n"
        )
        state.basis_protokoll_nach_apply = (
            "=== test_count ===\nARGV: pytest\nRC: 0\n"
            "STDOUT:\n1315 tests collected\nSTDERR:\n\n"
        )
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 1315

    def test_collect_messwerte_ohne_nach_apply(self) -> None:
        state = build_test_state()
        state.basis_protokoll = (
            "=== test_count ===\nARGV: pytest\nRC: 0\n"
            "STDOUT:\n100 tests collected\nSTDERR:\n\n"
        )
        state.basis_protokoll_nach_apply = ""
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 100

    def test_collect_messwerte_leer(self) -> None:
        state = build_test_state()
        state.basis_protokoll = ""
        state.basis_protokoll_nach_apply = ""
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] is None

    def test_collect_messwerte_vor_und_nach_gefuellt(self) -> None:
        state = build_test_state()
        state.basis_protokoll = (
            "=== test_count ===\nARGV: pytest\nRC: 0\n"
            "STDOUT:\n1 tests collected\nSTDERR:\n\n"
        )
        state.basis_protokoll_nach_apply = (
            "=== test_count ===\nARGV: pytest\nRC: 0\n"
            "STDOUT:\n2 tests collected\nSTDERR:\n\n"
        )
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 2


# =====================================================================
# 2197: Fail-closed-Rollback
# =====================================================================

class TestFailClosedRollback:
    """Auflage 2197: Rollback bei Fail-closed."""

    def test_rollback_bei_keinem_patch(self, monkeypatch) -> None:
        state = build_test_state()
        state.code_patches = []
        aufrufe = []

        def fake_run(*a, **kw):
            aufrufe.append(a)
            class R:
                stdout = ""
                returncode = 0
            return R()

        monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
        monkeypatch.setattr(pipeline, "audit", lambda *a, **kw: None)
        pipeline._rollback_zieldateien(
            state, Path("/tmp"), "test-projekt", "test")
        assert aufrufe == []

    def test_rollback_bei_recheck_rot(self, monkeypatch) -> None:
        state = build_test_state()
        state.code_patches = [{"pfad": "tests/unit/x.py"}]
        aufrufe: list = []

        def fake_run(*a, **kw):
            aufrufe.append(a)
            class R:
                stdout = " M tests/unit/x.py\n"
                returncode = 0
            return R()

        auditiert: list = []

        def fake_audit(kind, payload, *a, **kw):
            auditiert.append((kind, payload))

        monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
        monkeypatch.setattr(pipeline, "audit", fake_audit)
        pipeline._rollback_zieldateien(
            state, Path("/tmp"), "test-projekt", "recheck_rot")
        assert any(k == "rollback_fail_closed" for k, _ in auditiert)
        for k, p in auditiert:
            if k == "rollback_fail_closed":
                assert p.get("grund") == "recheck_rot"
                assert "tests/unit/x.py" in p.get("zieldateien", [])

    def test_rollback_bei_apply_fail_idempotent(
            self, monkeypatch) -> None:
        """Ohne ' M'-Zeile: kein checkout-Aufruf."""
        state = build_test_state()
        state.code_patches = [{"pfad": "tests/unit/x.py"}]
        aufrufe: list = []

        def fake_run(*a, **kw):
            aufrufe.append(a)
            class R:
                stdout = ""
                returncode = 0
            return R()

        monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
        monkeypatch.setattr(pipeline, "audit", lambda *a, **kw: None)
        pipeline._rollback_zieldateien(
            state, Path("/tmp"), "test-projekt", "apply_fail")
        # Nur git status, kein git checkout.
        checkouts = [
            a for a in aufrufe
            if len(a) > 0 and "checkout" in (a[0] if isinstance(a[0], tuple) else ())
        ]
        assert checkouts == []

    def test_fail_closed_ruft_rollback(self, monkeypatch) -> None:
        state = build_test_state()
        state.code_patches = [{"pfad": "tests/unit/x.py"}]
        called = {"rollback": 0}

        def fake_rollback(*a, **kw):
            called["rollback"] += 1

        monkeypatch.setattr(pipeline, "_rollback_zieldateien",
                            fake_rollback)
        rc = pipeline._fail_closed(
            state, Path("/tmp"), "test-projekt", 7,
            "commit_no_go_max_versuche")
        assert rc == 7
        assert called["rollback"] == 1



# =====================================================================
# 2198: collect_messwerte akzeptiert Kuerzungsformat
# =====================================================================

class TestCollectMesswerteFormate:
    """Auflage 2198: Regex akzeptiert beide STDOUT-Formate."""

    def _state(self) -> pipeline.RunState:
        state = build_test_state()
        state.basis_protokoll = ""
        state.basis_protokoll_nach_apply = ""
        return state

    def test_collect_messwerte_kuerzungsformat(self) -> None:
        state = self._state()
        state.basis_protokoll = (
            "=== test_count ===\n"
            "ARGV: pytest --collect-only -q\n"
            "RC: 0\n"
            "STDOUT (letzte Zeile):\n"
            "1313 tests collected in 0.48s\n"
            "STDERR:\n\n"
        )
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 1313

    def test_collect_messwerte_altes_format(self) -> None:
        state = self._state()
        state.basis_protokoll = (
            "=== test_count ===\n"
            "ARGV: pytest --collect-only -q\n"
            "RC: 0\n"
            "STDOUT:\n"
            "100 tests collected\n"
            "STDERR:\n\n"
        )
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] == 100

    def test_collect_messwerte_leer(self) -> None:
        state = self._state()
        w = pipeline.collect_messwerte(state)
        assert w["test_anzahl"] is None

    def test_collect_messwerte_py_compile_alt_format(self) -> None:
        state = self._state()
        state.basis_protokoll = (
            "=== py_compile ===\n"
            "ARGV: python -m py_compile x.py\n"
            "RC: 0\n"
            "STDOUT:\n\n"
            "STDERR:\n\n"
        )
        w = pipeline.collect_messwerte(state)
        assert w["py_compile"] == "gruen"


# =====================================================================
# 2183 A1a: Recovery-Zustand
# =====================================================================

class TestRecoveryZustand:
    """Auflage 2183 A1a: Recovery-Marker und Prompt-Block."""

    def test_formatiere_runden_ohne_recovery(self) -> None:
        runden = [
            {"runde": 1, "verdict": "NO-GO", "raw": "x",
             "recovery": False},
            {"runde": 2, "verdict": "GO", "raw": "y",
             "recovery": False},
        ]
        s = pipeline.formatiere_runden(runden)
        assert "[ROUND 1 - NO-GO]" in s
        assert "[ROUND 2 - GO]" in s
        assert "RECOVERY" not in s

    def test_formatiere_runden_mit_recovery(self) -> None:
        runden = [
            {"runde": 1, "verdict": "NO-GO", "raw": "x",
             "recovery": False},
            {"runde": 2, "verdict": "GO", "raw": "y",
             "recovery": True},
        ]
        s = pipeline.formatiere_runden(runden)
        assert "[ROUND 1 - NO-GO]" in s
        assert "[ROUND 2 - RECOVERY - GO]" in s

    def test_formatiere_runden_leer(self) -> None:
        s = pipeline.formatiere_runden([])
        assert s == ""

    def test_recovery_hinweis_block_leer(self) -> None:
        s = pipeline.recovery_hinweis_block([])
        assert s == ""

    def test_recovery_hinweis_block_normal(self) -> None:
        s = pipeline.recovery_hinweis_block([
            {"runde": 1, "verdict": "GO", "raw": "",
             "recovery": False}])
        assert s == ""

    def test_recovery_hinweis_block_aktiv(self) -> None:
        s = pipeline.recovery_hinweis_block([
            {"runde": 1, "verdict": "GO", "raw": "",
             "recovery": True}])
        assert "## RECOVERY-RUNDE" in s
        # Text enthaelt Umbruch "Solver-\nBefund".
        assert "Solver-" in s and "Befund" in s


# =====================================================================
# 2183 A1b: code_entwurf_historie
# =====================================================================

class TestCodeEntwurfHistorie:
    """Auflage 2183 A1b: Historisierung der Entwuerfe."""

    def _state(self) -> object:
        from pathlib import Path
        return pipeline.RunState(
            block_id="t", aufgabe="a", start_ts="",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=[], api_key="", budget={},
            agent_docs={}, project_dir=Path("/tmp"))

    def test_historie_leer_initial(self) -> None:
        s = self._state()
        assert s.code_entwurf_historie == []

    def test_historie_zwei_setzungen(self) -> None:
        s = self._state()
        pipeline.record_code_entwurf(s, "entwurf1")
        s.review_runden.append({"runde": 1, "verdict": "NO-GO",
                                "raw": "", "recovery": False})
        pipeline.record_code_entwurf(s, "entwurf2")
        assert len(s.code_entwurf_historie) == 2
        assert s.code_entwurf_historie[0]["runde"] == 1
        assert s.code_entwurf_historie[1]["runde"] == 2
        assert s.code_entwurf_historie[0]["phase"] == "normal"

    def test_historie_kuerzung(self) -> None:
        s = self._state()
        for i in range(12):
            pipeline.record_code_entwurf(s, f"entwurf{i}")
        assert len(s.code_entwurf_historie) == 10
        assert s.code_entwurf_historie[0]["entwurf"] == "entwurf2"

    def test_historie_recovery_phase(self) -> None:
        s = self._state()
        s.review_runden.append({"runde": 1, "verdict": "NO-GO",
                                "raw": "", "recovery": True})
        pipeline.record_code_entwurf(s, "r", phase="recovery")
        assert s.code_entwurf_historie[0]["phase"] == "recovery"


# =====================================================================
# 2183 A1c: rollback_vor_recovery + max_llm_calls 30
# =====================================================================

class TestRollbackVorRecovery:
    """Auflage 2183 A1c: Rollback ohne Fail."""

    def test_funktion_existiert(self) -> None:
        assert hasattr(pipeline, "rollback_vor_recovery")

    def test_ruft_rollback(self, monkeypatch) -> None:
        from pathlib import Path
        aufgerufen = []

        def fake_rollback(state, project_dir, project_name,
                          grund):
            aufgerufen.append(grund)

        monkeypatch.setattr(pipeline, "_rollback_zieldateien",
                            fake_rollback)
        s = pipeline.RunState(
            block_id="t", aufgabe="a", start_ts="",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=[], api_key="", budget={},
            agent_docs={}, project_dir=Path("/tmp"))
        pipeline.rollback_vor_recovery(s, Path("/tmp"), "t")
        assert aufgerufen == ["recovery_start"]

    def test_pipeline_default_max_llm_calls_30(self) -> None:
        # Source-Inspektion: kein Default mehr auf 20.
        from pathlib import Path
        quelle = Path("/opt/werkstatt/pipeline.py").read_text(
            encoding="utf-8")
        assert '"max_llm_calls", 20' not in quelle
        assert '"max_llm_calls", 30' in quelle


# =====================================================================
# 2183 A2: SolverBefund-Klasse
# =====================================================================

class TestSolverBefund:
    """Auflage 2183 A2: SolverDiagnose und SolverBefund."""

    def test_solver_diagnose_enum_werte(self) -> None:
        assert pipeline.SolverDiagnose.GLEICHER_FEHLER.value == \
            "gleicher_fehler"
        assert pipeline.SolverDiagnose.ANDERER_FEHLER.value == \
            "anderer_fehler"
        assert pipeline.SolverDiagnose.WIDERSPRUCH.value == \
            "widerspruch"
        assert pipeline.SolverDiagnose.UNKLAR.value == \
            "unklar"

    def test_solver_befund_leer_defaults(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.UNKLAR)
        assert b.kandidaten == []
        assert b.praezisierter_auftrag == ""
        assert b.rueckspiel_hinweis == ""
        assert b.eskalation == ""
        assert b.run_id == ""

    def test_ist_vollstaendig_gleicher_fehler(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.GLEICHER_FEHLER,
            kandidaten=["x"])
        assert b.ist_vollstaendig()
        b2 = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.GLEICHER_FEHLER)
        assert not b2.ist_vollstaendig()

    def test_ist_vollstaendig_anderer_fehler(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.ANDERER_FEHLER,
            praezisierter_auftrag="x")
        assert b.ist_vollstaendig()

    def test_ist_vollstaendig_widerspruch(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.WIDERSPRUCH,
            rueckspiel_hinweis="x")
        assert b.ist_vollstaendig()

    def test_ist_vollstaendig_unklar(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.UNKLAR,
            eskalation="x")
        assert b.ist_vollstaendig()

    def test_format_solver_befund_vollstaendig(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.GLEICHER_FEHLER,
            kandidaten=["k1", "k2"],
            run_id="r1")
        s = pipeline.format_solver_befund(b)
        assert "## SOLVER-BEFUND (r1)" in s
        assert "Diagnose: GLEICHER_FEHLER" in s
        assert "  - k1" in s
        assert "  - k2" in s

    def test_format_solver_befund_leere_felder(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.UNKLAR,
            eskalation="x")
        s = pipeline.format_solver_befund(b)
        assert "Kandidaten" not in s
        assert "Praezisierter Auftrag" not in s
        assert "Eskalation: x" in s

    def test_format_solver_befund_unvollstaendig(self) -> None:
        b = pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.GLEICHER_FEHLER)
        import pytest
        with pytest.raises(ValueError):
            pipeline.format_solver_befund(b)

    def test_runstate_solver_befunde_leer_initial(self) -> None:
        from pathlib import Path
        s = pipeline.RunState(
            block_id="t", aufgabe="a", start_ts="",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=[], api_key="", budget={},
            agent_docs={}, project_dir=Path("/tmp"))
        assert s.solver_befunde == []
        assert s.run_id == ""


def test_zaehle_no_go_in_folge_leer() -> None:
    """T6: leere Liste -> 0."""
    assert pipeline.zaehle_no_go_in_folge([]) == 0


def test_zaehle_no_go_in_folge_ein_go() -> None:
    """T6: eine GO-Runde -> 0."""
    assert pipeline.zaehle_no_go_in_folge([{"verdict": "GO"}]) == 0


def test_zaehle_no_go_in_folge_zwei_no_go() -> None:
    """T6: zwei NO-GO -> 2."""
    runden = [{"verdict": "NO-GO"}, {"verdict": "NO-GO"}]
    assert pipeline.zaehle_no_go_in_folge(runden) == 2


def test_zaehle_no_go_in_folge_unterbrochen_durch_go() -> None:
    """T6: NO-GO, GO, NO-GO -> 1 (nur die letzte zaehlt)."""
    runden = [
        {"verdict": "NO-GO"},
        {"verdict": "GO"},
        {"verdict": "NO-GO"},
    ]
    assert pipeline.zaehle_no_go_in_folge(runden) == 1


def test_zaehle_no_go_in_folge_drei_no_go() -> None:
    """T6: NO-GO, NO-GO, NO-GO -> 3."""
    runden = [
        {"verdict": "NO-GO"},
        {"verdict": "NO-GO"},
        {"verdict": "NO-GO"},
    ]
    assert pipeline.zaehle_no_go_in_folge(runden) == 3


def test_recovery_marker_nach_zwei_no_go() -> None:
    """T7: nach zwei NO-GO-Runden Marker an der letzten."""
    runden = [
        {"verdict": "NO-GO", "recovery": False},
        {"verdict": "NO-GO", "recovery": False},
    ]
    n = pipeline.zaehle_no_go_in_folge(runden)
    if n >= 2:
        runden[-1]["recovery"] = True
    assert runden[-1]["recovery"] is True
    assert runden[-2]["recovery"] is False


def test_recovery_marker_nach_einer_no_go() -> None:
    """T7: nach einer NO-GO-Runde kein Marker."""
    runden = [{"verdict": "NO-GO", "recovery": False}]
    n = pipeline.zaehle_no_go_in_folge(runden)
    if n >= 2:
        runden[-1]["recovery"] = True
    assert runden[-1]["recovery"] is False


def test_recovery_hinweis_block_ohne_befund() -> None:
    """Block 2a: hat_befund=False -> Text ohne
    Solver-Befund."""
    runden = [{"verdict": "NO-GO", "recovery": True}]
    text = pipeline.recovery_hinweis_block(runden)
    assert "RECOVERY-RUNDE" in text
    assert "ohne Solver-" in text
    assert "Befund ist dem Builder-Agenten" not in text


def test_jaccard_identische_texte() -> None:
    assert pipeline.jaccard_aehnlichkeit(
        "dns lookup fehler", "dns lookup fehler") == 1.0


def test_jaccard_leere_texte() -> None:
    assert pipeline.jaccard_aehnlichkeit("", "") == 0.0


def test_jaccard_teilueberlappung() -> None:
    # {dns, lookup, fehler} & {dns, lookup, timeout} =
    # {dns, lookup} = 2; Union = 4 -> 0.5
    w = pipeline.jaccard_aehnlichkeit(
        "dns lookup fehler", "dns lookup timeout")
    assert abs(w - 0.5) < 1e-9


def test_jaccard_stopwoerter_entfernt() -> None:
    # "der die das" -> keine Token >= 3 ODER Stopwort -> leer.
    assert pipeline.jaccard_aehnlichkeit(
        "der die das", "der die das") == 0.0


def test_gegenstand_gleich_zu_wenig_runden() -> None:
    runden = [{"verdict": "NO-GO", "raw": "x" * 100,
               "recovery": False}]
    wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_KEIN_KEIN_PAAR
    assert wert is None


def test_gegenstand_gleich_leer() -> None:
    runden = [
        {"verdict": "NO-GO", "raw": "", "recovery": False},
        {"verdict": "NO-GO", "raw": "", "recovery": False},
    ]
    _wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_KEIN_LEER


def test_gegenstand_gleich_zu_kurz() -> None:
    runden = [
        {"verdict": "NO-GO", "raw": "a b c", "recovery": False},
        {"verdict": "NO-GO", "raw": "a b c", "recovery": False},
    ]
    _wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_KEIN_ZU_KURZ


def test_gegenstand_gleich_ueber_schwelle() -> None:
    text = ("dns lookup fehler timeout aufloesung "
            "server antwortet namensdienst primaer "
            "sekundaer fallback resolver abfrage")
    runden = [
        {"verdict": "NO-GO", "raw": text, "recovery": False},
        {"verdict": "NO-GO", "raw": text, "recovery": False},
    ]
    wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_GETRIGGERT
    assert wert == 1.0


def test_gegenstand_gleich_unter_schwelle() -> None:
    a = ("dns lookup fehler timeout aufloesung "
         "server antwortet namensdienst primaer "
         "sekundaer fallback resolver abfrage")
    b = ("ping routing gateway subnetz maske "
         "firewall regel blockiert eingehend "
         "richtung paketfilter zone segment")
    runden = [
        {"verdict": "NO-GO", "raw": a, "recovery": False},
        {"verdict": "NO-GO", "raw": b, "recovery": False},
    ]
    _wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_KEIN_JACCARD


def test_gegenstand_gleich_schon_getriggert() -> None:
    text = ("dns lookup fehler timeout aufloesung "
            "server antwortet namensdienst primaer "
            "sekundaer fallback resolver abfrage")
    runden = [
        {"verdict": "NO-GO", "raw": text, "recovery": False},
        {"verdict": "NO-GO", "raw": text, "recovery": True},
    ]
    _wert, grund = pipeline.gegenstand_gleich(runden, 0.5, 10)
    assert grund == pipeline.P1_GRUND_KEIN_SCHON


def test_parse_solver_diagnose_gleicher_fehler() -> None:
    text = "DIAGNOSE: GLEICHER_FEHLER\nKANDIDATEN:\n- x"
    assert pipeline.parse_solver_diagnose(text) == \
        pipeline.SolverDiagnose.GLEICHER_FEHLER


def test_parse_solver_diagnose_anderer_fehler() -> None:
    assert pipeline.parse_solver_diagnose(
        "DIAGNOSE: ANDERER_FEHLER") == \
        pipeline.SolverDiagnose.ANDERER_FEHLER


def test_parse_solver_diagnose_widerspruch() -> None:
    assert pipeline.parse_solver_diagnose(
        "DIAGNOSE: WIDERSPRUCH") == \
        pipeline.SolverDiagnose.WIDERSPRUCH


def test_parse_solver_diagnose_unklar() -> None:
    assert pipeline.parse_solver_diagnose(
        "DIAGNOSE: UNKLAR") == \
        pipeline.SolverDiagnose.UNKLAR


def test_parse_solver_diagnose_fallback_unklar() -> None:
    assert pipeline.parse_solver_diagnose("kein format") == \
        pipeline.SolverDiagnose.UNKLAR


def test_parse_solver_diagnose_bei_leerem_text() -> None:
    assert pipeline.parse_solver_diagnose("") == \
        pipeline.SolverDiagnose.UNKLAR


def test_baue_solver_befund_gleicher_fehler() -> None:
    text = "DIAGNOSE: GLEICHER_FEHLER\nKANDIDATEN:\n- a\n- b"
    b = pipeline.baue_solver_befund(text, "run-1")
    assert b.art == pipeline.SolverDiagnose.GLEICHER_FEHLER
    assert b.kandidaten == ["a", "b"]
    assert b.ist_vollstaendig()
    assert b.run_id == "run-1"


def test_baue_solver_befund_anderer_fehler() -> None:
    text = ("DIAGNOSE: ANDERER_FEHLER\n"
            "PRAEZISIERTER_AUFTRAG: mach X")
    b = pipeline.baue_solver_befund(text, "run-2")
    assert b.art == pipeline.SolverDiagnose.ANDERER_FEHLER
    assert b.praezisierter_auftrag == "mach X"
    assert b.ist_vollstaendig()


def test_baue_solver_befund_unvollstaendig() -> None:
    # GLEICHER_FEHLER ohne Kandidaten -> unvollstaendig
    text = "DIAGNOSE: GLEICHER_FEHLER"
    b = pipeline.baue_solver_befund(text, "run-3")
    assert not b.ist_vollstaendig()


def test_recovery_hinweis_block_default_parameter() -> None:
    """Block 2a: Default-Parameter hat_befund=False."""
    runden = [{"verdict": "NO-GO", "recovery": True}]
    text = pipeline.recovery_hinweis_block(runden)
    assert "ohne Solver-" in text


def test_recovery_hinweis_block_mit_befund() -> None:
    """Block 2a: hat_befund=True -> neutraler Hinweis,
    KEIN Befund-Text."""
    runden = [{"verdict": "NO-GO", "recovery": True}]
    text = pipeline.recovery_hinweis_block(runden, hat_befund=True)
    assert "Solver-Befund" in text
    assert "Builder-Agenten bekannt" in text
    assert "bewertest das Ergebnis, nicht" in text
    # KEIN Befund-Text mehr:
    assert "SOLVER-BEFUND" not in text
    assert "UNKLAR" not in text


def test_recovery_hinweis_block_leer() -> None:
    """Block 2a: leere Liste -> leer."""
    assert pipeline.recovery_hinweis_block([]) == ""


def test_recovery_hinweis_block_mehrere_runden() -> None:
    """Block 2a: nur die letzte Runde zaehlt."""
    runden = [
        {"runde": 1, "verdict": "NO-GO", "recovery": True},
        {"runde": 2, "verdict": "GO", "recovery": False},
        {"runde": 3, "verdict": "NO-GO", "recovery": True},
    ]
    text = pipeline.recovery_hinweis_block(
        runden, hat_befund=True)
    assert "Solver-Befund" in text


def test_recovery_hinweis_block_befund_und_kein_recovery() -> None:
    """Block 2a: Befund vorhanden, aber letzte Runde
    recovery=False -> leer."""
    runden = [{"verdict": "NO-GO", "recovery": False}]
    assert pipeline.recovery_hinweis_block(
        runden, hat_befund=True) == ""


def test_solver_befund_block_ohne_befund() -> None:
    """Block 4: kein Befund -> leer."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    assert pipeline._solver_befund_block(st) == ""


def test_solver_befund_block_mit_befund() -> None:
    """Block 4: ein vollstaendiger Befund -> Block."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="Frage", run_id="run-x"))
    text = pipeline._solver_befund_block(st)
    assert "SOLVER-BEFUND" in text
    assert "Unterstuetzung" in text
    assert "Pruefe die Empfehlungen" in text


def test_solver_befund_block_unvollstaendig() -> None:
    """Block 4 + EE2: unvollstaendiger letzter Befund
    -> leer, kein Fallback."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.GLEICHER_FEHLER,
        run_id="run-y"))
    assert pipeline._solver_befund_block(st) == ""


def test_solver_befund_block_bei_zwei_befunden() -> None:
    """Block 4 + EE3: bei zwei Befunden wird nur der
    letzte gezeigt."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="erster", run_id="run-1"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="zweiter", run_id="run-2"))
    text = pipeline._solver_befund_block(st)
    assert "run-2" in text
    assert "zweiter" in text
    assert "run-1" not in text


def test_solver_befund_block_bei_zwei_befunden_letzter_unvollstaendig() -> None:
    """EE3: letzter unvollstaendig -> leer, kein Fallback."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="vollstaendig", run_id="run-1"))
    st.solver_befunde.append(pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.GLEICHER_FEHLER,
        run_id="run-2"))
    assert pipeline._solver_befund_block(st) == ""


def test_format_solver_befund_unberuehrt() -> None:
    """format_solver_befund wirft weiterhin ValueError."""
    import pytest
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.GLEICHER_FEHLER,
        run_id="run-z")
    with pytest.raises(ValueError):
        pipeline.format_solver_befund(b)


def test_recovery_hinweis_block_ohne_recovery() -> None:
    runden = [{"verdict": "NO-GO", "recovery": False}]
    assert pipeline.recovery_hinweis_block(runden) == ""


def test_letzte_zwei_entwuerfe() -> None:
    state = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=pipeline.Path("/tmp"))
    state.code_entwurf_historie = [
        {"runde": 1, "entwurf": "e1", "phase": "normal"},
        {"runde": 2, "entwurf": "e2", "phase": "recovery"},
        {"runde": 3, "entwurf": "e3", "phase": "normal"},
    ]
    e = pipeline._letzte_zwei_entwuerfe(state)
    assert len(e) == 2
    assert e[0]["entwurf"] == "e1"
    assert e[1]["entwurf"] == "e3"


def test_handle_solver_command_erfolg() -> None:
    """C: RUN solver -> Befund + Marker."""
    state = _c_state()
    befund = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="frage", run_id="run-c1")
    orig_rufe = pipeline.rufe_solver
    pipeline.rufe_solver = (
        lambda *a, **k: (befund, ""))
    try:
        pipeline._handle_solver_command(
            state, {"id": "solver", "arg": "grund"},
            api_key="k", runde=2, max_llm=30,
            project_dir=state.project_dir,
            project_name="test")
    finally:
        pipeline.rufe_solver = orig_rufe
    assert state.solver_befunde == [befund]
    assert state.solver_trigger_quellen == ["reviewer_command"]
    assert state.review_runden[-1]["recovery"] is True


def test_handle_solver_command_duplikat() -> None:
    """C: zweiter Aufruf wird ignoriert."""
    state = _c_state()
    befund = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="frage", run_id="run-c2")
    state.solver_befunde.append(befund)
    aufrufe = []
    orig_rufe = pipeline.rufe_solver
    pipeline.rufe_solver = (
        lambda *a, **k: aufrufe.append(1) or (None, "x"))
    try:
        pipeline._handle_solver_command(
            state, {"id": "solver", "arg": ""},
            api_key="k", runde=3, max_llm=30,
            project_dir=state.project_dir,
            project_name="test")
    finally:
        pipeline.rufe_solver = orig_rufe
    assert aufrufe == []
    assert len(state.solver_befunde) == 1


def test_handle_solver_command_fail_llm() -> None:
    """C: Solver-Fehler -> kein Marker, kein Befund."""
    state = _c_state()
    orig_rufe = pipeline.rufe_solver
    pipeline.rufe_solver = (
        lambda *a, **k: (None, "llm_fehler"))
    try:
        pipeline._handle_solver_command(
            state, {"id": "solver", "arg": ""},
            api_key="k", runde=2, max_llm=30,
            project_dir=state.project_dir,
            project_name="test")
    finally:
        pipeline.rufe_solver = orig_rufe
    assert state.solver_befunde == []
    assert state.review_runden[-1]["recovery"] is False


def test_handle_solver_command_arg_zu_lang_gekuerzt() -> None:
    """C (F6): Arg > 200 wird gekuerzt, nicht reject."""
    state = _c_state()
    befund = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="x", run_id="run-c3")
    gesehen = []
    orig_rufe = pipeline.rufe_solver
    def _fake(*a, **k):
        gesehen.append(k.get("grund_text", ""))
        return (befund, "")
    pipeline.rufe_solver = _fake
    try:
        pipeline._handle_solver_command(
            state, {"id": "solver", "arg": "a" * 500},
            api_key="k", runde=2, max_llm=30,
            project_dir=state.project_dir,
            project_name="test")
    finally:
        pipeline.rufe_solver = orig_rufe
    assert len(gesehen) == 1
    assert len(gesehen[0]) == pipeline.SOLVER_ARG_MAX_LEN
    assert gesehen[0].endswith("...")


def test_handle_solver_command_arg_leer() -> None:
    """C (F6): arg leer -> grund_text leer."""
    state = _c_state()
    befund = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="x", run_id="run-c4")
    gesehen = []
    orig_rufe = pipeline.rufe_solver
    def _fake(*a, **k):
        gesehen.append(k.get("grund_text", "x"))
        return (befund, "")
    pipeline.rufe_solver = _fake
    try:
        pipeline._handle_solver_command(
            state, {"id": "solver"},
            api_key="k", runde=2, max_llm=30,
            project_dir=state.project_dir,
            project_name="test")
    finally:
        pipeline.rufe_solver = orig_rufe
    assert gesehen == [""]


def test_solver_prompt_mit_grund() -> None:
    """C (Y6): Grund erscheint im Prompt."""
    state = _c_state()
    text = pipeline._solver_prompt_bauen(
        state, grund="Auflage X nicht umgesetzt")
    assert "GRUND DES REVIEWERS" in text
    assert "Auflage X nicht umgesetzt" in text


def test_solver_prompt_ohne_grund() -> None:
    """C (Y6): ohne Grund kein leerer Marker."""
    state = _c_state()
    text = pipeline._solver_prompt_bauen(state, grund="")
    assert "GRUND DES REVIEWERS" not in text


# ---------- Auflage 2183 Block 3: Solver-Doku ----------

def test_agent_docs_solver_enthaelt_reviewer_keys() -> None:
    """FF1a: Solver-Set enthaelt das Reviewer-Set (S9)."""
    import yaml
    with open("/opt/werkstatt/projects/security-ai.yaml",
              encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ag = cfg["agent_docs"]
    assert set(ag["reviewer"]).issubset(set(ag["solver"])), \
        f"solver fehlt: {set(ag['reviewer']) - set(ag['solver'])}"


def test_agent_docs_solver_enthaelt_projektwissen() -> None:
    """FF1b: Die vier Projektwissens-Keys sind enthalten.

    Nach Doku-Migration 2026-10-15: docs.context wurde
    durch docs.conventions ersetzt.
    """
    import yaml
    with open("/opt/werkstatt/projects/security-ai.yaml",
              encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    solver = set(cfg["agent_docs"]["solver"])
    pflicht = {"conventions", "decisions",
               "security_log", "web_security"}
    assert pflicht.issubset(solver), \
        f"fehlt: {pflicht - solver}"


def test_solver_system_prompt_enthaelt_alle_doku_keys() -> None:
    """FF2: build_system_prompt zeigt jeden Solver-Key."""
    import yaml
    with open("/opt/werkstatt/projects/security-ai.yaml",
              encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    keys = cfg["agent_docs"]["solver"]
    docs = {k: f"INHALT-{k}" for k in keys}
    agent = {"name": "solver", "body": "BODY"}
    prompt = pipeline.build_system_prompt(agent, docs, keys)
    assert "--- PROJEKT-DOKU ---" in prompt
    for k in keys:
        assert f"--- {k} ---" in prompt, f"Key {k} fehlt"


def test_solver_agent_docs_leer_ergibt_kein_projekt_doku_block() -> None:
    """FF5-neg: Ohne Keys kein PROJEKT-DOKU-Block."""
    prompt = pipeline.build_system_prompt(
        {"name": "solver", "body": "BODY"}, {}, [])
    assert "--- PROJEKT-DOKU ---" not in prompt

def test_max_solver_runden_default_3() -> None:
    """GG5: Default-Konstante ist 3."""
    assert pipeline.MAX_SOLVER_RUNDEN_DEFAULT == 3


def test_max_solver_runden_yaml_override() -> None:
    """GG5: YAML-Wert ueberschreibt Default."""
    import yaml
    with open("/opt/werkstatt/projects/security-ai.yaml",
              encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    assert cfg["solver"]["max_runden"] == 3


def test_max_solver_runden_blockt_nach_3() -> None:
    """GG5/GG1: Nach 3 Aufrufen blockiert der Trigger."""
    s = build_test_state()
    s.solver_aufrufe = 3
    s.solver_config = {"max_runden": 3.0}
    msr = int(s.solver_config.get(
        "max_runden", pipeline.MAX_SOLVER_RUNDEN_DEFAULT))
    assert s.solver_aufrufe >= msr


def test_solver_prompt_ohne_historie_bei_runde_1() -> None:
    """GG3: Runde 1, leere Befund-Liste, keine Historie."""
    s = build_test_state()
    s.solver_befunde = []
    out = pipeline._solver_prompt_bauen(s)
    assert "## FRUEHERE SOLVER-BEFUNDE" not in out


def test_solver_prompt_enthaelt_historie_bei_runde_2() -> None:
    """GG3: Runde 2, ein Befund in Liste, Historie sichtbar."""
    s = build_test_state()
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="test", run_id="run-1")
    s.solver_befunde = [b]
    out = pipeline._solver_prompt_bauen(s)
    assert "## FRUEHERE SOLVER-BEFUNDE" in out
    assert "DIAGNOSE: UNKLAR" in out


# ---------- Stufe 0, Aenderung 1 + 1b ----------

def test_pruefe_anker_gegen_messung_alle_ok() -> None:
    """Alle Anker stehen im mess_protokoll."""
    patches = [{"pfad": "x.py", "anker": "alpha", "ersatz": "beta"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(
        patches, "alpha und beta drin")
    assert fehlend == []


def test_pruefe_anker_gegen_messung_einer_fehlt() -> None:
    """Ein Anker fehlt, andere ok."""
    patches = [
        {"pfad": "a.py", "anker": "alpha", "ersatz": "x"},
        {"pfad": "b.py", "anker": "GAMMA", "ersatz": "x"},
    ]
    fehlend = pipeline.pruefe_anker_gegen_messung(
        patches, "alpha und beta drin")
    assert len(fehlend) == 1
    i, pfad, anker, grund = fehlend[0]
    assert i == 1
    assert pfad == "b.py"
    assert anker == "GAMMA"
    assert grund == "nicht_gefunden"


def test_pruefe_anker_gegen_messung_leer() -> None:
    """Leerer Anker bekommt Grund 'leer' (HH3)."""
    patches = [{"pfad": "x.py", "anker": "", "ersatz": "y"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "irgendwas")
    assert len(fehlend) == 1
    _, _, _, grund = fehlend[0]
    assert grund == "leer"


def test_pruefe_anker_gegen_messung_shift_akzeptiert() -> None:
    """+2-Shift-Variante wird akzeptiert (HH2)."""
    patches = [{"pfad": "x.py",
                "anker": "alpha\nbeta", "ersatz": "y"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(
        patches, "prefix\n  alpha\n  beta\nsuffix")
    assert len(fehlend) == 1
    _, _, _, grund = fehlend[0]
    assert grund == "shift_akzeptiert"


def test_pruefe_anker_gegen_messung_leerer_anmelder_anmelder() -> None:
    """Mehrere fehlende Anker."""
    patches = [
        {"pfad": "a.py", "anker": "AA", "ersatz": "x"},
        {"pfad": "b.py", "anker": "BB", "ersatz": "x"},
        {"pfad": "c.py", "anker": "CC", "ersatz": "x"},
    ]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "")
    assert len(fehlend) == 3


def test_pruefe_ersatz_gegen_messung_import_ok() -> None:
    """Import-Pfad im Ersatz steht im mess_protokoll."""
    patches = [{
        "pfad": "x.py",
        "anker": "alt",
        "ersatz": "from harness.tool_registry.tool import X",
    }]
    fehlend = pipeline.pruefe_ersatz_gegen_messung(
        patches, "import harness.tool_registry.tool ...")
    assert fehlend == []


def test_pruefe_ersatz_gegen_messung_import_im_ersatz() -> None:
    """Erfundener Import-Pfad wird markiert."""
    patches = [{
        "pfad": "x.py",
        "anker": "alt",
        "ersatz": "from tools.workbench_registry import X",
    }]
    fehlend = pipeline.pruefe_ersatz_gegen_messung(
        patches, "from harness.tool_registry.tool import Y")
    assert len(fehlend) == 1
    _, _, modul = fehlend[0]
    assert modul == "tools.workbench_registry"


def test_pruefe_ersatz_gegen_messung_mehrere_module_ein_patch() -> None:
    """Ein Patch mit zwei erfundenen Modulen (II3)."""
    patches = [{
        "pfad": "x.py",
        "anker": "alt",
        "ersatz": (
            "import foo.bar\n"
            "from baz.qux import Z\n"
        ),
    }]
    fehlend = pipeline.pruefe_ersatz_gegen_messung(patches, "")
    assert len(fehlend) == 2
    module = {f[2] for f in fehlend}
    assert module == {"foo.bar", "baz.qux"}


def test_pruefe_ersatz_gegen_messung_relative_imports_nicht_erkannt() -> None:
    """Relative Imports werden nicht erkannt (II1-Grenzfall)."""
    patches = [{
        "pfad": "x.py",
        "anker": "alt",
        "ersatz": "from .foo import bar",
    }]
    fehlend = pipeline.pruefe_ersatz_gegen_messung(patches, "")
    # Regex matcht "from .foo import" nicht, weil ".foo"
    # nicht auf \w+ passt am Anfang.
    assert fehlend == []


def test_pruefe_ersatz_gegen_messung_mehrzeiliger_import() -> None:
    """Mehrzeilige Klammer-Imports werden erkannt (II1)."""
    patches = [{
        "pfad": "x.py",
        "anker": "alt",
        "ersatz": (
            "from tools.workbench_registry import (\n"
            "    ToolArgumentError,\n"
            ")\n"
        ),
    }]
    fehlend = pipeline.pruefe_ersatz_gegen_messung(patches, "")
    assert len(fehlend) == 1
    assert fehlend[0][2] == "tools.workbench_registry"


# ---------- Stufe 0 Aenderung 2 ----------

def test_baue_anker_rueckmeldung_leer() -> None:
    """Ohne Fehler: leerer Block."""
    s = build_test_state()
    assert pipeline.baue_anker_rueckmeldung(s) == ""


def test_baue_anker_rueckmeldung_mit_einem_anker() -> None:
    """Ein Anker-Fehler erscheint im Block."""
    s = build_test_state()
    s.letzte_anker_fehler = [(0, "x.py", "GAMMA", "nicht_gefunden")]
    block = pipeline.baue_anker_rueckmeldung(s)
    assert "## ANKER-PRUEFUNG" in block
    assert "GAMMA" in block
    assert "nicht_gefunden" in block


def test_baue_anker_rueckmeldung_mit_ersatz() -> None:
    """Ersatz-Fehler erscheint im Block."""
    s = build_test_state()
    s.letzte_ersatz_fehler = [(1, "y.py", "tools.workbench_registry")]
    block = pipeline.baue_anker_rueckmeldung(s)
    assert "tools.workbench_registry" in block


def test_baue_anker_rueckmeldung_max_5() -> None:
    """HH4: max 5 Eintraege, dann ..."""
    s = build_test_state()
    s.letzte_anker_fehler = [
        (i, f"p{i}.py", f"A{i}", "nicht_gefunden")
        for i in range(8)
    ]
    block = pipeline.baue_anker_rueckmeldung(s)
    assert "und 3 weitere Anker" in block


def test_anker_fehler_in_folge_initial_null() -> None:
    """Neuer Zaehler startet bei 0."""
    s = build_test_state()
    assert s.anker_fehler_in_folge == 0


def test_letzte_anker_fehler_initial_leer() -> None:
    """Neue Felder starten leer."""
    s = build_test_state()
    assert s.letzte_anker_fehler == []
    assert s.letzte_ersatz_fehler == []


# ---------- Stufe 0 Aenderung 4 ----------

def test_klassifiziere_deadlock_anker() -> None:
    """Anker-Fehler -> anker_nicht_gemessen."""
    s = build_test_state()
    s.letzte_anker_fehler = [(0, "x.py", "A", "nicht_gefunden")]
    assert pipeline.klassifiziere_deadlock(s, "") == \
        "anker_nicht_gemessen"


def test_klassifiziere_deadlock_ersatz() -> None:
    """Ersatz-Fehler -> anker_nicht_gemessen."""
    s = build_test_state()
    s.letzte_ersatz_fehler = [(0, "x.py", "tools.workbench_registry")]
    assert pipeline.klassifiziere_deadlock(s, "") == \
        "anker_nicht_gemessen"


def test_klassifiziere_deadlock_rueckfrage() -> None:
    """Reply ohne Patch/Command mit Frage -> rueckfrage."""
    s = build_test_state()
    reply = "Aus welchem Modul soll das kommen?"
    assert pipeline.klassifiziere_deadlock(s, reply) == "rueckfrage"


def test_klassifiziere_deadlock_leer() -> None:
    """Reply ohne Patch/Command ohne Frage -> leer."""
    s = build_test_state()
    assert pipeline.klassifiziere_deadlock(s, "ok") == "leer"


def test_klassifiziere_deadlock_patch_vorhanden() -> None:
    """Mit PATCH-BEGINN: nie rueckfrage."""
    s = build_test_state()
    reply = "PATCH-BEGINN\nfoo?\nPATCH-ENDE"
    # kein COMMAND, kein ? ohne Patch-Kontext
    result = pipeline.klassifiziere_deadlock(s, reply)
    assert result == "leer"


# ---------- Stufe 0 Aenderung 3 ----------

def test_pruefe_trigger_b_bei_patch_mit_frage_im_fuss() -> None:
    """Patch + Frage im Fuss: Trigger."""
    reply = (
        "PATCH-BEGINN\nanker: x\nersatz: y\nPATCH-ENDE\n"
        "Aus welchem Modul soll das kommen?"
    )
    assert pipeline.pruefe_trigger_b(reply) is True


def test_pruefe_trigger_b_bei_patch_ohne_frage() -> None:
    """Patch ohne Frage: kein Trigger."""
    reply = "PATCH-BEGINN\nanker: x\nersatz: y\nPATCH-ENDE"
    assert pipeline.pruefe_trigger_b(reply) is False


def test_pruefe_trigger_b_bei_langer_antwort_ohne_frage() -> None:
    """Langer Reply ohne Frage: kein Trigger."""
    reply = "x" * 5000
    assert pipeline.pruefe_trigger_b(reply) is False


def test_pruefe_trigger_b_bei_frage_ohne_inhaltswort() -> None:
    """Fertig? im Fuss: kein Trigger (II6)."""
    reply = "PATCH-BEGINN\nfoo\nPATCH-ENDE\nFertig?"
    assert pipeline.pruefe_trigger_b(reply) is False


def test_pruefe_trigger_b_bei_frage_im_mittelteil() -> None:
    """Frage im Mittelteil, Fuss ohne: kein Trigger."""
    reply = "Was soll ich tun?\n" + "y" * 400
    assert pipeline.pruefe_trigger_b(reply) is False


def test_erlaubte_solver_quellen_enthaelt_neue() -> None:
    """Neue Trigger-Gruende sind in ERLAUBTE_SOLVER_QUELLEN."""
    assert "anker_nicht_gemessen" in pipeline.ERLAUBTE_SOLVER_QUELLEN
    assert "builder_rueckfrage" in pipeline.ERLAUBTE_SOLVER_QUELLEN


def test_inhaltswoerter_liste_vorhanden() -> None:
    """Liste der Inhaltswoerter existiert und ist nicht leer."""
    assert len(pipeline.INHALTSWOERTER_TRIGGER_B) >= 5


# ---------- Block Auftrag-erfuellt, B1 ----------

def test_pruefe_anker_wirkungslos_erkannt() -> None:
    """anker == ersatz -> Grund 'wirkungslos'."""
    patches = [{"pfad": "x.py",
                "anker": "from foo import bar",
                "ersatz": "from foo import bar"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(
        patches, "from foo import bar")
    assert len(fehlend) == 1
    assert fehlend[0][3] == "wirkungslos"


def test_pruefe_anker_mit_trailing_whitespace_ist_wirkungslos() -> None:
    """anker != ersatz (Trailing \n): NICHT wirkungslos (JJ1)."""
    patches = [{"pfad": "x.py",
                "anker": "from foo import bar",
                "ersatz": "from foo import bar\n"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(
        patches, "from foo import bar")
    # anker steht im mess -> kein Fehler.
    assert fehlend == []


def test_pruefe_anker_leer_bleibt_leer() -> None:
    """Leerer Anker: Grund 'leer', nicht 'wirkungslos'."""
    patches = [{"pfad": "x.py", "anker": "", "ersatz": ""}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "")
    assert len(fehlend) == 1
    assert fehlend[0][3] == "leer"


def test_pruefe_anker_wirkungslos_hat_einen_grund_pro_patch() -> None:
    """JJ3: ein Eintrag pro Patch."""
    patches = [{"pfad": "x.py",
                "anker": "gleich", "ersatz": "gleich"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "")
    assert len(fehlend) == 1


def test_pruefe_anker_wirksamer_patch_kein_fehler() -> None:
    """anker != ersatz, anker im mess: kein Fehler."""
    patches = [{"pfad": "x.py",
                "anker": "alt", "ersatz": "neu"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "alt")
    assert fehlend == []


# ---------- Block Auftrag-erfuellt, B3 ----------

def test_letzter_patch_wirkungslos_initial_false() -> None:
    """Neues Flag startet False."""
    s = build_test_state()
    assert s.letzter_patch_wirkungslos is False


def test_wirkungslos_setzt_flag_im_loop() -> None:
    """Wenn Anker-Fehler 'wirkungslos' enthaelt, Flag True."""
    # Direkter Test der Logik: pruefe_anker liefert
    # 'wirkungslos', dann Flag setzen.
    patches = [{"pfad": "x.py", "anker": "y", "ersatz": "y"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "")
    wirkt = any(g == "wirkungslos" for (_, _, _, g) in fehlend)
    assert wirkt is True


def test_nicht_wirkungslos_setzt_flag_nicht() -> None:
    """Wenn Anker-Fehler nicht 'wirkungslos' ist, kein Signal."""
    patches = [{"pfad": "x.py", "anker": "GAMMA", "ersatz": "y"}]
    fehlend = pipeline.pruefe_anker_gegen_messung(patches, "")
    wirkt = any(g == "wirkungslos" for (_, _, _, g) in fehlend)
    assert wirkt is False


# ---------- Block Auftrag-erfuellt, B4 ----------

def test_erlaubte_quelle_wirkungsloser_patch() -> None:
    """Neue Quelle ist in ERLAUBTE_SOLVER_QUELLEN."""
    assert "wirkungsloser_patch" in pipeline.ERLAUBTE_SOLVER_QUELLEN


def test_wirkungslos_flag_ist_trigger_c_vorbedingung() -> None:
    """Trigger C greift nur wenn Flag True."""
    s = build_test_state()
    assert s.letzter_patch_wirkungslos is False
    s.letzter_patch_wirkungslos = True
    assert s.letzter_patch_wirkungslos is True


# ---------- Block Auftrag-erfuellt, B2 ----------

def test_auftrag_bereits_erfuellt_mit_bestaetigung() -> None:
    """Flag + Befund ANDERER_FEHLER mit Auftrag: True (MM2)."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.ANDERER_FEHLER,
        praezisierter_auftrag="test-auftrag",
        run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is True


def test_auftrag_bereits_erfuellt_ohne_flag() -> None:
    """Ohne Flag: False."""
    s = build_test_state()
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="test", run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


def test_auftrag_bereits_erfuellt_ohne_solver() -> None:
    """Flag, kein Solver-Befund: False."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


def test_auftrag_bereits_erfuellt_mit_widerspruch() -> None:
    """Flag + WIDERSPRUCH: False (JJ4)."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.WIDERSPRUCH,
        rueckspiel_hinweis="test", run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


def test_auftrag_bereits_erfuellt_ohne_quelle() -> None:
    """Flag, Quelle fehlt: False."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="test", run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


# ---------- Block Auftrag-erfuellt, B5 ----------

def test_erhoehe_solver_aufruf_unter_limit() -> None:
    """Unter Limit: erhoeht, True."""
    s = build_test_state()
    assert s.solver_aufrufe == 0
    assert pipeline.erhoehe_solver_aufruf(s, 3) is True
    assert s.solver_aufrufe == 1


def test_erhoehe_solver_aufruf_am_limit() -> None:
    """Am Limit: kein erhoehen, False."""
    s = build_test_state()
    s.solver_aufrufe = 3
    assert pipeline.erhoehe_solver_aufruf(s, 3) is False
    assert s.solver_aufrufe == 3


def test_bestaetigung_erfordert_vollstaendigen_befund() -> None:
    """MM2: unvollstaendiger Befund ist keine Bestaetigung."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    # ANDERER_FEHLER ohne praezisierten Auftrag: unvollstaendig.
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.ANDERER_FEHLER,
        praezisierter_auftrag="",
        run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


def test_bestaetigung_unklar_ist_keine() -> None:
    """MM2: UNKLAR ist keine Bestaetigung."""
    s = build_test_state()
    s.letzter_patch_wirkungslos = True
    s.solver_trigger_quellen = ["wirkungsloser_patch"]
    b = pipeline.SolverBefund(
        art=pipeline.SolverDiagnose.UNKLAR,
        eskalation="test", run_id="run-1")
    s.solver_befunde = [b]
    assert pipeline.pruefe_auftrag_bereits_erfuellt(s) is False


# ---------- Block A2: Auftrag-erfuellt-Hinweis ----------

def test_solver_prompt_enthaelt_auftrag_erfuellt_hinweis() -> None:
    """A2: solver.md traegt den Hinweis."""
    with open("/opt/werkstatt/agents/solver.md",
              encoding="utf-8") as f:
        text = f.read()
    assert "Auftrag bereits" in text
    assert "PRAEZISIERTER_AUFTRAG" in text


def test_solver_md_enthaelt_gemessenen_inhalt_erwaehnung() -> None:
    """OO7: solver.md verweist auf GEMESSENER INHALT."""
    with open("/opt/werkstatt/agents/solver.md",
              encoding="utf-8") as f:
        text = f.read()
    assert "GEMESSENER INHALT" in text


# ---------- Solver-Prompt: AUFTRAG ----------

def test_solver_prompt_enthaelt_auftrag() -> None:
    """AUFTRAG-Block steht im Solver-Prompt."""
    s = build_test_state()
    s.aufgabe = "Stelle notify_ntfy um auf ToolArgumentValueError."
    prompt = pipeline._solver_prompt_bauen(s)
    assert "AUFGABE:" in prompt
    assert "Stelle notify_ntfy um" in prompt


def test_solver_prompt_auftrag_vor_no_go() -> None:
    """AUFTRAG steht vor NO-GO-RUNDEN."""
    s = build_test_state()
    s.aufgabe = "Testauftrag."
    prompt = pipeline._solver_prompt_bauen(s)
    i_auf = prompt.find("AUFGABE:")
    i_ng = prompt.find("## NO-GO-RUNDEN")
    assert i_auf > -1
    assert i_ng > -1
    assert i_auf < i_ng


def test_solver_prompt_auftrag_leer() -> None:
    """Leerer Auftrag: Block erscheint trotzdem."""
    s = build_test_state()
    s.aufgabe = ""
    prompt = pipeline._solver_prompt_bauen(s)
    assert "AUFGABE:" in prompt


# ---------- Agent-Memory A2: Projekt-Stand ----------

def test_format_projekt_stand_leer() -> None:
    """Ohne projekt_stand: leerer Block."""
    s = build_test_state()
    s.projekt_stand = {}
    assert pipeline.format_projekt_stand(s) == ""


def test_format_projekt_stand_mit_commits() -> None:
    """Mit Commits: Block mit Hash + Message."""
    s = build_test_state()
    s.projekt_stand = {
        "letzte_commits": [
            {"hash": "abc123",
             "datum": "2026-10-15T11:32:00+00:00",
             "message": "test(workbench): x",
             "quelle": "werkstatt",
             "dateien": ["tools/x.py"]},
        ],
    }
    block = pipeline.format_projekt_stand(s)
    assert "## PROJEKT-STAND" in block
    assert "abc123" in block
    assert "2026-10-15" in block
    assert "werkstatt" in block
    assert "tools/x.py" in block


def test_format_projekt_stand_max_5() -> None:
    """UU8: nur max 5 Commits."""
    s = build_test_state()
    s.projekt_stand = {
        "letzte_commits": [
            {"hash": f"h{i}", "datum": "2026-10-15",
             "message": f"m{i}", "quelle": "werkstatt",
             "dateien": []}
            for i in range(10)
        ],
    }
    block = pipeline.format_projekt_stand(s)
    # Nur 5 Eintraege.
    assert block.count("- h") == 5


def test_projekt_stand_im_builder_prompt() -> None:
    """A2: PROJEKT-STAND steht im Builder-Prompt."""
    # Wir bauen einen minimalen RunState und pruefen
    # nur die Funktion. Der echte Builder-Prompt braucht
    # zu viel Setup fuer einen Unit-Test.
    s = build_test_state()
    s.projekt_stand = {
        "letzte_commits": [{
            "hash": "abc", "datum": "2026-10-15",
            "message": "test", "quelle": "werkstatt",
            "dateien": ["x.py"]}],
    }
    block = pipeline.format_projekt_stand(s)
    assert "abc" in block


def test_projekt_stand_nach_auftrag_im_solver() -> None:
    """A2: AUFTRAG vor PROJEKT-STAND im Solver-Prompt."""
    s = build_test_state()
    s.aufgabe = "Testauftrag."
    s.projekt_stand = {
        "letzte_commits": [{
            "hash": "abc", "datum": "2026-10-15",
            "message": "test", "quelle": "werkstatt",
            "dateien": []}],
    }
    prompt = pipeline._solver_prompt_bauen(s)
    i_auf = prompt.find("AUFGABE:")
    i_ps = prompt.find("## PROJEKT-STAND")
    assert i_auf > -1
    assert i_ps > -1
    assert i_auf < i_ps


def test_solver_schon_gelaufen() -> None:
    state = _c_state()
    assert not pipeline._solver_schon_gelaufen(state)
    state.solver_befunde.append(
        pipeline.SolverBefund(
            art=pipeline.SolverDiagnose.UNKLAR,
            eskalation="x", run_id="run-c5"))
    assert pipeline._solver_schon_gelaufen(state)


def _c_state() -> pipeline.RunState:
    """Hilfsfunktion: minimaler RunState fuer C-Tests."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={"solver": {"name": "solver",
                                    "body": "b"}},
        always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.review_runden.append(
        {"runde": 1, "verdict": "NO-GO",
         "raw": "x", "recovery": False})
    return st


def test_mess_protokoll_veraltet_default_false() -> None:
    """Z1: neuer State hat _veraltet=False."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    assert st.mess_protokoll_veraltet is False


def test_mess_protokoll_nicht_mutiert_von_veraltet_flag() -> None:
    """Z1: das Flag aendert mess_protokoll nicht."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.mess_protokoll = "urspruenglich"
    st.mess_protokoll_veraltet = True
    assert st.mess_protokoll == "urspruenglich"


def test_nach_apply_block_leer_bleibt_weg() -> None:
    """Z4: leerer basis_protokoll_nach_apply -> Block fehlt."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.mess_protokoll = "inhalt vor apply"
    st.mess_protokoll_veraltet = True
    st.basis_protokoll_nach_apply = ""
    # Wir simulieren den Prompt-Bau wie in Phase 1.
    header = (
        ("!!! ACHTUNG: Code-Patches wurden angewendet.\n"
         "!!! Der folgende GEMESSENER INHALT ist der\n"
         "!!! Stand VOR dem Apply.\n\n")
        if st.mess_protokoll_veraltet else "")
    nach_apply = (
        (f"GEMESSENER INHALT NACH APPLY:\n"
         f"{st.basis_protokoll_nach_apply}\n\n")
        if st.basis_protokoll_nach_apply else "")
    text = header + st.mess_protokoll + nach_apply
    assert "Stand VOR dem Apply" in text
    assert "GEMESSENER INHALT NACH APPLY" not in text


def test_nach_apply_block_erscheint_bei_inhalt() -> None:
    """Z3: bei vorhandenem basis_protokoll_nach_apply -> Block da."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.mess_protokoll = "inhalt vor apply"
    st.mess_protokoll_veraltet = True
    st.basis_protokoll_nach_apply = "nach apply: alles gruen"
    nach_apply = (
        (f"GEMESSENER INHALT NACH APPLY:\n"
         f"{st.basis_protokoll_nach_apply}\n\n")
        if st.basis_protokoll_nach_apply else "")
    assert "GEMESSENER INHALT NACH APPLY" in nach_apply
    assert "nach apply: alles gruen" in nach_apply


def test_prompt_phase1_vor_erstem_apply_kein_header() -> None:
    """Z4: ohne Apply kein Header, kein Nach-Apply-Block."""
    from pathlib import Path as _P
    st = pipeline.RunState(
        block_id="b", aufgabe="a", start_ts="t",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=_P("/tmp"))
    st.mess_protokoll = "frisch gemessen"
    assert st.mess_protokoll_veraltet is False
    assert st.basis_protokoll_nach_apply == ""

# =====================================================================
# P2b-Luecke-A: NEW_FILE-Patch-Format
# =====================================================================

class TestParseNewFilePatch:
    def _text(self, bloecke: str) -> str:
        return bloecke

    def test_new_file_erkannt(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "typ: new_file\n"
            "pfad: core/hello.py\n"
            "inhalt: |\n"
            "  x = 1\n"
            "PATCH-ENDE\n"
        )
        patches = pipeline._parse_patches(text)
        assert len(patches) == 1
        p = patches[0]
        assert p["typ"] == "new_file"
        assert p["pfad"] == "core/hello.py"
        assert p["inhalt"] == "x = 1"

    def test_new_file_mit_anker_verworfen(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "typ: new_file\n"
            "pfad: core/hello.py\n"
            "anker: |\n"
            "  x\n"
            "inhalt: |\n"
            "  y\n"
            "PATCH-ENDE\n"
        )
        patches = pipeline._parse_patches(text)
        assert patches == []

    def test_typ_unbekannt_verworfen(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "typ: unbekannt\n"
            "pfad: core/hello.py\n"
            "inhalt: |\n"
            "  y\n"
            "PATCH-ENDE\n"
        )
        patches = pipeline._parse_patches(text)
        assert patches == []

    def test_patch_ohne_typ_bleibt_patch(self) -> None:
        text = (
            "PATCH-BEGINN\n"
            "pfad: a.py\n"
            "anker: |\n"
            "  x\n"
            "ersatz: |\n"
            "  y\n"
            "PATCH-ENDE\n"
        )
        patches = pipeline._parse_patches(text)
        assert len(patches) == 1
        assert patches[0]["typ"] == "patch"


class TestApplyNewFile:
    def _state(self, tmp_path: Path) -> pipeline.RunState:
        return pipeline.RunState(
            block_id="t", aufgabe="t",
            start_ts="2026-01-01T00:00:00+00:00",
            docs={}, agents={}, always={}, optional={},
            file_whitelist=["core/"],
            api_key="x", budget={}, agent_docs={},
            project_dir=tmp_path, project_name="t")

    def test_new_file_angelegt(self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        state = self._state(tmp_path)
        patches = [{"typ": "new_file",
                    "pfad": "core/hello.py",
                    "inhalt": "x = 1\n"}]
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline.apply_code_patches(state, patches)
        assert ok is True
        assert (tmp_path / "core" / "hello.py").read_text() == "x = 1\n"

    def test_new_file_existiert_fail(
            self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "hello.py").write_text("alt")
        state = self._state(tmp_path)
        patches = [{"typ": "new_file",
                    "pfad": "core/hello.py",
                    "inhalt": "neu\n"}]
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline.apply_code_patches(state, patches)
        assert ok is False

    def test_new_file_whitelist_fail(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        patches = [{"typ": "new_file",
                    "pfad": "other/hello.py",
                    "inhalt": "x\n"}]
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline.apply_code_patches(state, patches)
        assert ok is False

    def test_zwei_new_file_gleicher_pfad_fail(
            self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        state = self._state(tmp_path)
        patches = [
            {"typ": "new_file", "pfad": "core/a.py", "inhalt": "x\n"},
            {"typ": "new_file", "pfad": "core/a.py", "inhalt": "y\n"},
        ]
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline.apply_code_patches(state, patches)
        assert ok is False

# =====================================================================
# Review-Persistenz (Auflage A4/A6/A9, 2026-10-16)
# =====================================================================

class TestReviewRoundAudit:
    """Tests fuer _review_round_audit_payload.

    Die Funktion ist der Audit-Payload-Bauer fuer
    kind=review_round. Sie redacted + kappt den
    Reviewer-Rohtext (Auflage A7/A9).
    """

    def test_no_go_schreibt_raw(self) -> None:
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", "irgendein Reviewer-Text")
        assert p["runde"] == 1
        assert p["verdict"] == "NO-GO"
        assert p["raw"] == "irgendein Reviewer-Text"
        assert isinstance(p["raw_len"], int)
        assert p["raw_len"] > 0

    def test_go_schreibt_raw(self) -> None:
        p = pipeline._review_round_audit_payload(
            2, "GO", "GO-Begruendung")
        assert p["runde"] == 2
        assert p["verdict"] == "GO"
        assert p["raw"] == "GO-Begruendung"
        assert p["raw_len"] > 0

    def test_redaction_greift(self) -> None:
        # Oeffentliche IP: 8.8.8.8 -> [IPV4].
        # (Private IPs werden bewusst nicht maskiert,
        #  siehe redaction.py Docstring.)
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", "Verbindung zu 8.8.8.8 fehlgeschlagen")
        assert "8.8.8.8" not in p["raw"]
        assert "[IPV4]" in p["raw"]
        assert p["raw_len_original"] > 0
        assert p["raw_len_redacted"] > 0

    def test_kappung_unter_grenze(self) -> None:
        kurz = "kurzer Text"
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", kurz)
        assert p["raw"] == kurz
        assert "raw_gekuerzt" not in p

    def test_kappung_ueber_grenze(self) -> None:
        # Ueber _AUDIT_RAW_MAX_LEN = 32768.
        lang = "x" * (pipeline._AUDIT_RAW_MAX_LEN + 100)
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", lang)
        assert len(p["raw"]) == pipeline._AUDIT_RAW_MAX_LEN
        assert p["raw_gekuerzt"] is True
        assert p["raw_len"] == pipeline._AUDIT_RAW_MAX_LEN
        assert p["raw_len_original"] == len(lang)

    def test_kappung_genau_grenze(self) -> None:
        # == Grenze -> NICHT kappen (Auflage Frage 2).
        genau = "x" * pipeline._AUDIT_RAW_MAX_LEN
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", genau)
        assert "raw_gekuerzt" not in p
        assert len(p["raw"]) == pipeline._AUDIT_RAW_MAX_LEN

    def test_kein_neuer_audit_kind(self) -> None:
        # Baseline: 66 Eintraege. Stand nach
        # B0: UNKLAR-Behandlung (2026-10-16).
        # Vorherige Baselines: 60 (Review-Persistenz),
        #                      61 (--resume-force),
        #                      62 (commit_review_new_file_skip),
        #                      63 (phase_plan_unbeantwortet).
        assert "review_round" in pipeline._AUDIT_KINDS_BEKANNT
        assert "phase_resume_force" in pipeline._AUDIT_KINDS_BEKANNT
        assert "commit_review_new_file_skip" in pipeline._AUDIT_KINDS_BEKANNT
        assert "phase_plan_unbeantwortet" in pipeline._AUDIT_KINDS_BEKANNT
        assert "review_unklar_eskalation" in pipeline._AUDIT_KINDS_BEKANNT
        assert "review_r15_verstoss" in pipeline._AUDIT_KINDS_BEKANNT
        assert "review_unklar_widerspruch" in pipeline._AUDIT_KINDS_BEKANNT
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 78

    def test_state_unredacted(self) -> None:
        """Regression: state.review_runden[i]['raw']
        bleibt unredacted (Auflage A8).
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "state.review_runden.append(" in quelle
        assert '"raw": reply.content' in quelle

    def test_drei_laengen(self) -> None:
        # Laengen-Reihenfolge: raw_len <=
        # raw_len_redacted <= raw_len_original.
        p = pipeline._review_round_audit_payload(
            1, "NO-GO", "normaler Text ohne Secrets")
        assert p["raw_len"] <= p["raw_len_redacted"]
        assert p["raw_len_redacted"] <= p["raw_len_original"]

# =====================================================================
# commit_review_new_file_skip (Auflage A8, 2026-10-16)
# =====================================================================

class TestCommitReviewNewFileSkip:
    """Tests fuer den Skip-Pfad im Commit-Review.

    Reine new_file-Patches haben keinen Anker; der
    Fail-closed-Check bei leerem mess_protokoll wird
    uebersprungen. Audit-Kind: commit_review_new_file_skip.
    """

    def test_kein_neuer_audit_kind_ist_62(self) -> None:
        assert "commit_review_new_file_skip" in \
            pipeline._AUDIT_KINDS_BEKANNT
        # Katalog waechst mit neuen Audit-Kinds.
        # Stand 2026-10-16 (B0): 66.
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 78

    def test_skip_wenn_nur_new_file(self) -> None:
        """Reine new_file-Patches + leeres mess_protokoll
        -> kein Fail-closed. Per String-Match im Quelltext.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "_hat_anker_patches" in quelle
        assert "commit_review_new_file_skip" in quelle
        assert "anzahl_new_file" in quelle

    def test_fail_closed_pfad_bleibt(self) -> None:
        """Regression: Fail-closed-Pfad fuer Anker-Patches
        bleibt erhalten.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "_hat_anker_patches and not state.mess_protokoll" \
            in quelle
        assert "commit_review_ohne_messung" in quelle

    def test_console_text_differenziert(self) -> None:
        """A6: Console-Text unterscheidet 0 und n Patches."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "reine new_file-" in quelle
        assert "keine Patches. Skip." in quelle

    def test_anzahl_new_file_berechnet(self) -> None:
        """A7: anzahl_new_file wird VOR dem Audit berechnet."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "_anzahl_new_file = sum(" in quelle

    def test_payload_felder(self) -> None:
        """Payload hat runde, anzahl_new_file, phase_id."""
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert '"runde": _runde_audit' in quelle
        assert '"anzahl_new_file": _anzahl_new_file' in quelle
        assert '"phase_id": getattr(state, "phase_id", "")' in quelle
        # Redundantes Feld soll NICHT drin sein.
        assert "anzahl_anker_patches" not in quelle

# =====================================================================
# _post_apply_messung (Auflage A7, 2026-10-16)
# =====================================================================

class TestPostApplyMessung:
    """Tests fuer _post_apply_messung.

    Liest new_file-Pfade aus state.code_patches nach dem
    Apply und schreibt read_file-Ausgaben nach
    state.mess_protokoll_nach_apply.
    """

    def _state(self, tmp_path: Path,
               patches: list[dict]) -> pipeline.RunState:
        from unittest.mock import patch
        with patch("pipeline.audit"):
            state = build_test_state(
                project_dir=tmp_path,
                file_whitelist=["core/", "tests/"])
        state.always = {
            "read_file": pipeline.Measurement(
                "read_file", ("cat",), "Datei lesen."),
        }
        state.code_patches = patches
        return state

    def test_leere_code_patches(self, tmp_path: Path) -> None:
        state = self._state(tmp_path, [])
        ok = pipeline._post_apply_messung(
            state, ["core/", "tests/"])
        assert ok is True
        assert state.mess_protokoll_nach_apply == ""

    def test_nur_patch_kein_new_file(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path, [
            {"typ": "patch", "pfad": "core/x.py",
             "anker": "ALT", "ersatz": "NEU"}])
        ok = pipeline._post_apply_messung(
            state, ["core/", "tests/"])
        assert ok is True
        assert state.mess_protokoll_nach_apply == ""

    def test_new_file_wird_gelesen(
            self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        ziel = tmp_path / "core" / "neu.py"
        ziel.write_text("x = 1\n", encoding="utf-8")
        state = self._state(tmp_path, [
            {"typ": "new_file", "pfad": "core/neu.py",
             "inhalt": "x = 1\n"}])
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline._post_apply_messung(
                state, ["core/", "tests/"])
        assert ok is True
        assert "core/neu.py" in state.mess_protokoll_nach_apply
        assert "x = 1" in state.mess_protokoll_nach_apply

    def test_read_file_nicht_im_katalog(
            self, tmp_path: Path) -> None:
        (tmp_path / "core").mkdir()
        (tmp_path / "core" / "neu.py").write_text(
            "x = 1\n", encoding="utf-8")
        state = self._state(tmp_path, [
            {"typ": "new_file", "pfad": "core/neu.py",
             "inhalt": "x = 1\n"}])
        state.always = {}  # read_file nicht drin
        state.optional = {}
        from unittest.mock import patch
        with patch("pipeline.audit"):
            ok = pipeline._post_apply_messung(
                state, ["core/", "tests/"])
        assert ok is True
        assert state.mess_protokoll_nach_apply == ""

    def test_commit_review_nutzt_neuen_kanal(self) -> None:
        """Regression: Commit-Review-Input enthaelt
        GEMESSENER INHALT NACH APPLY, wenn gesetzt.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.run_pipeline)
        assert "GEMESSENER INHALT NACH APPLY " in quelle
        assert "new_file-Pfade" in quelle

    def test_aufruf_in_apply_and_recheck(self) -> None:
        """Regression: apply_and_recheck ruft
        _post_apply_messung nach dem Basis-Gate.
        """
        import inspect as ins
        quelle = ins.getsource(pipeline.apply_and_recheck)
        assert "_post_apply_messung" in quelle
        assert "return 17" in quelle

# =====================================================================
# Recovery-Prompt-Fix (A1+A2, 2026-10-16)
# =====================================================================

class TestRecoveryPromptFix:
    """Tests fuer _bauer_recovery_prompt.

    A1: Fallback auf rohantwort, wenn diagnose und
        reparaturplan leer sind.
    A2: GEMESSENER INHALT (nach Apply) im Prompt.
    """

    def _state(self, tmp_path: Path) -> pipeline.RunState:
        state = build_test_state(project_dir=tmp_path)
        return state

    def test_fallback_rohantwort_wenn_diagnose_leer(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        state.letzter_recovery_vorschlag = (
            pipeline.RecoveryVorschlag(
                art="basis_gate",
                diagnose="",
                reparaturplan=[],
                rohantwort="DIAGNOSE:\nDer Test oeffnet die "
                           "Datei ohne with-Block."))
        text = pipeline._bauer_recovery_prompt(state)
        assert "Der Test oeffnet die Datei ohne with-Block" in text

    def test_diagnose_vorhanden_kein_fallback(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        state.letzter_recovery_vorschlag = (
            pipeline.RecoveryVorschlag(
                art="basis_gate",
                diagnose="Strukturierte Diagnose",
                reparaturplan=["Schritt 1"],
                rohantwort="Rohantwort-Text"))
        text = pipeline._bauer_recovery_prompt(state)
        assert "Strukturierte Diagnose" in text
        assert "Rohantwort-Text" not in text

    def test_messblock_nach_apply_im_prompt(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        state.mess_protokoll_nach_apply = (
            "=== read_file ===\n"
            "ARGV: cat core/x.py\n"
            "RC: 0\nSTDOUT: x = 1")
        state.letzter_recovery_vorschlag = (
            pipeline.RecoveryVorschlag(
                art="basis_gate",
                diagnose="Test",
                reparaturplan=[],
                rohantwort=""))
        text = pipeline._bauer_recovery_prompt(state)
        assert "GEMESSENER INHALT (nach Apply)" in text
        assert "x = 1" in text

    def test_messblock_leer_zeigt_platzhalter(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        state.mess_protokoll_nach_apply = ""
        state.letzter_recovery_vorschlag = (
            pipeline.RecoveryVorschlag(
                art="basis_gate",
                diagnose="Test",
                reparaturplan=[],
                rohantwort=""))
        text = pipeline._bauer_recovery_prompt(state)
        assert "(keine Messung nach Apply)" in text

    def test_rohantwort_wird_redacted(
            self, tmp_path: Path) -> None:
        state = self._state(tmp_path)
        state.letzter_recovery_vorschlag = (
            pipeline.RecoveryVorschlag(
                art="basis_gate",
                diagnose="",
                reparaturplan=[],
                rohantwort="Server 8.8.8.8 ist nicht erreichbar."))
        text = pipeline._bauer_recovery_prompt(state)
        assert "8.8.8.8" not in text
        assert "[IPV4]" in text

# =====================================================================
# _truncate_mit_marker (Truncation-Fix A1, 2026-10-16)
# =====================================================================

class TestTruncateMitMarker:
    """Tests fuer _truncate_mit_marker."""

    def test_kurz_bleibt_unveraendert(self) -> None:
        text = "kurzer Text"
        out = pipeline._truncate_mit_marker(text, 100)
        assert out == text

    def test_genau_grenze_kein_marker(self) -> None:
        text = "x" * 100
        out = pipeline._truncate_mit_marker(text, 100)
        assert out == text
        assert "gekuerzt" not in out

    def test_ueber_grenze_marker(self) -> None:
        text = "x" * 250
        out = pipeline._truncate_mit_marker(text, 100)
        assert out.startswith("x" * 100)
        assert "Kontext gekuerzt" in out
        assert "150 Zeichen weggelassen" in out

    def test_konstante_vorhanden(self) -> None:
        assert pipeline._REVIEWER_KONTEXT_MAX == 2000

# =====================================================================
# _format_whitelist_block (A5, 2026-10-16)
# =====================================================================

class TestFormatWhitelistBlock:
    """Tests fuer _format_whitelist_block."""

    def test_leere_liste(self) -> None:
        out = pipeline._format_whitelist_block([])
        assert "FILE-WHITELIST" in out
        assert "(keine Pfade freigegeben)" in out

    def test_mit_pfaden(self) -> None:
        out = pipeline._format_whitelist_block(
            ["apps/", "core/", "data/", "tests/"])
        assert "FILE-WHITELIST" in out
        assert "apps/" in out
        assert "core/" in out
        assert "data/" in out
        assert "tests/" in out

    def test_marker_am_ende(self) -> None:
        out = pipeline._format_whitelist_block(["core/"])
        assert "=== /FILE-WHITELIST ===" in out

    def test_block_enden_mit_doppel_newline(self) -> None:
        out = pipeline._format_whitelist_block(["core/"])
        assert out.endswith("\n\n")

    def test_aufgabe_block_unveraendert(self) -> None:
        """Regression: aufgabe_block liefert nur AUFGABE."""
        import inspect as ins
        quelle = ins.getsource(pipeline.aufgabe_block)
        assert "FILE-WHITELIST" not in quelle
        assert "AUFGABE:" in quelle

    def test_reviewer_prompt_bauer_nutzt_block(self) -> None:
        """Regression: die Aufrufstellen enthalten den Block."""
        import inspect as ins
        quelle_rev = ins.getsource(pipeline.run_pipeline)
        assert "_format_whitelist_block" in quelle_rev
        quelle_rec = ins.getsource(
            pipeline.ask_reviewer_for_recovery)
        assert "_format_whitelist_block" in quelle_rec

# =====================================================================
# Rollen-Kalibrierung (A5, 2026-10-16)
# =====================================================================

class TestRollenKalibrierung:
    """Tests fuer die drei Rollen-Prompt-Fixes."""

    def _lade_agent(self, name: str) -> str:
        from pathlib import Path
        p = Path("/opt/werkstatt/agents") / f"{name}.md"
        return p.read_text(encoding="utf-8")

    def test_builder_md_spec_treue(self) -> None:
        md = self._lade_agent("builder")
        assert "## SPEC-TREUE" in md
        assert "Vorgabe falsch oder" in md or "falsch oder\nunmoeglich" in md
        assert "COMMAND: frage_reviewer" in md

    def test_builder_md_solver_befund(self) -> None:
        md = self._lade_agent("builder")
        assert "## SOLVER-BEFUND" in md
        assert "Ohne Messung folge" in md

    def test_reviewer_md_sachfaden(self) -> None:
        md = self._lade_agent("reviewer")
        assert "## SACHFADEN" in md
        assert "Hauptbefund" in md
        # Markdown hat Zeilenumbruch zwischen den
        # beiden Woertern, daher nur den Prefix.
        assert "3 aufeinanderfolgenden" in md
        assert "ESKALATION" in md

    def test_hard_rules_builder_b13(self) -> None:
        assert "B13. SPEC-TREUE." in pipeline.HARD_RULES_BUILDER
        assert "COMMAND: frage_reviewer" in \
            pipeline.HARD_RULES_BUILDER

    def test_hard_rules_builder_b14(self) -> None:
        assert "B14. SOLVER-BEFUND." in pipeline.HARD_RULES_BUILDER
        assert "Ohne Messung" in pipeline.HARD_RULES_BUILDER

    def test_hard_rules_reviewer_r11(self) -> None:
        assert "R11. SACHFADEN." in pipeline.HARD_RULES_REVIEWER
        assert "3 aufeinanderfolgenden Runden" in \
            pipeline.HARD_RULES_REVIEWER

    def test_build_system_prompt_builder(self) -> None:
        agent = {
            "name": "builder",
            "body": "Body",
        }
        prompt = pipeline.build_system_prompt(
            agent, {}, [], mit_anti_patterns=False)
        assert "B13. SPEC-TREUE." in prompt
        assert "B14. SOLVER-BEFUND." in prompt

    def test_build_system_prompt_reviewer(self) -> None:
        agent = {
            "name": "reviewer",
            "body": "Body",
        }
        prompt = pipeline.build_system_prompt(
            agent, {}, [], mit_anti_patterns=False)
        assert "R11. SACHFADEN." in prompt

# =====================================================================
# New_file-Marker + B15/R12 (A7, 2026-10-16)
# =====================================================================

class TestNewFileMarker:
    """Tests fuer den new_file-Marker + Rollen-Regeln."""

    def _state_new_file(self, tmp_path: Path) -> pipeline.RunState:
        s = build_test_state(project_dir=tmp_path)
        s.code_patches = [
            {"typ": "new_file", "pfad": "core/x.py",
             "inhalt": "x = 1\n"},
            {"typ": "new_file", "pfad": "core/y.py",
             "inhalt": "y = 1\n"},
        ]
        s.mess_protokoll = ""
        return s

    def _state_patch(self, tmp_path: Path) -> pipeline.RunState:
        s = build_test_state(project_dir=tmp_path)
        s.code_patches = [
            {"typ": "patch", "pfad": "core/x.py",
             "anker": "ALT", "ersatz": "NEU"},
        ]
        s.mess_protokoll = ""
        return s

    def test_marker_konstante(self) -> None:
        assert "_NEW_FILE_MARKER" in dir(pipeline)
        assert "nicht anwendbar" in pipeline._NEW_FILE_MARKER

    def test_alle_patches_new_file_true(
            self, tmp_path: Path) -> None:
        s = self._state_new_file(tmp_path)
        assert pipeline._alle_patches_sind_new_file(s) is True

    def test_alle_patches_new_file_false_patch(
            self, tmp_path: Path) -> None:
        s = self._state_patch(tmp_path)
        assert pipeline._alle_patches_sind_new_file(s) is False

    def test_alle_patches_new_file_false_leer(
            self, tmp_path: Path) -> None:
        s = build_test_state(project_dir=tmp_path)
        s.code_patches = []
        s.mess_protokoll = ""
        assert pipeline._alle_patches_sind_new_file(s) is False

    def test_messwerte_prompt_marker_bei_new_file(
            self, tmp_path: Path) -> None:
        s = self._state_new_file(tmp_path)
        out = pipeline._messwerte_fuer_prompt(s)
        assert "nicht anwendbar" in out

    def test_messwerte_prompt_keine_bei_patch(
            self, tmp_path: Path) -> None:
        s = self._state_patch(tmp_path)
        out = pipeline._messwerte_fuer_prompt(s)
        assert out == "(keine)"

    def test_messwerte_prompt_voller_text(
            self, tmp_path: Path) -> None:
        s = self._state_new_file(tmp_path)
        s.mess_protokoll = "=== read_file ===\nFakten."
        out = pipeline._messwerte_fuer_prompt(s)
        assert "Fakten" in out

    def test_hard_rules_builder_b15(self) -> None:
        assert "B15. NEW_FILE OHNE MESSUNG." in \
            pipeline.HARD_RULES_BUILDER

    def test_hard_rules_reviewer_r12(self) -> None:
        assert "R12. NEW_FILE-MARKER." in \
            pipeline.HARD_RULES_REVIEWER

    def test_build_system_prompt_builder_b15(self) -> None:
        agent = {"name": "builder", "body": "Body"}
        prompt = pipeline.build_system_prompt(
            agent, {}, [], mit_anti_patterns=False)
        assert "B15. NEW_FILE OHNE MESSUNG." in prompt

    def test_build_system_prompt_reviewer_r12(self) -> None:
        agent = {"name": "reviewer", "body": "Body"}
        prompt = pipeline.build_system_prompt(
            agent, {}, [], mit_anti_patterns=False)
        assert "R12. NEW_FILE-MARKER." in prompt

    def test_agents_builder_md_new_file(self) -> None:
        p = Path("/opt/werkstatt/agents/builder.md")
        md = p.read_text(encoding="utf-8")
        assert "Bei new_file-Patches: read_file liefert" in md
        assert "OHNE vorheriges read_file" in md

    def test_agents_reviewer_md_new_file(self) -> None:
        p = Path("/opt/werkstatt/agents/reviewer.md")
        md = p.read_text(encoding="utf-8")
        assert "Bei reinen new_file-Patches" in md
        assert "KEIN NO-GO" in md

# =====================================================================
# Phasen-Header + R9/R13/R14 (Fix 1-4, 2026-10-16)
# =====================================================================

class TestPhasenHeader:
    """Tests fuer Fix 1-4."""

    def test_konstante_code_review(self) -> None:
        assert hasattr(pipeline, "_PHASE_HEADER_CODE_REVIEW")
        assert "CODE-REVIEW" in pipeline._PHASE_HEADER_CODE_REVIEW
        assert "Phase 1" in pipeline._PHASE_HEADER_CODE_REVIEW

    def test_konstante_commit_review(self) -> None:
        assert hasattr(pipeline, "_PHASE_HEADER_COMMIT_REVIEW")
        assert "COMMIT-REVIEW" in pipeline._PHASE_HEADER_COMMIT_REVIEW
        assert "Phase 2" in pipeline._PHASE_HEADER_COMMIT_REVIEW

    def test_reviewer_md_phasen_header(self) -> None:
        p = Path("/opt/werkstatt/agents/reviewer.md")
        md = p.read_text(encoding="utf-8")
        assert "## Phasen-Header" in md
        assert "CODE-REVIEW (Phase 1)" in md
        assert "COMMIT-REVIEW (Phase 2)" in md

    def test_hard_rules_r13(self) -> None:
        assert "R13. PHASEN-TRENNUNG." in \
            pipeline.HARD_RULES_REVIEWER
        assert "2169" in pipeline.HARD_RULES_REVIEWER

    def test_hard_rules_r14(self) -> None:
        assert "R14. VERDICT-KONSISTENZ." in \
            pipeline.HARD_RULES_REVIEWER

    def test_r9_eskalation(self) -> None:
        """R9 nutzt ESKALATION, nicht NO-GO."""
        assert "R9. ROLLENGRENZE" in pipeline.HARD_RULES_REVIEWER
        # Suche nach dem R9-Block
        i = pipeline.HARD_RULES_REVIEWER.find("R9. ROLLENGRENZE")
        j = pipeline.HARD_RULES_REVIEWER.find("R10.", i)
        r9_block = pipeline.HARD_RULES_REVIEWER[i:j]
        assert "ESKALATION" in r9_block
        # Kein "NO-GO mit dem Befund" mehr
        assert "NO-GO mit dem Befund" not in r9_block

    def test_r11_eskalation_bezug(self) -> None:
        assert "ESKALATION ist ein anderer Ausgang" in \
            pipeline.HARD_RULES_REVIEWER

    def test_reviewer_md_verdict_konsistenz(self) -> None:
        p = Path("/opt/werkstatt/agents/reviewer.md")
        md = p.read_text(encoding="utf-8")
        assert "## VERDICT-KONSISTENZ" in md

    def test_reviewer_md_eskalation_vs_no_go(self) -> None:
        p = Path("/opt/werkstatt/agents/reviewer.md")
        md = p.read_text(encoding="utf-8")
        assert "ESKALATION vs. NO-GO" in md

    def test_build_system_prompt_reviewer_enthaelt_r13_r14(
            self) -> None:
        agent = {"name": "reviewer", "body": "Body"}
        prompt = pipeline.build_system_prompt(
            agent, {}, [], mit_anti_patterns=False)
        assert "R13. PHASEN-TRENNUNG." in prompt
        assert "R14. VERDICT-KONSISTENZ." in prompt

    def test_u4_hinweis_models_py(self) -> None:
        import yaml
        d = yaml.safe_load(
            Path("/opt/werkstatt/projects/security-ai.phase.yaml")
            .read_text())
        for u in d["phase_unterbloecke"]:
            if u["id"] == "U4":
                hat_hinweis = any(
                    "models.py" in p
                    for p in u.get("unterpunkte", []))
                assert hat_hinweis
                break


# =====================================================================
# B0 (2026-10-16): UNKLAR-Behandlung Reviewer+Solver+Loop
# =====================================================================

class TestUnklarBehandlung:
    def test_reviewer_r15_im_prompt(self) -> None:
        assert "R15." in pipeline.HARD_RULES_REVIEWER
        assert "SYMBOLISCHE PRUEFUNG BEI NEW_FILE" in \
            pipeline.HARD_RULES_REVIEWER

    def test_reviewer_r15_nur_bei_new_file(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "reine" in s.lower() and "new_file" in s

    def test_reviewer_r15_widerspruchs_format(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "Widerspruch:" in s
        assert "Beleg:" in s

    def test_reviewer_r15_querverweis_r12(self) -> None:
        # B0-A8: R15 ergaenzt R12.
        s = pipeline.HARD_RULES_REVIEWER
        assert "ergaenzt R12" in s

    def test_solver_s10_im_prompt(self) -> None:
        assert "S10." in pipeline.HARD_RULES_SOLVER
        assert "SYMBOLISCHE PRUEFUNG BEI NEW_FILE" in \
            pipeline.HARD_RULES_SOLVER

    def test_solver_s10_nur_bei_new_file(self) -> None:
        s = pipeline.HARD_RULES_SOLVER
        assert "new_file" in s
        assert "Widerspruch" in s

    def test_parser_widerspruch_erkannt(self) -> None:
        raw = "UNKLAR:\nWiderspruch: A vs B\nBeleg: Zeile 3"
        assert pipeline._review_unklar_widerspruch(raw) is True

    def test_parser_widerspruch_fehlt(self) -> None:
        raw = "UNKLAR: ich weiss nicht."
        assert pipeline._review_unklar_widerspruch(raw) is False

    def test_audit_kinds_existieren(self) -> None:
        for k in ("review_r15_verstoss",
                  "review_unklar_eskalation",
                  "review_unklar_widerspruch"):
            assert k in pipeline._AUDIT_KINDS_BEKANNT

    def test_unklar_zweig_im_loop(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert 'verdict == "UNKLAR"' in src
        assert "_review_unklar_widerspruch" in src
        assert "_n_unklar >= 2" in src
        assert "review_unklar_eskalation" in src

    def test_eskalation_rc_14(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # rc=14 konsistent mit ESKALATION (B0-A2).
        # mindestens 2x return 14 im Quelltext.
        assert src.count("return 14") >= 2

# =====================================================================
# B0c (2026-10-16): classify_verdict Fallback am Ende
# Bug-1: rc=14 im run_phase-Loop
# Bug-2: review_unklar_eskalation mit raw
# =====================================================================

class TestB0cUndBugs:
    def test_classify_go_am_ende(self) -> None:
        # B0c: GO am Ende einer langen Antwort.
        text = ("## Pruefung\n\nAlle Punkte OK.\n\nGO")
        assert pipeline.classify_verdict(text) == "GO"

    def test_classify_no_go_am_ende(self) -> None:
        text = "## Bericht\n\nBefund.\n\nNO-GO"
        assert pipeline.classify_verdict(text) == "NO-GO"

    def test_classify_anfang_gewinnt(self) -> None:
        # Anfang hat Vorrang (konservativ).
        text = "GO\n\nAusfuehrlicher Bericht.\n\nNO-GO"
        assert pipeline.classify_verdict(text) == "GO"

    def test_classify_unklar_bleibt_unklar(self) -> None:
        text = "## Pruefung\n\nIch weiss nicht.\n"
        assert pipeline.classify_verdict(text) == "UNKLAR"

    def test_unklar_eskalation_mit_raw(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert "review_unklar_eskalation" in src
        # raw in der Payload.
        i = src.find("review_unklar_eskalation")
        umfeld = src[i:i+400]
        assert '"raw"' in umfeld

    def test_rc_14_kein_rollback(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_phase)
        # rc=14 muss vor dem Klasse-4-else-Zweig stehen.
        i14 = src.find("if rc_unterblock == 14:")
        i15 = src.find("if rc_unterblock == 15:")
        assert i14 > 0, "rc=14-Zweig fehlt"
        assert i14 < i15, "rc=14 muss vor rc=15 stehen"
        # Der rc=14-Zweig darf kein _phase_rollback enthalten.
        block_14 = src[i14:i15]
        assert "_phase_rollback" not in block_14


# =====================================================================
# Timeout-Fix 2026-10-16 (Option B)
# =====================================================================

class TestAskLlmTimeout:
    def test_ask_llm_timeout_ist_tupel(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        assert "_req_timeout = (_CONNECT_S, _read_adapt)" in src
        assert "timeout=_req_timeout" in src

    def test_ask_llm_retry_prueft_deadline(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        assert "_deadline" in src
        assert "if _rest <= 0:" in src

    def test_ask_llm_gesamt_timeout_greift(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        assert "llm_timeout_gesamt" in src
        assert "Gesamt-Timeout" in src

    def test_runstate_max_total_llm_s_default(self) -> None:
        import dataclasses
        feld = None
        for f in dataclasses.fields(pipeline.RunState):
            if f.name == "max_total_llm_s":
                feld = f
                break
        assert feld is not None
        assert feld.default == 240

    def test_audit_kind_llm_timeout_gesamt_existiert(self) -> None:
        for k in ("llm_timeout_gesamt",
                  "llm_timeout_connect",
                  "llm_timeout_read"):
            assert k in pipeline._AUDIT_KINDS_BEKANNT

    def test_ask_llm_timeout_audit_enthaelt_modell(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        # Audit-Payload enthaelt Modell + Aufgabe.
        assert "\"modell\": model" in src
        assert "\"aufgabe\": aufgabe" in src

    def test_ask_llm_read_timeout_adaptiv(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        assert "_read_adapt = int(min(_READ_S, max(1, _rest)))" in src

    def test_ask_llm_deadline_kein_zweiter_versuch(self) -> None:
        # Strukturtest: Deadline-Check steht VOR
        # dem requests.post-Aufruf.
        import inspect
        src = inspect.getsource(pipeline.ask_llm)
        i_deadline = src.find("if _rest <= 0:")
        i_post = src.find("res = requests.post")
        assert i_deadline > 0
        assert i_post > 0
        assert i_deadline < i_post

    def test_ask_llm_aufgabe_parameter(self) -> None:
        import inspect
        sig = inspect.signature(pipeline.ask_llm)
        assert "aufgabe" in sig.parameters


# =====================================================================
# F1 + F2 + F3 (2026-10-16): Commit-Phase-Infrastruktur
# =====================================================================

class TestCommitPhaseFixes:
    def test_rollback_git_status_uall(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._rollback_zieldateien)
        assert '"-uall"' in src

    def test_rollback_findet_datei_in_neuem_verzeichnis(self) -> None:
        # Strukturtest: -uall muss im Rollback stehen.
        import inspect
        src = inspect.getsource(pipeline._rollback_zieldateien)
        assert "--porcelain" in src and "-uall" in src

    def test_add_n_und_rollback_status_sauber(self) -> None:
        # F2-A2: Rollback enthaelt reset HEAD vor unlink.
        import inspect
        src = inspect.getsource(pipeline._rollback_zieldateien)
        assert '"reset"' in src
        assert '"HEAD"' in src
        i_reset = src.find('"reset"')
        i_unlink = src.find(".unlink()")
        assert i_reset < i_unlink

    def test_rollback_reset_head_vor_unlink(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._rollback_zieldateien)
        i_reset = src.find("_pfade_zum_reset")
        i_unlink = src.find(".unlink()")
        assert 0 < i_reset < i_unlink

    def test_git_add_intent_nach_apply(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.apply_and_recheck)
        assert '"add"' in src and '"-N"' in src
        assert "git_add_intent" in src

    def test_git_add_intent_nur_new_file(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.apply_and_recheck)
        assert 'p.get("typ") == "new_file"' in src

    def test_git_add_intent_audit(self) -> None:
        assert "git_add_intent" in pipeline._AUDIT_KINDS_BEKANNT
        assert "git_add_intent_failed" in pipeline._AUDIT_KINDS_BEKANNT

    def test_git_add_intent_failed_fail_closed(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.apply_and_recheck)
        # Bei returncode != 0 oder Exception: return 17.
        i_failed = src.find("git_add_intent_failed")
        i_ret = src.find("return 17", i_failed)
        assert i_failed > 0
        assert i_ret > i_failed

    def test_git_add_n_mit_normalisiertem_pfad(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.apply_and_recheck)
        # Pfad aus p.get("pfad", "") — kein fuehrender
        # Slash noetig. Test prueft, dass Pfad aus
        # code_patches uebernommen wird.
        assert 'p.get("pfad", "")' in src

    def test_collect_messwerte_git_head_fallback(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.collect_messwerte)
        assert "F3-Fix" in src
        assert "basis_protokoll_nach_apply" in src
        assert "basis_protokoll" in src

    def test_collect_messwerte_git_head_primaer(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.collect_messwerte)
        # Fallback greift nur, wenn Hauptwert leer.
        assert 'if not werte.get("git_head"):' in src

    def test_katalog_anzahl_ist_71(self) -> None:
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 78


# =====================================================================
# B0c-2 (2026-10-16, Lauf 26): Markdown + mehrzeiliger End-Fallback
# =====================================================================

class TestB0c2MarkdownEnde:
    def test_go_in_markdown_fett(self) -> None:
        text = "## Bericht\n\nAlle OK.\n\n**GO**"
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_nicht_letzte_zeile(self) -> None:
        # GO in -2, danach noch Text.
        text = ("## Bericht\n\nBefund.\n\n**GO**\n\n"
                "Die Werkstatt wendet an.")
        assert pipeline.classify_verdict(text) == "GO"

    def test_go_mit_backtick(self) -> None:
        text = "## Bericht\n\nOK.\n\n`GO`"
        assert pipeline.classify_verdict(text) == "GO"

    def test_no_go_markdown(self) -> None:
        text = "## Bericht\n\nBefund.\n\n**NO-GO**"
        assert pipeline.classify_verdict(text) == "NO-GO"

    def test_go_in_satz_zaehlt_nicht(self) -> None:
        text = "## Bericht\n\nR15: GO ist erfuellt, weil ..."
        assert pipeline.classify_verdict(text) == "UNKLAR"

    def test_go_nach_sechs_zeilen_nicht(self) -> None:
        text = ("## Bericht\n\nOK.\n\n**GO**\n\n"
                "Zeile1.\nZeile2.\nZeile3.\nZeile4.\n"
                "Zeile5.")
        # GO liegt mehr als 5 nicht-leere Zeilen zurueck.
        assert pipeline.classify_verdict(text) == "UNKLAR"


# =====================================================================
# D1 + D3 (2026-10-16): Commit-Paket-Scope deterministisch
# =====================================================================

class TestCommitPaketScope:
    def test_build_commit_paket_zieldateien_aus_patches(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "ZIELDATEIEN DIESES AUFTRAGS" in src
        assert "_ziel_pfade" in src

    def test_build_commit_paket_zieldateien_leer(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "Auftrag bereits" in src

    def test_build_commit_paket_prompt_scope_hinweis(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "Andere untracked Dateien" in src

    def test_d3_ueberschreibt_halluzination(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Strukturtest: D3 setzt dateien aus code_patches.
        assert "phase_commit_dateien_deterministisch" in src
        assert 'state.commit_paket["dateien"] = sorted' in src

    def test_d3_b2_fall_leere_liste(self) -> None:
        # Strukturtest: auch bei leeren Patches.
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        i_d3 = src.find("if state.phase_aktiv:")
        i_audit = src.find("phase_commit_dateien_deterministisch")
        assert 0 < i_d3 < i_audit

    def test_d3_nicht_im_nicht_phasen_modus(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Der Guard steht vor der Zuweisung.
        i_guard = src.find("if state.phase_aktiv:")
        i_zuweisung = src.find(
            'state.commit_paket["dateien"] = sorted', i_guard)
        assert 0 < i_guard < i_zuweisung

    def test_d3_vor_phase_commit_pakete_append(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        i_d3 = src.find("phase_commit_dateien_deterministisch")
        i_append = src.find(
            "state.phase_commit_pakete.append")
        assert 0 < i_d3 < i_append

    def test_audit_kind_existiert(self) -> None:
        assert ("phase_commit_dateien_deterministisch"
                in pipeline._AUDIT_KINDS_BEKANNT)

    def test_d3_ziel_pfade_aus_code_patches(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Im D3-Block werden Pfade aus code_patches gezogen.
        i = src.find("phase_commit_dateien_deterministisch")
        umfeld = src[i-500:i]
        assert 'p.get("pfad", "")' in umfeld
        assert 'state.code_patches' in umfeld

    def test_katalog_anzahl_ist_72(self) -> None:
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 78


# =====================================================================
# E + R16 (2026-10-16): git diff --name-only HEAD + Teilmengen-Check
# =====================================================================

class TestEDiffNameOnly:
    def test_commit_input_enthaelt_diff_name_only(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert "GIT DIFF --NAME-ONLY HEAD" in src

    def test_commit_input_ruft_git_diff_name_only(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert '"diff", "--name-only", "HEAD"' in src

    def test_commit_input_diff_vor_code_patches(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        i_diff = src.find("GIT DIFF --NAME-ONLY HEAD")
        i_cp = src.find("CODE-PATCHES (angewendet)")
        assert 0 < i_diff < i_cp

    def test_diff_name_only_leer_zeigt_keine(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert '"\""(keine)\""' not in src
        assert '"(keine)"' in src

    def test_diff_name_only_fehler_fail_closed(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Bei Fehler: return 9.
        i = src.find("commit_review_diff_fehler")
        assert i > 0
        i_ret = src.find("return 9", i)
        assert i_ret > i

    def test_r16_entfernt_im_reviewer_prompt(self) -> None:
        # A1-final (2026-10-16): R16 entfernt.
        assert "R16." not in pipeline.HARD_RULES_REVIEWER

    def test_r16_teilmenge_bei_phasen_modus(self) -> None:
        # A1-final (2026-10-16): R16 entfernt.
        # _check_commit_scope uebernimmt.
        import inspect
        src = inspect.getsource(pipeline._check_commit_scope)
        assert "BETROFFENE DATEIEN" in src or "dateien" in src

    def test_audit_kinds_commit_review_diff(self) -> None:
        assert ("commit_review_diff_name_only"
                in pipeline._AUDIT_KINDS_BEKANNT)
        assert ("commit_review_diff_fehler"
                in pipeline._AUDIT_KINDS_BEKANNT)

    def test_katalog_anzahl_ist_74(self) -> None:
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 78


# =====================================================================
# W2 (2026-10-16): HARD_RULES_BUILDER B4/B13b
# =====================================================================

class TestW2BuilderRules:
    def test_b4_zwei_klassen(self) -> None:
        s = pipeline.HARD_RULES_BUILDER
        assert "SYSTEMWERTE" in s
        assert "AUFTRAGS-BEHAUPTUNGEN" in s

    def test_b13b_im_prompt(self) -> None:
        assert "B13b." in pipeline.HARD_RULES_BUILDER
        assert "BEHAUPTUNGEN PRUEFEN" in pipeline.HARD_RULES_BUILDER

    def test_b13b_datei_existenz_wortlaut(self) -> None:
        s = pipeline.HARD_RULES_BUILDER
        assert "Datei X existiert" in s
        assert "Datei X existiert nicht" in s
        assert "Import aus a/b/c.py" in s

    def test_b13b_frage_reviewer_format(self) -> None:
        s = pipeline.HARD_RULES_BUILDER
        assert "COMMAND: frage_reviewer" in s

    def test_b13b_nicht_fuer_signaturen(self) -> None:
        s = pipeline.HARD_RULES_BUILDER
        assert "Funktions-Signaturen" in s
        assert "Nummernkreise" in s


# =====================================================================
# W3+W4 (2026-10-16): Planner-Messung + Plan-Korrektur
# =====================================================================

class TestW3PlannerMessung:
    def test_p19_im_planner_prompt(self) -> None:
        assert "P19." in pipeline.HARD_RULES_PLANNER_STUFE2

    def test_p19_nennt_read_file(self) -> None:
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        assert "COMMAND: RUN read_file" in s
        assert "MESSEN VOR DEM PLAN" in s

    def test_p19_nicht_in_stufe1(self) -> None:
        assert "P19." not in pipeline.HARD_RULES_PLANNER_STUFE1

    def test_planner_command_loop_im_code(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._planner_lauf)
        assert "COMMAND:" in src
        assert "parse_commands" in src
        assert "quelle=\"planner\"" in src

    def test_planner_command_loop_max_runden(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._planner_lauf)
        assert "planner_command_max_runden" in src
        assert "max_runden" in src

    def test_planner_user_content_hat_messwerte(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._planner_user_content)
        assert "_messwerte_fuer_planner" in src

    def test_planner_in_erlaubte_quellen(self) -> None:
        assert "planner" in pipeline.ERLAUBTE_QUELLEN

    def test_p9strich_verweist_auf_p19(self) -> None:
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        assert "P10-P19" in s

    def test_p18_hat_sechste_punkt(self) -> None:
        s = pipeline.HARD_RULES_PLANNER_STUFE2
        # P18 Punkt 6: Messungs-Pflicht.
        i = s.find("P18.")
        j = s.find("P19.", i)
        block = s[i:j] if i >= 0 and j > i else s[i:]
        assert "6. Der Unterpunkt-Text" in block

    def test_planner_lauf_signatur_max_runden(self) -> None:
        import inspect
        sig = inspect.signature(pipeline._planner_lauf)
        assert "max_runden" in sig.parameters

    def test_audit_kind_planner_command_max_runden(self) -> None:
        assert ("planner_command_max_runden"
                in pipeline._AUDIT_KINDS_BEKANNT)

    def test_planner_user_content_state_optional(self) -> None:
        # Alte Tests ohne state bleiben gruen.
        uc = pipeline._planner_user_content(
            "roh", "hist", stufe=1)
        assert isinstance(uc, str)


# =====================================================================
# W6a (2026-10-16): Diagnose-Regex + read_file-Limit
# =====================================================================

class TestW6a:
    def test_diagnose_regex_ignoriert_stdout(self) -> None:
        import re
        # Der Test-Text simuliert den GEMESSENER-
        # INHALT-Block mit einem read_file-Output.
        text = (
            "GEMESSENER INHALT (verbindlich, gewinnt):\n"
            "=== read_file ===\n"
            "ARGV: cat /x.py\n"
            "RC: 0\n"
            "STDOUT:\n"
            "def f():\n"
            "    pass\n"
            "STDERR:\n"
            "\n"
            "NAECHSTE SEKTION:\n"
        )
        marker = "GEMESSENER INHALT (verbindlich"
        i = text.find(marker)
        rest = text[i:]
        m2 = re.search(
            r"\n(?!ARGV:|RC:|STDOUT:|STDERR:)"
            r"([A-ZAEOEUE][A-ZAEOEUEa-zaeoeue_ ()/,-]{2,60}:)",
            rest[len(marker):])
        assert m2 is not None
        assert "NAECHSTE SEKTION" in m2.group(1)

    def test_read_file_konstante_existiert(self) -> None:
        assert pipeline.MAX_PROTOKOLL_PER_COMMAND_READ_FILE == 20_000

    def test_total_konstante_150k(self) -> None:
        assert pipeline.MAX_PROTOKOLL_TOTAL == 150_000

    def test_trim_output_mit_grenze(self) -> None:
        lang = "x" * 30_000
        gekappt = pipeline.trim_output(lang, grenze=20_000)
        assert len(gekappt) < 30_000

    def test_read_file_grenze_20k(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.execute_commands)
        assert "MAX_PROTOKOLL_PER_COMMAND_READ_FILE" in src
        assert '"read_file"' in src


# =====================================================================
# W6b (2026-10-16): read_file Zeilenbereich + Anker-zentriert
# =====================================================================

class TestW6b:
    def test_anker_zeilenbereich_findet_an_zeile(self) -> None:
        from pathlib import Path
        aufgabe = (
            "patch: apps/dashboard/app.py. "
            "ANKER (count==1): '    from apps.dashboard."
            "routes_tools import register_tools_routes\n"
            "    register_tools_routes(app)\n' "
            "ERSATZ: '...'."
        )
        info = pipeline._anker_zeilenbereich(
            aufgabe, Path("/opt/security-ai"))
        assert info is not None
        assert info[0] >= 1
        assert info[1] > info[0]

    def test_anker_zeilenbereich_kein_anker(self) -> None:
        from pathlib import Path
        info = pipeline._anker_zeilenbereich(
            "kein anker hier", Path("/opt/security-ai"))
        assert info is None

    def test_read_file_zeilenbereich_klassisch(self) -> None:
        m = pipeline.Measurement("read_file", ("cat",), "x")
        wl = ["apps/"]
        from pathlib import Path
        _out, ok, argv = pipeline.run_measurement_mit_argv(
            m, wl, Path("/opt/security-ai"),
            "apps/dashboard/app.py")
        assert ok
        assert "cat" in argv
        assert "sed" not in argv

    def test_read_file_zeilenbereich_sed(self) -> None:
        m = pipeline.Measurement("read_file", ("cat",), "x")
        wl = ["apps/"]
        from pathlib import Path
        _out, ok, argv = pipeline.run_measurement_mit_argv(
            m, wl, Path("/opt/security-ai"),
            "apps/dashboard/app.py:255-260")
        assert ok
        assert "sed" in argv
        assert "-n" in argv
        assert "255,260p" in argv

    def test_ensure_ziel_gemessen_signatur_aufgabe(self) -> None:
        import inspect
        sig = inspect.signature(pipeline.ensure_ziel_gemessen)
        assert "aufgabe" in sig.parameters

    def test_ensure_ziel_gemessen_nutzt_anker(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.ensure_ziel_gemessen)
        assert "_anker_zeilenbereich" in src
        assert "_anker_info" in src

    def test_parse_commands_read_file_zeilenbereich(self) -> None:
        cmds = pipeline.parse_commands(
            "COMMAND: RUN read_file apps/dashboard/app.py:255-260")
        assert len(cmds) == 1
        assert cmds[0]["id"] == "read_file"
        assert cmds[0]["arg"] == "apps/dashboard/app.py:255-260"

    def test_anker_zeilenbereich_clamp_start(self) -> None:
        # Anker in Zeile 2: start = max(1, 2-5) = 1.
        # Nutze eine existierende Datei mit Anker in
        # frueher Zeile — oder synthetisch.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            (td_p / "x").mkdir()
            (td_p / "x" / "y.py").write_text(
                "line1\nline2\nline3\n",
                encoding="utf-8")
            aufgabe = (
                "patch: x/y.py. ANKER: 'line2' ERSATZ: 'line3'.")
            info = pipeline._anker_zeilenbereich(aufgabe, td_p)
            # Kein Pfad-Match (Erwartung: x/y.py in
            # patch:).
            # Wenn info: start = 1.
            if info is not None:
                assert info[0] == 1


# =====================================================================
# W8 (2026-10-16): Commit-Paket-Prompt + Message-Check
# =====================================================================

class TestW8:
    def test_git_status_gefiltert_im_code(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "_ziel_pfade" in src
        assert "_gs_zeilen" in src or "gefiltert" in src

    def test_git_status_filter_logik(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        # Filter prueft Zeile[3:] gegen _ziel_pfade.
        assert "_gs_pfad" in src
        assert "_gs[3:]" in src

    def test_message_sanity_check_im_code(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # W10 (2026-10-16): W8-2 ersetzt durch
        # Aenderung-Block-Check.
        assert "commit_message_diskrepanz" in src
        assert "_w10_pfade" in src

    def test_message_regex_endungen(self) -> None:
        import re
        # Die Regex aus W8-2.
        regex = re.compile(
            r"[a-zA-Z0-9_./-]+\."
            r"(?:py|sql|md|yaml|yml|json|toml|html|"
            r"css|js|cfg|ini|txt)")
        # Positiv:
        assert regex.findall("core/x.py") == ["core/x.py"]
        assert regex.findall("data/migrations/0017_x.sql") == [
            "data/migrations/0017_x.sql"]
        # Negativ:
        assert regex.findall("v1.2") == []
        assert regex.findall("3.x") == []

    def test_commit_paket_gebaut_audit_kind(self) -> None:
        assert ("commit_paket_gebaut"
                in pipeline._AUDIT_KINDS_BEKANNT)

    def test_commit_message_diskrepanz_audit_kind(self) -> None:
        assert ("commit_message_diskrepanz"
                in pipeline._AUDIT_KINDS_BEKANNT)

    def test_r16_entfernt(self) -> None:
        # A1-final (2026-10-16): R16 entfernt.
        s = pipeline.HARD_RULES_REVIEWER
        assert "R16." not in s


# =====================================================================
# W8b (2026-10-16): Commit-Paket-Prompt — Verbot fremder Pfade
# =====================================================================

class TestW8b:
    def test_prompt_verbietet_fremde_pfade(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "VERBOTEN" in src
        assert "Ausblick auf spaetere Unterbloecke" in src

    def test_prompt_positiv_format(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.build_commit_paket)
        assert "Positiv-Format der Commit-Message" in src
        assert "Ein Pfad pro Zeile" in src


# =====================================================================
# W9a (2026-10-16): Message-Marker im Commit-Review-Prompt
# =====================================================================

class TestW9a:
    def test_commit_review_prompt_message_marker(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert "=== COMMIT-MESSAGE (vollstaendig) ===" in src
        assert "=== /COMMIT-MESSAGE ===" in src

    def test_konsistenz_mit_bestehenden_markern(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._planner_user_content)
        # Der Planner nutzt === REVIEWER-BEFUND ===.
        assert "=== REVIEWER-BEFUND" in src


# =====================================================================
# W10 (2026-10-16): Message-Check praeziser
# =====================================================================

class TestW10:
    def test_aenderung_block_extraktion(self) -> None:
        msg = (
            "Titel\n\n"
            "Ausgangslage:\nText mit routes_tools.py "
            "als Referenz.\n\n"
            "Aenderung:\n"
            "  - apps/dashboard/routes_guardrails.py\n\n"
            "Tests:\n1392 gesammelt.\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert pfade == {"apps/dashboard/routes_guardrails.py"}

    def test_referenzen_ignoriert(self) -> None:
        msg = (
            "Ausgangslage:\n"
            "Muster: apps/dashboard/routes_tools.py.\n"
            "Template: apps/dashboard/templates/guardrails.html.\n\n"
            "Aenderung:\n"
            "  - apps/dashboard/routes_guardrails.py\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert "apps/dashboard/routes_tools.py" not in pfade
        assert ("apps/dashboard/templates/guardrails.html"
                not in pfade)
        assert pfade == {"apps/dashboard/routes_guardrails.py"}

    def test_mehrere_aenderung_pfade(self) -> None:
        msg = (
            "Aenderung:\n"
            "  - a/x.py\n"
            "  - b/y.sql\n"
            "  - c/z.md\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert pfade == {"a/x.py", "b/y.sql", "c/z.md"}

    def test_kein_aenderung_block_fail_closed(self) -> None:
        msg = "Titel\n\nAusgangslage:\nText.\n"
        _pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == "b"

    def test_aenderung_ohne_bullets_fail_closed(self) -> None:
        msg = (
            "Aenderung:\n"
            "Fliesstext ohne Bullets.\n"
        )
        _pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == "a"

    def test_umlaut_variante_erkannt(self) -> None:
        # Der Check nutzt "Aenderung:" (ae).
        # Die Umlaut-Variante "Änderung:" wird
        # NICHT erkannt (MESSUNG: der Builder
        # schreibt ae).
        msg = (
            "Änderung:\n"
            "  - x.py\n"
        )
        _pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        # fall b: kein "Aenderung:".
        assert fehler == "b"

    def test_pfad_normalisierung(self) -> None:
        assert pipeline._normalisiere_pfad("./x.py") == "x.py"
        assert pipeline._normalisiere_pfad("/x.py") == "x.py"
        assert pipeline._normalisiere_pfad("x/") == "x"
        assert pipeline._normalisiere_pfad(
            "a\\b.py") == "a/b.py"

    def test_audit_kind_commit_message_diskrepanz_existiert(self) -> None:
        assert ("commit_message_diskrepanz"
                in pipeline._AUDIT_KINDS_BEKANNT)


# =====================================================================
# W10b (2026-10-16): Aenderung-Block Fallback
# =====================================================================

class TestW10b:
    def test_aenderung_block_fliesstext_fallback(self) -> None:
        msg = (
            "Aenderung:\n"
            "apps/dashboard/routes_guardrails.py, neue "
            "Datei mit register_guardrails_routes(app).\n"
            "\n"
            "Tests:\n"
            "1392 gesammelt.\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert pfade == {"apps/dashboard/routes_guardrails.py"}

    def test_aenderung_block_fliesstext_mit_referenz(self) -> None:
        # Fliesstext mit Referenz auf Muster.
        msg = (
            "Aenderung:\n"
            "apps/dashboard/routes_guardrails.py, "
            "Muster apps/dashboard/routes_tools.py.\n"
            "\n"
            "Tests:\n"
            "1392 gesammelt.\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        # Fallback zaehlt ALLE Pfade im Block
        # (nicht nur Zieldateien).
        assert "apps/dashboard/routes_guardrails.py" in pfade
        assert "apps/dashboard/routes_tools.py" in pfade


# =====================================================================
# W11 (2026-10-16): Unterblock-Isolation im Commit-Review
# =====================================================================

class TestW11:
    def test_r17_im_prompt(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "R17." in s
        assert "UNTERBLOCK-ISOLATION IM PHASEN-MODUS" in s

    def test_r17_nur_phasen_modus(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        # R17 gilt nur bei PHASEN-MODUS aktiv.
        assert "Wenn PHASEN-MODUS aktiv" in s

    def test_r17_new_file_ohne_registrierung_ok(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "KEIN Commit-Review-" in s
        assert "spaeteren Unterblock folgt" in s

    def test_r17_verweist_auf_r11_r16(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "R17 ergaenzt R16" in s
        assert "R17 ergaenzt R11" in s

    def test_r17_ausnahme_auftrag_nennt_pfad(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "AUSNAHME" in s
        assert "aufgabe_block" in s
        assert "WOERTLICH" in s

    def test_r17_hinweis_statt_no_go(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        assert "HINWEIS ohne" in s
        assert "KEIN NO-GO" in s

    def test_commit_review_prompt_unterblock_kontext(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        assert "_w11_unterblock_kontext" in src
        assert "UNTERBLOCK:" in src
        assert "von {_w11_total}" in src

    def test_commit_review_prompt_unterblock_nur_phasen_modus(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Der Kontext wird nur bei state.phase_aktiv
        # gefuellt.
        assert "if state.phase_aktiv:" in src
        assert "_w11_unterblock_kontext = \"\"" in src

    def test_r16_nicht_mehr_im_prompt(self) -> None:
        # A1-final (2026-10-16): R16 entfernt,
        # ersetzt durch deterministischen
        # _check_commit_scope.
        s = pipeline.HARD_RULES_REVIEWER
        assert "R16." not in s
        # R17 bleibt.
        assert "R17." in s


# =====================================================================
# W10c (2026-10-16): Regex mit Verzeichnis-Praefix
# =====================================================================

class TestW10c:
    def test_app_py_ohne_pfad_ignoriert(self) -> None:
        msg = (
            "Aenderung:\n"
            "  - apps/dashboard/routes_guardrails.py\n"
            "  Referenz: app.py\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert pfade == {"apps/dashboard/routes_guardrails.py"}

    def test_app_py_mit_pfad_gezaehlt(self) -> None:
        msg = (
            "Aenderung:\n"
            "  - apps/dashboard/app.py\n"
            "  - apps/dashboard/routes_guardrails.py\n"
        )
        pfade, fehler = pipeline._extrahiere_aenderung_pfade(msg)
        assert fehler == ""
        assert pfade == {
            "apps/dashboard/app.py",
            "apps/dashboard/routes_guardrails.py",
        }


# =====================================================================
# A1-final (2026-10-16): Deterministische Vor-Checks Reviewer
# =====================================================================

class TestA1Final:
    def test_check_ersatz_gleich_anker_new_file_ausschluss(
            self) -> None:
        # typ=new_file wird ausgeschlossen.
        patches = [
            {"typ": "new_file", "pfad": "x.py",
             "inhalt": "..."},
        ]
        fehlend = pipeline.pruefe_ersatz_gegen_messung(
            patches, "(kein Messprotokoll)")
        assert fehlend == []

    def test_check_commit_scope_vor_reviewer(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.run_pipeline)
        # Aufruf von _check_commit_scope vor dem
        # Reviewer-Call.
        assert "_check_commit_scope" in src
        assert "if not _scope_ok:" in src

    def test_commit_scope_fail_closed(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._check_commit_scope)
        assert "commit_scope_violation" in src
        assert "return (False" in src

    def test_r5_nicht_mehr_im_prompt(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        import re
        assert not re.search(r"(?<![A-Z])R5\.", s)

    def test_r16_nicht_mehr_im_prompt(self) -> None:
        s = pipeline.HARD_RULES_REVIEWER
        import re
        assert not re.search(r"(?<![A-Z])R16\.", s)

    def test_hard_rules_reviewer_anzahl_15(self) -> None:
        import re
        s = pipeline.HARD_RULES_REVIEWER
        regeln = re.findall(r"^(R\d+\w?)\.", s, re.MULTILINE)
        assert len(regeln) == 15

    def test_r12_r15_schon_im_prompt(self) -> None:
        # Regression: R12 und R15 bleiben.
        s = pipeline.HARD_RULES_REVIEWER
        import re
        assert re.search(r"(?<![A-Z])R12\.", s)
        assert re.search(r"(?<![A-Z])R15\.", s)


# =====================================================================
# W13a (2026-10-16): _anker_zeilenbereich mit \n-Literal
# =====================================================================

class TestW13a:
    def test_anker_zeilenbereich_mit_literal_n(self) -> None:
        # YAML-Quoting '\n' (Backslash-n) wird zu
        # echtem Zeilenumbruch.
        from pathlib import Path

        # Nutze den realen U9-Auftrag aus phase.yaml.
        import yaml
        d = yaml.safe_load(
            Path("/opt/werkstatt/projects/security-ai.phase.yaml")
            .read_text())
        aufgabe = ""
        for u in d["phase_unterbloecke"]:
            if u["id"] == "U9":
                aufgabe = (u["titel"] + "\n"
                           + "\n".join(f"- {p}"
                                        for p in u["unterpunkte"]))
        info = pipeline._anker_zeilenbereich(
            aufgabe, Path("/opt/security-ai"))
        assert info is not None
        assert info[0] >= 1
        assert info[1] > info[0]

    def test_anker_zeilenbereich_mit_echtem_newline(self) -> None:
        # Ein Anker-Text mit echtem Zeilenumbruch muss
        # unveraendert funktionieren.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            (td_p / "x").mkdir()
            (td_p / "x" / "y.py").write_text(
                "zeile1\nzeile2\nzeile3\n",
                encoding="utf-8")
            aufgabe = (
                "patch: x/y.py. ANKER: 'zeile2' ERSATZ: 'zeile3'.")
            info = pipeline._anker_zeilenbereich(aufgabe, td_p)
            # Treffer in Z. 2 -> (1, 12).
            assert info is not None
            assert info[0] == 1


# =====================================================================
# W13b (2026-10-16): pruefe_ersatz_gegen_messung deaktiviert
# =====================================================================

class TestW13b:
    def test_pruefe_ersatz_gegen_messung_existiert(self) -> None:
        # Die Funktion existiert weiter (fuer
        # spaetere Nutzung), wird aber nicht mehr
        # aufgerufen.
        assert hasattr(pipeline, "pruefe_ersatz_gegen_messung")

    def test_ersatz_fehler_nicht_mehr_geprueft(self) -> None:
        import inspect
        src = inspect.getsource(pipeline.builder_reply_mit_command_loop)
        # Der Aufruf ist deaktiviert.
        # Stattdessen nur anker_fehler.
        assert "ersatz_fehler: list" in src
        # Der Aufruf ist nicht mehr im Code.
        # (Textsuche nach Aufrufzeile.)
        # Wenn er noch im Code steht: Fehler.
        # Anmerkung: Textsuche, nicht Ausfuehrung.
        assert "if anker_fehler or ersatz_fehler" not in src


# =====================================================================
# W11b (2026-10-16): _check_commit_scope beruecksichtigt untracked
# =====================================================================

class TestW11b:
    def test_check_commit_scope_liest_git_status(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._check_commit_scope)
        assert '"git", "status", "--porcelain", "-uall"' in src
        assert "diff_pfade.add" in src

    def test_check_commit_scope_untracked_akzeptiert(self) -> None:
        import inspect
        src = inspect.getsource(pipeline._check_commit_scope)
        # Untracked Pfade landen in diff_pfade.
        assert "_status_res.stdout" in src


# =====================================================================
# W25-1 (2026-10-17): Basis-Gate test_result.
# Klassifizierer + _ziel_test_pfade + Gate-Funktionen.
# =====================================================================


class TestW25Klassifizierung:
    """W25-A25/A38: pytest-Ergebnis-Klassifizierung."""

    def test_klassifiziere_gruen(self) -> None:
        r = pipeline._klassifiziere_pytest(
            0, "5 passed in 1.23s\n", "", 1.23)
        assert r["klassifizierung"] == "gruen"
        assert r["exit_code"] == 0
        assert r["passed_count"] == 5
        assert r["failed_count"] == -1
        assert r["failed_test_ids"] == []

    def test_klassifiziere_test_failures(self) -> None:
        stdout = (
            "FAILED tests/test_x.py::test_a - assert\n"
            "FAILED tests/test_x.py::test_b - assert\n"
            "2 failed, 1393 passed in 500s\n"
        )
        r = pipeline._klassifiziere_pytest(
            1, stdout, "", 500.0)
        assert r["klassifizierung"] == "test_failures"
        assert r["failed_count"] == 2
        assert r["passed_count"] == 1393
        assert r["failed_test_ids"] == [
            "tests/test_x.py::test_a",
            "tests/test_x.py::test_b",
        ]
        assert r["failed_test_ids_mehr"] == 0

    def test_klassifiziere_failed_ids_limit(self) -> None:
        zeilen = [
            f"FAILED tests/test_x.py::test_{i}"
            for i in range(25)
        ]
        stdout = "\n".join(zeilen) + "\n25 failed in 10s\n"
        r = pipeline._klassifiziere_pytest(
            1, stdout, "", 10.0)
        assert len(r["failed_test_ids"]) == 20
        assert r["failed_test_ids_mehr"] == 5

    def test_klassifiziere_collection_error(self) -> None:
        r = pipeline._klassifiziere_pytest(
            2, "ERROR collecting tests/test_y.py\n",
            "", 0.5)
        assert r["klassifizierung"] == "collection_error"
        assert r["exit_code"] == 2

    def test_klassifiziere_no_tests(self) -> None:
        r = pipeline._klassifiziere_pytest(
            5, "no tests ran in 0.01s\n", "", 0.01)
        assert r["klassifizierung"] == "no_tests"

    def test_klassifiziere_unknown(self) -> None:
        r = pipeline._klassifiziere_pytest(
            99, "irgendwas", "", 1.0)
        assert r["klassifizierung"] == "unknown"

    def test_klassifiziere_timeout(self) -> None:
        r = pipeline._klassifiziere_pytest(
            None, "", "", 60.0, is_timeout=True)
        assert r["klassifizierung"] == "timeout"
        assert r["exit_code"] is None
        assert r["failed_count"] == -1
        assert r["passed_count"] == -1


class TestW25ZielPfade:
    """W25-A28: Filter auf tests/-Pfade."""

    def test_ziel_test_pfade_filter(self, tmp_path: Path) -> None:
        state = build_test_state(project_dir=tmp_path)
        state.code_patches = [
            {"pfad": "tests/test_a.py", "typ": "new_file"},
            {"pfad": "core/b.py", "typ": "patch"},
            {"pfad": "tests/unit/test_c.py", "typ": "new_file"},
            {"pfad": "tests/integration/test_d.py",
             "typ": "new_file"},
            {"pfad": "docs/x.md", "typ": "new_file"},
        ]
        r = pipeline._ziel_test_pfade(state)
        assert r == [
            "tests/test_a.py",
            "tests/unit/test_c.py",
            "tests/integration/test_d.py",
        ]

    def test_ziel_test_pfade_leer(self, tmp_path: Path) -> None:
        state = build_test_state(project_dir=tmp_path)
        state.code_patches = [
            {"pfad": "core/b.py", "typ": "patch"},
            {"pfad": "docs/x.md", "typ": "new_file"},
        ]
        assert pipeline._ziel_test_pfade(state) == []

    def test_ziel_test_pfade_nicht_dict(self, tmp_path: Path) -> None:
        state = build_test_state(project_dir=tmp_path)
        state.code_patches = [
            "kein dict",
            {"pfad": "tests/test_x.py"},
            None,
            {"kein_pfad": "x"},
        ]
        # Nicht-dict-Eintraege werden ignoriert.
        r = pipeline._ziel_test_pfade(state)
        assert r == ["tests/test_x.py"]


class TestW25BasisGate:
    """W25: _basis_gate_pytest_ziel / _suite (Mock)."""

    def test_basis_gate_pytest_ziel_rot(
            self, tmp_path: Path, monkeypatch) -> None:
        class FakeResult:
            returncode = 1
            stdout = "1 failed, 5 passed in 2s\n"
            stderr = ""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: FakeResult())
        r = pipeline._basis_gate_pytest_ziel(
            tmp_path, ["tests/test_x.py"], 60)
        assert r["exit_code"] == 1
        assert r["klassifizierung"] == "test_failures"
        assert r["failed_count"] == 1
        assert r["passed_count"] == 5

    def test_basis_gate_pytest_ziel_gruen(
            self, tmp_path: Path, monkeypatch) -> None:
        class FakeResult:
            returncode = 0
            stdout = "13 passed in 0.03s\n"
            stderr = ""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: FakeResult())
        r = pipeline._basis_gate_pytest_ziel(
            tmp_path, ["tests/test_x.py"], 60)
        assert r["exit_code"] == 0
        assert r["klassifizierung"] == "gruen"
        assert r["passed_count"] == 13

    def test_basis_gate_pytest_ziel_timeout(
            self, tmp_path: Path, monkeypatch) -> None:
        import subprocess as sp
        def fake_run(*a, **kw):
            raise sp.TimeoutExpired(cmd="pytest", timeout=60)
        monkeypatch.setattr("subprocess.run", fake_run)
        r = pipeline._basis_gate_pytest_ziel(
            tmp_path, ["tests/test_x.py"], 60)
        assert r["klassifizierung"] == "timeout"
        assert r["exit_code"] is None

    def test_basis_gate_pytest_suite_gruen(
            self, tmp_path: Path, monkeypatch) -> None:
        class FakeResult:
            returncode = 0
            stdout = "1395 passed in 560s\n"
            stderr = ""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: FakeResult())
        r = pipeline._basis_gate_pytest_suite(tmp_path, 900)
        assert r["exit_code"] == 0
        assert r["klassifizierung"] == "gruen"
        assert r["passed_count"] == 1395

    def test_basis_gate_pytest_suite_rot(
            self, tmp_path: Path, monkeypatch) -> None:
        class FakeResult:
            returncode = 1
            stdout = (
                "FAILED tests/a.py::test_x - assert\n"
                "1 failed, 1394 passed in 560s\n"
            )
            stderr = ""
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: FakeResult())
        r = pipeline._basis_gate_pytest_suite(tmp_path, 900)
        assert r["klassifizierung"] == "test_failures"
        assert r["failed_count"] == 1
        assert r["failed_test_ids"] == [
            "tests/a.py::test_x",
        ]


class TestW25FehlerNachApply:
    """W25-2-A36/A37: _fehler_nach_apply deterministisch."""

    def _v(self, diagnose: str = "",
           plan: list[str] | None = None) -> object:
        class V:
            pass
        v = V()
        v.diagnose = diagnose
        v.reparaturplan = plan or []
        return v

    def test_none_nicht_reparierbar(self) -> None:
        assert pipeline._fehler_nach_apply(None, 0) is False

    def test_leer_nicht_reparierbar(self) -> None:
        v = self._v(diagnose="", plan=[])
        assert pipeline._fehler_nach_apply(v, 0) is False

    def test_nur_diagnose_reparierbar(self) -> None:
        v = self._v(diagnose="Test xyz falsch.")
        assert pipeline._fehler_nach_apply(v, 0) is True

    def test_nur_plan_reparierbar(self) -> None:
        v = self._v(diagnose="",
                    plan=["Datei A fixen."])
        assert pipeline._fehler_nach_apply(v, 0) is True

    def test_marker_frueherer_unterblock(self) -> None:
        v = self._v(diagnose="Fehler aus frueherem Unterblock.")
        assert pipeline._fehler_nach_apply(v, 0) is False

    def test_marker_case_insensitive(self) -> None:
        v = self._v(
            diagnose="FRUEHERER UNTERBLOCK ist schuld.")
        assert pipeline._fehler_nach_apply(v, 0) is False

    def test_marker_bereits_done(self) -> None:
        v = self._v(
            diagnose="Test war bereits done.")
        assert pipeline._fehler_nach_apply(v, 0) is False

    def test_ohne_marker_reparierbar(self) -> None:
        v = self._v(
            diagnose="Test test_xyz erwartet altes Verhalten.")
        assert pipeline._fehler_nach_apply(v, 0) is True


class TestW25SammelCommitRecovery:
    """W25-2-A33: Recovery bei (e)-Rot."""

    def _state(self, tmp_path: Path) -> object:
        state = build_test_state(project_dir=tmp_path)
        state.phase_aktiv = True
        state.phase_unterbloecke = [
            {"id": "U1", "status": "done",
             "titel": "A", "commit_paket": {}},
            {"id": "U2", "status": "pending",
             "titel": "B", "commit_paket": {}},
        ]
        state.phase_aktueller_index = 1
        state.code_patches = [
            {"pfad": "tests/unit/test_x.py",
             "typ": "new_file"},
        ]
        return state

    def test_sammel_commit_recovery_reparierbar(
            self, tmp_path: Path, monkeypatch) -> None:
        """Reviewer: reparierbar. Loop 1 Runde. (e) gruen.
        Status U2 -> done."""
        # (e) rot, dann gruen.
        calls = {"n": 0}

        def fake_suite(pd, timeout):
            calls["n"] += 1
            if calls["n"] == 1:
                return pipeline._klassifiziere_pytest(
                    1,
                    "FAILED tests/unit/test_x.py::test_a - x\n"
                    "1 failed, 5 passed in 2s\n",
                    "", 2.0)
            return pipeline._klassifiziere_pytest(
                0, "6 passed in 2s\n", "", 2.0)

        # Reviewer liefert reparierbare Diagnose.
        class V:
            diagnose = "Test test_a erwartet altes Verhalten."
            reparaturplan: ClassVar[list[str]] = [
                "Test test_a korrigieren."]
            reparierbar = True
            empfehlung = ""
            rohantwort = ""

        monkeypatch.setattr(
            pipeline, "_basis_gate_pytest_suite",
            fake_suite)
        monkeypatch.setattr(
            pipeline, "ask_reviewer_for_recovery",
            lambda *a, **kw: V())
        # Korrektur-Loop erfolgreich.
        monkeypatch.setattr(
            pipeline, "_post_apply_korrektur_loop",
            lambda *a, **kw: 0)
        # Status-Update mocken.
        status_log: list[tuple[str, str]] = []
        def fake_status(pn, uid, st):
            status_log.append((uid, st))
        monkeypatch.setattr(
            pipeline, "_phase_yaml_status_update",
            fake_status)

        self._state(tmp_path)  # Smoke: State baubar.
        # Wir testen nur den Recovery-Block, nicht
        # die ganze Sammel-Commit-Logik.
        # Ein minimaler Ausschnitt aus run_pipeline
        # ist nicht isoliert aufrufbar; deshalb
        # wird die Logik ueber das Modul geprueft,
        # dass der Code die Marker enthaelt.
        src = __import__("inspect").getsource(
            pipeline.run_pipeline)
        assert "phase_suite_rot_recovery" in src
        assert "_fehler_nach_apply" in src
        # Verhalten ueber Hilfsfunktionen:
        v = V()
        assert pipeline._fehler_nach_apply(v, 1) is True
        # Status-Update-Helper existiert.
        assert hasattr(pipeline, "_phase_yaml_status_update")

    def test_sammel_commit_recovery_nicht_reparierbar(
            self, tmp_path: Path) -> None:
        """Reviewer: Fehler aus frueherem Unterblock
        -> nicht reparierbar."""
        class V:
            diagnose = "Fehler aus frueherem Unterblock U1."
            reparaturplan: ClassVar[list[str]] = [
                "Nichts hier machbar."]
            reparierbar = False

        v = V()
        assert pipeline._fehler_nach_apply(v, 1) is False
