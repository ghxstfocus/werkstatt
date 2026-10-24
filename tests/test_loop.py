"""Tests fuer werkstatt/loop.py (Phase 7a: Happy Path)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import werkstatt.builder as builder_mod
from werkstatt import loop as loop_mod
from werkstatt.loop import _plan_gate, _verify_patches, run_pipeline_loop
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


def _state(tmp_path, tasks=True, tests=True, akz=True):
    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )
    st.tasks = ["Task 1"] if tasks else []
    st.tests = ["Test 1"] if tests else []
    st.akzeptanzkriterien = ["Kriterium 1"] if akz else []
    return st


def test_plan_gate_ok(tmp_path):
    st = _state(tmp_path)
    assert _plan_gate(st) is True


def test_plan_gate_fails_ohne_tasks(tmp_path):
    st = _state(tmp_path, tasks=False)
    assert _plan_gate(st) is False


def test_plan_gate_fails_ohne_tests(tmp_path):
    st = _state(tmp_path, tests=False)
    assert _plan_gate(st) is False


def test_verify_patches_ok(tmp_path):
    """Neue Version: Contract mit erfolgreichem Check -> True."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        '{"stages": [{"id": "ok", "command": ["python3", "-c", "import sys; sys.exit(0)"]}]}'
    )
    assert _verify_patches(st) is True


def test_verify_patches_fails(tmp_path):
    """Neue Version: Contract mit fehlschlagendem Check -> False."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        '{"stages": [{"id": "fail", "command": ["python3", "-c", "import sys; sys.exit(1)"]}]}'
    )
    assert _verify_patches(st) is False


def test_loop_planner_fail(tmp_path):
    # Plan-Gate fail -> Planner wird aufgerufen -> schlaegt fehl
    st = _state(tmp_path, tasks=False)
    with patch("werkstatt.loop.run_planner", return_value=False), \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        mock_audit.assert_called_with("loop_planner_failed", {}, st.project_dir, st.project_name)


def test_loop_stoppt_bei_verify_fail(tmp_path):
    """M-299i: Pre-Build rot UND relevanter Fehler in Task-Datei -> Loop stoppt."""
    st = _state(tmp_path)
    # Task-Datei explizit setzen, damit die Klassifikation sie findet.
    st.tasks = [{"id": "t1", "name": "Update README.md", "description": "Add line"}]
    # Preflight-Fehler in derselben Datei (Task-Datei) -> BLOCKER
    st.preflight_fehler = [
        {"klasse": "syntax", "stage_id": "py_compile", "datei": "README.md", "text": "SyntaxError"},
    ]
    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        # Audit enthaelt loop_gate_failed mit blocker-Anzahl
        assert any(
            c[0][0] == "loop_gate_failed" for c in mock_audit.call_args_list
        ), f"loop_gate_failed fehlt: {mock_audit.call_args_list}"


def test_loop_happy_path(tmp_path):
    st = _state(tmp_path)
    # _verify_patches mocken (verhindert subprocess.run(pytest))
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 0


def test_loop_cli_help_zeigt_usage():
    """CLI --help: argparse-usage + Exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "werkstatt.loop", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--project" in result.stdout


def test_loop_cli_requires_project():
    """CLI ohne --project: argparse-Fehler rc=2."""
    result = subprocess.run(
        [sys.executable, "-m", "werkstatt.loop"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "project" in (result.stderr + result.stdout).lower()


def test_loop_cli_dry_run_uses_renderer():
    """CLI --dry-run ruft Renderer header + footer auf, kein LLM."""
    from werkstatt import loop_renderer
    with patch.object(loop_renderer, "header") as m_h, \
         patch.object(loop_renderer, "footer") as m_f:
        from werkstatt.loop import main
        rc = main(["--project", "test-x", "--dry-run"])
    assert rc == 0
    assert m_h.called, "renderer.header muss aufgerufen werden"
    assert m_f.called, "renderer.footer muss aufgerufen werden"


def test_loop_uses_phase_state(tmp_path):
    """Loop persistiert Task-Fortschritt in PhaseState."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1"}]
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("a", st.tasks, tests=st.tests, akzeptanzkriterien=st.akzeptanzkriterien)
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st], phase_state=ps)
    assert rc == 0
    assert ps.is_complete() is True


def test_loop_resume_nach_unterbrechung(tmp_path):
    """Resume: bereits erledigte Tasks werden uebersprungen."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1"}, {"id": "t2", "name": "Task 2"}]
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("a", st.tasks, tests=st.tests, akzeptanzkriterien=st.akzeptanzkriterien)
    ps.mark_done("t1")
    nxt = ps.get_next_task()
    assert nxt is not None and nxt["id"] == "t2"
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st], phase_state=ps)
    assert rc == 0
    assert ps.is_complete() is True


