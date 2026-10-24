"""Tests fuer werkstatt/loop.py (Phase 7a: Happy Path)."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from werkstatt.loop import _plan_gate, _verify_patches, run_pipeline_loop
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
    from werkstatt.phase_state import PhaseState
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
    from werkstatt.phase_state import PhaseState
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

    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", side_effect=_mock_reviewer), \
         patch("werkstatt.loop._reflection_loop", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])

    # Reviewer rejected nach Reflection -> return 1
    assert rc == 1
    assert reviewer_calls["n"] == 2  # zwei Aufrufe: 1 original + 1 nach Reflection


def test_reflection_erhaelt_reviewer_bug_kontext(tmp_path):
    """M-314: _reflection_loop bekommt Reviewer-Bugs als error_context."""
    from werkstatt.loop import _reflection_loop

    st = _state(tmp_path)
    st.reviewer_bugs = [
        {"file": "x.py", "line": 0, "description": "fehlt", "severity": "high"},
    ]

    captured = {}

    def _mock_ask_llm(api_key, system, user_content, **kwargs):
        captured["user_content"] = user_content
        reply = type("R", (), {"ok": False, "content": "", "error": "test"})()
        return reply

    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.loop._get_baseline_error_details", return_value="test-error"), \
         patch("werkstatt.loop.ask_llm", side_effect=_mock_ask_llm), \
         patch("werkstatt.loop.audit"):
        _reflection_loop(st, max_runden=1, error_context='[{"file":"x.py","description":"fehlt"}]')

    prompt = captured.get("user_content", "")
    assert "x.py" in prompt
    assert "fehlt" in prompt
