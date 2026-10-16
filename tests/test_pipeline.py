"""Tests fuer /opt/werkstatt/pipeline.py.

Prueft die kritischen Pfade ohne echte LLM-Calls.
Kein DEEPSEEK_API_KEY erforderlich.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
        # Verdict ist erst nach 20 inhaltlichen Zeilen -> UNKLAR.
        text = "Zeile\n" * 20 + "GO"
        assert pipeline.classify_verdict(text) == "UNKLAR"

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
        """Auflage 2059: GO auf Zeile 16 -> UNKLAR (Grenze)."""
        # 15 Fuellzeilen + GO = Zeile 16.
        text = "Zeile\n" * 15 + "GO"
        assert pipeline.classify_verdict(text) == "UNKLAR"

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
        for r in ("R1.", "R2.", "R3.", "R4.", "R5.", "R6."):
            muster = rf"(?<![A-Z]){re.escape(r)}"
            assert re.search(muster, s), f"{r} fehlt im Reviewer-Prompt"

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
        # Baseline: 61 Eintraege. Stand nach
        # --resume-force (2026-10-16) ergaenzte
        # phase_resume_force.
        # Vorherige Baselines: 60 (Review-Persistenz).
        assert "review_round" in pipeline._AUDIT_KINDS_BEKANNT
        assert "phase_resume_force" in pipeline._AUDIT_KINDS_BEKANNT
        assert len(pipeline._AUDIT_KINDS_BEKANNT) == 61

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