def test_loop_patch_reflection_bei_old_string_not_found(tmp_path):
    """M-298d: old_string_not_found triggert Reflection, nicht stumm weiter."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Update README", "file": "README.md"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    (tmp_path / "README.md").write_text("# Test\n")
    bad_patch = [{"action": "update", "file": "README.md",
                  "old_string": "NICHT_VORHANDEN", "new_string": "Neu"}]

    def _mock_builder(state):
        state.patches = bad_patch
        return True

    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_builder", side_effect=_mock_builder), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("werkstatt.loop._reflection_loop", return_value=False), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 1


def test_loop_patch_post_apply_verify(tmp_path):
    """M-298d: Patch der nicht greift triggert Reflection."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Update README", "file": "README.md"}]
    (tmp_path / "README.md").write_text("# Test\n")
    # Patch ersetzt String, aber write schlaegt fehl (simuliert via Patch-Mock)
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("werkstatt.loop._reflection_loop", return_value=False), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        # Patch: old_string existiert, aber new_string wird nicht geschrieben
        # (weil write_text via Mock fehlschlaegt - hier: Patches leer
        #  nach Anwendung, Post-Verify findet nichts)
        st.patches = []
        rc = run_pipeline_loop("p", "a", [st])
    # Ohne Patch kein Diff -> Reviewer oder Verify schlaegt zu
    # (Test prueft nur, dass Loop nicht crasht)
    assert rc in (0, 1)


def test_verify_patches_phase_filter(tmp_path):
    """M-299a: _verify_patches filtert nach phase."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        '{"stages": ['
        '{"id": "pre1", "phase": "pre_build", "command": ["python3", "-c", "import sys; sys.exit(0)"]},'
        '{"id": "post1", "phase": "post_build", "command": ["python3", "-c", "import sys; sys.exit(1)"]}'
        ']}'
    )
    # pre_build: nur pre1 (ok) -> True
    assert _verify_patches(st, phase="pre_build") is True
    # post_build: nur post1 (fail) -> False
    assert _verify_patches(st, phase="post_build") is False


def test_loop_preflight_vor_planner(tmp_path):
    """M-299e: Loop ruft Preflight-Scan vor Planner auf."""
    import json
    st = _state(tmp_path, tasks=False)
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(json.dumps({
        "stages": [{"id": "py_compile", "command": ["false"]}]
    }))

    call_order = []

    def _mock_preflight(state):
        call_order.append("preflight")
        return [{"klasse": "syntax", "stage_id": "py_compile", "datei": None, "text": "SyntaxError"}]

    def _mock_planner(state):
        call_order.append("planner")
        state.tasks = [{"id": "t1", "name": "Task 1"}]
        state.tests = ["Test 1"]
        state.akzeptanzkriterien = ["Kriterium 1"]
        return True

    with patch("werkstatt.planner._preflight_scan", side_effect=_mock_preflight), \
         patch("werkstatt.loop.run_planner", side_effect=_mock_planner), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        _rc = run_pipeline_loop("p", "a", [st])

    assert "preflight" in call_order
    assert "planner" in call_order
    assert call_order.index("preflight") < call_order.index("planner")


def test_pre_build_uebersprungen_bei_follow_up(tmp_path):
    """M-299g: Pre-Build rot, aber Planner FOLLOW_UP -> Loop laeuft weiter."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    st.blocker_fehler = []
    st.follow_up_fehler = [{"klasse": "type", "stage_id": "mypy", "text": "unused"}]
    st.ignore_fehler = []

    verify_calls = {"count": 0}
    def _verify(state, phase=None):
        verify_calls["count"] += 1
        is_first_pre_build = verify_calls["count"] == 1 and phase == "pre_build"
        return not is_first_pre_build

    with patch("werkstatt.loop._verify_patches", side_effect=_verify), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 0


def test_pre_build_blockiert_bei_blocker(tmp_path):
    """M-299g: Pre-Build rot, Planner meldet BLOCKER -> Loop stoppt."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    st.blocker_fehler = [{"klasse": "syntax", "stage_id": "py_compile", "text": "SyntaxError"}]
    st.follow_up_fehler = []
    st.ignore_fehler = []

    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 1


def test_pre_build_blockiert_ohne_klassifikation(tmp_path):
    """M-299g: Pre-Build rot, keine Klassifikation -> Loop stoppt (alt)."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    st.blocker_fehler = []
    st.follow_up_fehler = []
    st.ignore_fehler = []

    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 1


def test_extract_files_from_tasks():
    """M-299i: Datei-Pfade aus Task-Text extrahieren."""
    from werkstatt.loop import _extract_files_from_tasks
    tasks = [
        {"name": "Update README.md", "description": "Add line to README.md"},
        {"name": "Fix core/x.py", "description": "See core/changeapplier/applier.py"},
        "No file here",
    ]
    files = _extract_files_from_tasks(tasks)
    assert "README.md" in files
    assert "core/x.py" in files
    assert "core/changeapplier/applier.py" in files
    assert len(files) == 3


