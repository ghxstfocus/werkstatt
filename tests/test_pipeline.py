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