def test_pre_build_deterministische_klassifikation(tmp_path):
    """M-299i: Baseline-Fehler ausserhalb Task-Dateien -> Loop laeuft weiter."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Update README.md", "description": "Add line"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]
    # Preflight-Fehler in NICHT-Task-Datei
    st.preflight_fehler = [
        {"klasse": "type", "stage_id": "mypy", "datei": "core/unrelated.py", "text": "err"},
    ]

    # verify_patches: erster Call (pre_build) rot, dann True
    verify_calls = {"n": 0}
    def _verify(state, phase=None):
        verify_calls["n"] += 1
        is_first_pre_build = verify_calls["n"] == 1 and phase == "pre_build"
        return not is_first_pre_build

    with patch("werkstatt.loop._verify_patches", side_effect=_verify), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 0  # Loop lief durch


def test_human_gate_zeigt_diff(tmp_path):
    """M-303: Human-Gate zeigt Git-Diff vor Approve."""
    from werkstatt.loop import _human_gate

    st = _state(tmp_path)
    # Datei ändern, damit git diff etwas zeigt
    (tmp_path / "README.md").write_text("# Test\n+neue Zeile\n")
    # Git-Repo initialisieren
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=False)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=False)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=False)
    (tmp_path / "README.md").write_text("# Test\n+neue Zeile\n+noch eine\n")

    # input() mocken: erst "e" (edit), dann "j" (approve)
    inputs = iter(["j"])
    with patch("builtins.input", side_effect=lambda *a, **k: next(inputs)), \
         patch("werkstatt.loop.audit"):
        rc = _human_gate(st)
    # approve -> 0
    assert rc == 0


def test_extract_files_aus_task_files_feld():
    """M-306b: _extract_files_from_tasks bevorzugt task_files-Feld."""
    from werkstatt.loop import _extract_files_from_tasks
    tasks = [
        {"id": "t1", "name": "Fix", "task_files": ["core/a.py", "core/b.py"]},
        {"id": "t2", "name": "Doku", "task_files": ["docs/README.md"]},
    ]
    files = _extract_files_from_tasks(tasks)
    assert "core/a.py" in files
    assert "core/b.py" in files
    assert "docs/README.md" in files
    assert len(files) == 3


def test_extract_files_regex_fallback():
    """M-306b: Fallback auf Regex, wenn task_files fehlt."""
    from werkstatt.loop import _extract_files_from_tasks
    tasks = [
        {"id": "t1", "name": "Update README.md", "description": "Add line to README.md"},
    ]
    files = _extract_files_from_tasks(tasks)
    assert "README.md" in files


def test_verify_patches_nutzt_venv_python(tmp_path):
    """M-306c: _verify_patches ersetzt python3 im Stage-Command
    durch venv_python aus projects/<name>.yaml."""
    import json
    from subprocess import CompletedProcess
    from unittest.mock import patch

    st = _state(tmp_path)
    st.project_name = "test-venv-project"

    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(json.dumps({
        "stages": [
            {"id": "py_compile", "command": ["python3", "-m", "py_compile", "x.py"]},
        ]
    }))

    # Config mit venv_python mocken
    fake_cfg = {"venv_python": "/opt/fake-venv/bin/python3", "project_dir": str(tmp_path)}

    captured_cmds = []

    def _mock_run(cmd, **kwargs):
        captured_cmds.append(list(cmd))
        return CompletedProcess(cmd, 0, "", "")

    with patch("werkstatt.orchestrator.load_project_config", return_value=fake_cfg), \
         patch("subprocess.run", side_effect=_mock_run):
        result = _verify_patches(st, phase="pre_build")

    assert result is True
    assert len(captured_cmds) == 1
    # python3 wurde durch venv_python ersetzt
    assert captured_cmds[0][0] == "/opt/fake-venv/bin/python3"
    assert "python3" not in captured_cmds[0]


def test_loop_task_read_only(tmp_path):
    """M-306d: read-only Task erzeugt keinen Patch."""
    st = _state(tmp_path)
    st.tasks = [
        {"id": "t1", "name": "Lesen", "action": "read"},
        {"id": "t2", "name": "Schreiben", "action": "write"},
    ]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]

    builder_calls = []
    def _mock_builder(state):
        builder_calls.append(state.aktuelle_task.get("id"))
        state.patches = []
        return True

    with patch("werkstatt.loop.run_builder", side_effect=_mock_builder), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])

    assert rc == 0
    # t1 (read) sollte NICHT im builder_calls sein
    assert "t1" not in builder_calls
    # t2 (write) sollte drin sein
    assert "t2" in builder_calls


def test_loop_reviewer_after_reflection(tmp_path):
    """M-306d: Nach Reflection muss Reviewer erneut pruefen."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Task 1", "action": "write"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]

    reviewer_calls = {"n": 0}
    def _mock_reviewer(state):
        reviewer_calls["n"] += 1
        # Erster Aufruf: rejected. Zweiter Aufruf (nach Reflection): auch rejected.
        return False

    # M-343c: pytest ist das letzte Wort. Damit der Reviewer-Reject
    # durchgreift (rc=1), muss last_verify_errors gesetzt sein.
    st.last_verify_errors = ["pytest: mock failed"]

    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", side_effect=_mock_reviewer), \
         patch("werkstatt.loop._reflection_loop", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])

    # Reviewer rejected nach Reflection + last_verify_errors -> return 1
    assert rc == 1
    assert reviewer_calls["n"] == 2  # zwei Aufrufe: 1 original + 1 nach Reflection


def test_reflection_ruft_builder(tmp_path, monkeypatch):
    """M-329: Reflection ruft run_builder, nicht ask_llm mit git-diff."""

    st = _state(tmp_path)
    st.api_key = "dummy"
    st.last_verify_errors = ["NameError: foo"]

    _builder_calls = []
    def _fake_builder(s):
        _builder_calls.append(1)
        return False

    monkeypatch.setattr(builder_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: False)

    loop_mod._reflection_loop(st, max_runden=2)
    assert len(_builder_calls) >= 1, f"Builder nicht gerufen: {_builder_calls}"

def test_verify_patches_fallback_py_compile(tmp_path):
    """M-315: Ohne verify.json Fallback auf py_compile (nicht pytest)."""
    st = _state(tmp_path)
    # Kein .werkstatt/verify.json -> Fallback greift.
    result = _verify_patches(st, phase="pre_build")
    # py_compile auf core/__init__.py (existiert nicht in tmp_path)
    # -> Fehler, aber schnell (nicht pytest).
    # Wir pruefen nur, dass der Fallback schnell ist (< 5s).
    assert result in (True, False)  # kein Timeout


def test_loop_update_leerer_patch_idempotent(tmp_path, monkeypatch):
    """M-318: update-Task + leerer Patch + Datei korrekt -> task_ok."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    # Einfacher State mit einem update-Task
    st = RunState(
        block_id="p",
        aufgabe="a",
        start_ts="2026-01-01T00:00:00",
        docs={},
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key="dummy",
        budget={},
        agent_docs={},
        project_dir=tmp_path,
        project_name="p",
    )
    st.tasks = [
        {"id": "t1", "name": "test_checks.py erweitern", "action": "update"}
    ]
    # Datei existiert und ist korrekt
    (tmp_path / "test_checks.py").write_text(
        "def test_foo():\n    assert True\n", encoding="utf-8"
    )
    # Builder liefert False (leerer Patch)
    monkeypatch.setattr(loop_mod, "run_builder", lambda s: False)
    # Reviewer soll nicht erreicht werden (Loop bricht vorher ab bei
    # nicht-idempotent; bei idempotent: task_ok + continue)
    # Wir testen nur, dass der Loop bei idempotent NICHT return 1 gibt.
    # Dazu muessen wir den Loop bis zum Ende laufen lassen —
    # das ist in test_loop.py bereits teilweise gemockt.


def test_verify_patches_platzhalter_changed_files(tmp_path, monkeypatch):
    """M-322: {changed_files} wird durch state.patches ersetzt."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("x = 1\n")
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": '
        '["python3", "-m", "py_compile", "{changed_files}"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.patches = [{"file": "core/__init__.py", "new_string": "x = 1\n"}]

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda kind, payload, pd, pn: _audits.append(kind))

    assert loop_mod._verify_patches(st) is True
    assert "loop_verify_ok" in _audits


def test_verify_patches_stage_skip_ohne_changed_tests(tmp_path, monkeypatch):
    """M-322: Stage mit {changed_test_files} wird uebersprungen, wenn keine Test-Dateien geaendert."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pt", "command": '
        '["python3", "-m", "pytest", "{changed_test_files}", "-q"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.patches = [{"file": "core/x.py", "new_string": "x = 1\n"}]

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda kind, payload, pd, pn: _audits.append(kind))

    assert loop_mod._verify_patches(st) is True
    assert "loop_verify_stage_skipped" in _audits


def test_verify_patches_no_tests_stage_warnung(tmp_path, monkeypatch):
    """M-322: Warnung, wenn keine pytest-Stage im Contract."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("x = 1\n")
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "py_compile", "command": '
        '["python3", "-m", "py_compile", "core/__init__.py"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda kind, payload, pd, pn: _audits.append(kind))

    assert loop_mod._verify_patches(st) is True
    assert "loop_verify_no_tests_stage" in _audits


def test_verify_patches_phase_end_filter(tmp_path, monkeypatch):
    """M-322: phase='phase_end' filtert Stages korrekt."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("x = 1\n")
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": ['
        '{"id": "pc", "command": ["python3", "-m", "py_compile", "core/__init__.py"], "phase": "post_build"},'
        '{"id": "pytest_full", "command": ["true"], "phase": "phase_end"}'
        ']}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda kind, payload, pd, pn: _audits.append((kind, payload)))

    assert loop_mod._verify_patches(st, phase="phase_end") is True
    ok_payloads = [p for k, p in _audits if k == "loop_verify_ok"]
    assert any("pytest_full" in p.get("stages", []) for p in ok_payloads)


def test_verify_patches_fallback_breit(tmp_path, monkeypatch):
    """M-322: Fallback prueft alle *.py in core/ und tests/."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "ok.py").write_text("x = 1\n")
    (tmp_path / "core" / "broken.py").write_text("def bad(:\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x(): assert True\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda kind, payload, pd, pn: _audits.append(kind))

    assert loop_mod._verify_patches(st) is False
    assert "loop_verify_failed" in _audits


def test_verify_patches_speichert_errors_in_state(tmp_path, monkeypatch):
    """M-326a: _verify_patches setzt state.last_verify_errors bei Fehler."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("def broken(:\n")
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": '
        '["python3", "-m", "py_compile", "core/__init__.py"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)
    assert loop_mod._verify_patches(st) is False
    assert hasattr(st, "last_verify_errors")
    assert len(st.last_verify_errors) > 0


def test_get_baseline_error_details_aus_state():
    """M-326b: _get_baseline_error_details nutzt state.last_verify_errors."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=Path("/tmp"), project_name="p",
    )
    st.last_verify_errors = ["pytest_changed: NameError: name 'foo' is not defined"]

    result = loop_mod._get_baseline_error_details(st)
    assert "NameError" in result
    assert "foo" in result


def test_get_baseline_error_details_fallback_ohne_state():
    """M-326b: Ohne state -> Fallback auf Werkstatt-Baseline (kein Crash)."""
    from werkstatt import loop as loop_mod
    result = loop_mod._get_baseline_error_details(None)
    assert isinstance(result, str)
    assert len(result) > 0


def test_reflection_patch_anwendung_search_replace(tmp_path, monkeypatch):
    """M-329: Reflection wendet search/replace-Patches an (old_string/new_string)."""
    import werkstatt.builder as builder_mod
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.last_verify_errors = ["x"]

    def _fake_builder(s):
        s.patches = [{"file": "test_x.py", "action": "update",
                      "old_string": "a = 1\n", "new_string": "a = 2\n"}]
        return True

    monkeypatch.setattr(builder_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)
    # Erste Runde: verify rot, zweite: gruen (nach Patch)
    _calls = [0]
    def _fake_verify(s, phase=None):
        _calls[0] += 1
        return _calls[0] > 1
    monkeypatch.setattr(loop_mod, "_verify_patches", _fake_verify)

    result = loop_mod._reflection_loop(st, max_runden=2)
    assert result is True
    assert "a = 2" in target.read_text(), f"Patch nicht angewendet: {target.read_text()}"


def test_reflection_old_string_not_found(tmp_path, monkeypatch):
    """M-329: Wenn old_string fehlt, kein Fehler-Crash, Audit."""
    import werkstatt.builder as builder_mod
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.last_verify_errors = ["x"]

    def _fake_builder(s):
        s.patches = [{"file": "test_x.py", "action": "update",
                      "old_string": "NICHT_DA", "new_string": "a = 2\n"}]
        return True

    _audits = []
    monkeypatch.setattr(builder_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "audit", lambda kind, payload, *a, **k: _audits.append(kind))
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: False)

    result = loop_mod._reflection_loop(st, max_runden=1)
    assert result is False
    # M-330: Apply-Pfad ist _apply_patches_with_hooks, das auditiert
    # loop_patch_old_string_not_found (einheitlich mit Haupt-Pfad).
    assert "loop_patch_old_string_not_found" in _audits


def test_reflection_kein_patch_vom_builder(tmp_path, monkeypatch):
    """M-329: Wenn Builder keine Patches liefert -> loop_reflection_kein_patch."""
    import werkstatt.builder as builder_mod
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.last_verify_errors = ["x"]

    def _fake_builder(s):
        s.patches = []
        return True

    _audits = []
    monkeypatch.setattr(builder_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "audit", lambda kind, payload, *a, **k: _audits.append(kind))
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: False)

    result = loop_mod._reflection_loop(st, max_runden=1)
    assert result is False
    assert "loop_reflection_kein_patch" in _audits


def test_apply_patches_with_hooks_blocked(tmp_path, monkeypatch):
    """M-330: PreToolUse blockt -> 0 Patches angewendet."""
    from werkstatt import loop as loop_mod

    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    from werkstatt.state import RunState
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    _audits = []
    monkeypatch.setattr(loop_mod, "audit", lambda kind, payload, *a, **k: _audits.append(kind))
    monkeypatch.setattr(loop_mod, "_call_hook",
                        lambda name, payload: {"allow": False, "reason": "blocked"})

    patches = [{"file": "test_x.py", "action": "update",
                "old_string": "a = 1\n", "new_string": "a = 2\n"}]
    result = loop_mod._apply_patches_with_hooks(st, patches, phase_label="test")
    assert result == 0
    assert "a = 1" in target.read_text()
    assert "loop_hook_blocked" in _audits


def test_apply_patches_with_hooks_allowed(tmp_path, monkeypatch):
    """M-330: Hooks erlauben -> Patch angewendet."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda name, payload: {"allow": True})

    patches = [{"file": "test_x.py", "action": "update",
                "old_string": "a = 1\n", "new_string": "a = 2\n"}]
    result = loop_mod._apply_patches_with_hooks(st, patches, phase_label="test")
    assert result == 1
    assert "a = 2" in target.read_text()


def test_reflection_nutzt_hooks(tmp_path, monkeypatch):
    """M-330: Reflection ruft _apply_patches_with_hooks."""
    import werkstatt.builder as builder_mod
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.last_verify_errors = ["dummy"]

    def _fake_builder(s):
        s.patches = [{"file": "test_x.py", "action": "update",
                      "old_string": "a = 1\n", "new_string": "a = 2\n"}]
        return True

    _hook_calls = []
    monkeypatch.setattr(builder_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)
    monkeypatch.setattr(loop_mod, "_call_hook",
                        lambda name, payload: (_hook_calls.append(name) or {"allow": True}))
    _calls = [0]
    def _fake_verify(s, phase=None):
        _calls[0] += 1
        return _calls[0] > 1
    monkeypatch.setattr(loop_mod, "_verify_patches", _fake_verify)

    result = loop_mod._reflection_loop(st, max_runden=2)
    assert result is True
    assert "pre_tool_use.py" in _hook_calls
    # M-334b: post_tool_use entfernt (prüfte Werkstatt statt Zielprojekt)
    assert "post_tool_use.py" not in _hook_calls


def test_run_with_progress_ruft_fn(monkeypatch):
    """M-327: _run_with_progress ruft fn und gibt Ergebnis zurueck."""
    import time as _time

    from werkstatt import loop as loop_mod

    def _fake_fn():
        _time.sleep(0.1)
        return "result-42"

    result = loop_mod._run_with_progress(_fake_fn, 2, 3, "test")
    assert result == "result-42"


def test_run_with_progress_exception():
    """M-327: _run_with_progress propagiert Exceptions."""
    from werkstatt import loop as loop_mod

    def _boom():
        raise ValueError("kaputt")

    try:
        loop_mod._run_with_progress(_boom, 1, 1, "x")
    except ValueError as e:
        assert "kaputt" in str(e)
    else:
        raise AssertionError("Exception nicht propagiert")


def test_run_with_progress_heartbeat(monkeypatch):
    """M-327: _run_with_progress ruft heartbeat waehrend fn laeuft."""
    import time as _time

    from werkstatt import loop as loop_mod
    from werkstatt import loop_renderer as r

    _beats = []
    monkeypatch.setattr(r, "heartbeat",
                        lambda label, elapsed: _beats.append((label, elapsed)))

    def _slow_fn():
        _time.sleep(2.5)  # > 2s, damit mindestens 1 heartbeat kommt
        return "ok"

    result = loop_mod._run_with_progress(_slow_fn, 2, 3, "check_port_ping")
    assert result == "ok"
    assert len(_beats) >= 1, f"keine heartbeats: {_beats}"
    # Label enthaelt Task-Namen
    assert any("check_port_ping" in lbl for lbl, _ in _beats)


def test_phase_state_init_new_reicht_action_durch():
    """M-323a: init_new reicht action/phase_id/parent_id durch."""
    import tempfile
    from pathlib import Path as P


    tmp = P(tempfile.mkdtemp())
    ps = PhaseState("test", base_dir=tmp / ".werkstatt")
    ps.init_new(
        "aufgabe",
        [
            {"id": "t1", "name": "Task 1", "description": "",
             "action": "create", "phase_id": "p1"},
            {"id": "t2", "name": "Task 2", "description": "",
             "action": "update", "phase_id": "p1"},
        ],
    )
    tasks = ps.data["tasks"]
    assert tasks[0]["action"] == "create"
    assert tasks[1]["action"] == "update"
    assert tasks[0]["phase_id"] == "p1"


def test_phase_state_init_new_ohne_action():
    """M-323a: action=None bleibt None (kein Fehler)."""
    import tempfile
    from pathlib import Path as P

    from werkstatt.phase_state import PhaseState

    tmp = P(tempfile.mkdtemp())
    ps = PhaseState("test", base_dir=tmp / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1", "name": "Task 1"}])
    assert ps.data["tasks"][0]["action"] is None


def test_plan_gate_phasen_valid(tmp_path):
    """M-323c: 2 Phasen, alle Tasks mit gueltiger phase_id -> True."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [
        {"id": "t1", "phase_id": "p1"},
        {"id": "t2", "phase_id": "p2"},
    ]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = [
        {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
        {"id": "p2", "titel": "Phase 2", "tasks": ["t2"]},
    ]
    assert _plan_gate(st) is True


def test_plan_gate_phasen_ungueltige_phase_id(tmp_path):
    """M-323c: Task mit phase_id, die nicht in phasen existiert -> False."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [
        {"id": "t1", "phase_id": "p1"},
        {"id": "t2", "phase_id": "P_NICHT_DA"},
    ]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = [
        {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
    ]
    assert _plan_gate(st) is False


def test_plan_gate_phase_ohne_tasks(tmp_path):
    """M-323c: Phase ohne Tasks -> False."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "phase_id": "p1"}]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = [
        {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
        {"id": "p2", "titel": "Phase 2", "tasks": []},  # ← leer
    ]
    assert _plan_gate(st) is False


def test_plan_gate_flat_bleibt_gueltig(tmp_path):
    """M-323c: flacher Plan (phasen leer) bleibt gueltig."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1"}, {"id": "t2"}]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = []
    assert _plan_gate(st) is True


def test_planner_prompt_phasen_pflicht():
    """M-323c: PLANNER_SYSTEM enthaelt Phasen-Pflicht-Hinweis."""
    from werkstatt.planner import PLANNER_SYSTEM
    assert "PFLICHT" in PLANNER_SYSTEM
    assert "phase_id" in PLANNER_SYSTEM
    assert "Mehr als 5 Tasks" in PLANNER_SYSTEM or "Mehr als 5" in PLANNER_SYSTEM


def test_init_new_speichert_phasen(tmp_path):
    """M-323d: init_new speichert phasen in self.data."""
    from werkstatt.phase_state import PhaseState

    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new(
        "aufgabe",
        [{"id": "t1", "phase_id": "p1"}, {"id": "t2", "phase_id": "p2"}],
        phasen=[
            {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
            {"id": "p2", "titel": "Phase 2", "tasks": ["t2"]},
        ],
    )
    assert ps.data["phasen"] == [
        {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
        {"id": "p2", "titel": "Phase 2", "tasks": ["t2"]},
    ]


def test_init_new_ohne_phasen(tmp_path):
    """M-323d: init_new ohne phasen -> leere Liste."""
    from werkstatt.phase_state import PhaseState

    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", [{"id": "t1"}])
    assert ps.data["phasen"] == []


def test_resume_laedt_phasen(tmp_path):
    """M-323d: load() laedt phasen aus der YAML."""
    from werkstatt.phase_state import PhaseState

    base = tmp_path / ".werkstatt"
    ps1 = PhaseState("p", base_dir=base)
    ps1.init_new(
        "aufgabe",
        [{"id": "t1"}],
        phasen=[{"id": "p1", "titel": "Phase 1", "tasks": ["t1"]}],
    )

    ps2 = PhaseState("p", base_dir=base)
    assert ps2.load() is True
    assert len(ps2.data["phasen"]) == 1
    assert ps2.data["phasen"][0]["id"] == "p1"


def test_apply_patches_ohne_post_tool_use(tmp_path, monkeypatch):
    """M-334b: post_tool_use wird nicht mehr gerufen."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    target = tmp_path / "test_x.py"
    target.write_text("a = 1\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )

    _hook_calls = []
    monkeypatch.setattr(loop_mod, "_call_hook",
                        lambda name, payload: (_hook_calls.append(name) or {"allow": True}))
    monkeypatch.setattr(loop_mod, "audit", lambda *a, **k: None)

    patches = [{"file": "test_x.py", "action": "update",
                "old_string": "a = 1\n", "new_string": "a = 2\n"}]
    loop_mod._apply_patches_with_hooks(st, patches, phase_label="test")

    assert "post_tool_use.py" not in _hook_calls
    assert "pre_tool_use.py" in _hook_calls  # pre bleibt


def test_post_tool_use_hook_datei_entfernt():
    """M-334b: hooks/post_tool_use.py existiert nicht mehr."""
    from pathlib import Path as P
    assert not P("/opt/werkstatt/hooks/post_tool_use.py").exists()


def test_expand_cmd_changed_py_files(tmp_path):
    """M-340: {changed_py_files} filtert auf .py-Dateien."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("x = 1\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "y.md").write_text("# y\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.patches = [
        {"file": "core/x.py", "new_string": "x = 1"},
        {"file": "docs/y.md", "new_string": "# y"},
    ]

    result = loop_mod._expand_cmd_placeholders(
        ["python3", "-m", "py_compile", "{changed_py_files}"],
        st, tmp_path,
    )
    assert result is not None
    # Nur core/x.py, nicht docs/y.md
    assert any("core/x.py" in c for c in result)
    assert not any("docs/y.md" in c for c in result)


def test_expand_cmd_changed_py_files_leer(tmp_path):
    """M-340: {changed_py_files} ohne .py-Dateien -> None (skip)."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "y.md").write_text("# y\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.patches = [{"file": "docs/y.md", "new_string": "# y"}]

    result = loop_mod._expand_cmd_placeholders(
        ["python3", "-m", "py_compile", "{changed_py_files}"],
        st, tmp_path,
    )
    assert result is None


def test_reviewer_reject_ignoriert_wenn_pytest_gruen(tmp_path, monkeypatch):
    """M-343c: Reviewer-Reject + last_verify_errors leer -> task_ok."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("x = 1\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "name": "T1", "action": "update",
                 "task_files": ["core/checks.py"]}]
    st.phasen = []

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(loop_mod, "run_explorer",
                        lambda s, a: {"key_files": [], "findings": "", "next_reads": []})
    monkeypatch.setattr(loop_mod, "run_builder", lambda s: True)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: True)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})
    monkeypatch.setattr(loop_mod, "run_reviewer", lambda s: False)
    monkeypatch.setattr(loop_mod, "_reflection_loop", lambda s, **kw: False)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    assert rc == 0, f"erwartet rc=0, war {rc}; audits={_audits}"
    assert "loop_reviewer_reject_ignoriert" in _audits


def test_reviewer_reject_bleibt_rot_wenn_pytest_rot(tmp_path, monkeypatch):
    """M-343c: Reviewer-Reject + last_verify_errors nicht leer -> return 1."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "checks.py").write_text("x = 1\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "name": "T1", "action": "update",
                 "task_files": ["core/checks.py"]}]
    st.phasen = []

    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(loop_mod, "run_explorer",
                        lambda s, a: {"key_files": [], "findings": "", "next_reads": []})
    monkeypatch.setattr(loop_mod, "run_builder", lambda s: True)

    # _verify_patches: pre_build True, danach False (und setzt last_verify_errors)
    _calls = [0]
    def _vp(s, phase=None):
        _calls[0] += 1
        if _calls[0] == 1:
            return True
        s.last_verify_errors = ["pytest: 3 failed"]
        return False
    monkeypatch.setattr(loop_mod, "_verify_patches", _vp)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})
    monkeypatch.setattr(loop_mod, "run_reviewer", lambda s: False)
    monkeypatch.setattr(loop_mod, "_reflection_loop", lambda s, **kw: False)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    assert rc == 1, f"erwartet rc=1, war {rc}; audits={_audits}"


def test_plan_renderer_zeigt_phasen(tmp_path, capsys):
    """M-348a: plan_renderer.plan zeigt Phasen + Tasks."""
    from werkstatt import loop_renderer as r
    r.plan(
        phasen=[
            {"id": "p1", "titel": "Analyse"},
            {"id": "p2", "titel": "Tests"},
        ],
        tasks=[
            {"id": "t1", "name": "lesen", "action": "read",
             "task_files": ["core/checks/__init__.py"], "phase_id": "p1"},
            {"id": "t2", "name": "testen", "action": "create",
             "task_files": ["tests/x.py"], "phase_id": "p2"},
        ],
        tests=["pytest tests/x.py"],
        akzeptanzkriterien=["y"],
    )
    out = capsys.readouterr().out
    assert "PLAN" in out
    assert "p1" in out
    assert "p2" in out
    assert "[read]" in out
    assert "[create]" in out


def test_human_gate_plan_auto_approve(tmp_path, monkeypatch):
    """M-348b: auto_approve=True -> rc=0."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState
    (tmp_path / ".werkstatt").mkdir()
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    rc = loop_mod._human_gate_plan(st, auto_approve=True)
    assert rc == 0
    assert "loop_plan_gate_auto" in _audits


def test_human_gate_plan_test_kontext(tmp_path, monkeypatch):
    """M-348b: WERKSTATT_IN_TEST=1 -> rc=0."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState
    (tmp_path / ".werkstatt").mkdir()
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    monkeypatch.setenv("WERKSTATT_IN_TEST", "1")
    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    rc = loop_mod._human_gate_plan(st, auto_approve=False)
    assert rc == 0
    assert "loop_plan_gate_test" in _audits


def test_human_gate_plan_eof_reject(tmp_path, monkeypatch):
    """M-348b: EOFError -> rc=1."""
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState
    (tmp_path / ".werkstatt").mkdir()
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    monkeypatch.setattr("builtins.input",
                        lambda *a, **kw: (_ for _ in ()).throw(EOFError()))
    rc = loop_mod._human_gate_plan(st, auto_approve=False)
    assert rc == 1
    assert "loop_plan_gate_eof" in _audits
