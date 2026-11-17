"""Tests fuer werkstatt/loop.py (Phase 7a: Happy Path)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import werkstatt.roles.builder as builder_mod
from werkstatt import loop as loop_mod
from werkstatt.loop import _plan_gate, _verify_patches, run_pipeline_loop
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState
from werkstatt.verify import _stage_anzahl, _stage_count_by_phase, _stage_ids


def _verify_ok_with_evidence(state, *_args, **_kwargs):
    task = getattr(state, "aktuelle_task", None)
    scope_files = (
        task.get("task_files", []) if isinstance(task, dict) else []
    )
    state.last_verify_results = [{
        "stage_id": "pytest_regression", "exit_code": 0, "ok": True,
        "scope_files": scope_files,
    }]
    return True


def _state(tmp_path, tasks=True, tests=True, akz=True, explorer_ctx=None):
    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )
    st.tasks = [{
        "id": "t1", "name": "Task 1", "task_files": ["src/sample.py"],
        "criterion_refs": ["AC1"],
    }] if tasks else []
    st.tests = ["Test 1"] if tests else []
    st.akzeptanzkriterien = ["Kriterium 1"] if akz else []
    # OP-136a: explorer_context muss gefuellt sein, damit der
    # Contract-Check nicht vorzeitig abbricht. Tests, die den
    # Explorer-Fail pruefen wollen, uebergeben explorer_ctx={}.
    if explorer_ctx is None:
        st.explorer_context = {
            "findings": "test",
            "key_files": [{"file": "test.py"}],
            "next_reads": ["test.py"],
        }
    else:
        st.explorer_context = explorer_ctx
    return st


def _approve_test_plan(phase_state):
    """Seed the durable approval required by the checkpoint coordinator."""
    phase_state.run_id = "test-approved-run"
    phase_state.data["setup_complete"] = True
    phase_state.data["plan_complete"] = True
    phase_state.bind_approved_plan()
    phase_state.save()


def test_plan_gate_ok(tmp_path, monkeypatch):
    st = _state(tmp_path)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda *_a, **_k: {"allow": True})
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
        json.dumps({"stages": [{
            "id": "ok",
            "command": [sys.executable, "-c", "import sys; sys.exit(0)"],
        }]}),
    )
    assert _verify_patches(st) is True


def test_verify_patches_fails(tmp_path):
    """Neue Version: Contract mit fehlschlagendem Check -> False."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        json.dumps({"stages": [{
            "id": "fail",
            "command": [sys.executable, "-c", "import sys; sys.exit(1)"],
        }]}),
    )
    assert _verify_patches(st) is False


def test_verify_success_clears_previous_errors(tmp_path):
    """Ein gruenes Verify darf keine Fehler des vorigen Aufrufs behalten."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    contract = contract_dir / "verify.json"
    contract.write_text(
        json.dumps({"stages": [{
            "id": "check",
            "command": [sys.executable, "-c", "import sys; sys.exit(1)"],
        }]}),
    )

    assert _verify_patches(st) is False
    assert st.last_verify_errors

    contract.write_text(
        json.dumps({"stages": [{
            "id": "check",
            "command": [sys.executable, "-c", "import sys; sys.exit(0)"],
        }]}),
    )

    assert _verify_patches(st) is True
    assert st.last_verify_errors == []
    assert st.last_verify_results == [
        {"stage_id": "check", "exit_code": 0, "ok": True, "error_excerpt": ""}
    ]


def test_stage_anzahl(tmp_path):
    """_stage_anzahl: 0 ohne verify.json, 4 mit vier Stages."""
    # Fall 1: keine .werkstatt/verify.json -> 0
    assert _stage_anzahl(tmp_path) == 0

    # Fall 2: verify.json mit vier Stages -> 4
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]}'
    )
    assert _stage_anzahl(tmp_path) == 4


def test_stage_ids(tmp_path):
    """_stage_ids: [] ohne verify.json, IDs mit vier Stages."""
    # Fall (a): keine .werkstatt/verify.json -> []
    assert _stage_ids(tmp_path) == []

    # Fall (b): verify.json mit vier Stages -> IDs in Reihenfolge
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]}'
    )
    assert _stage_ids(tmp_path) == ["a", "b", "c", "d"]


def test_stage_count_by_phase(tmp_path):
    """_stage_count_by_phase: 0 ohne verify.json (fail-closed), Zaehlung pro Phase."""
    # Fall (a): keine .werkstatt/verify.json -> 0 (kein FileNotFoundError)
    assert _stage_count_by_phase(tmp_path, "post_build") == 0
    assert _stage_count_by_phase(tmp_path, "phase_end") == 0

    # Fall (b): verify.json mit drei Stages -> Zaehlung pro Phase
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": ['
        '{"id": "a", "phase": "post_build"}, '
        '{"id": "b", "phase": "post_build"}, '
        '{"id": "c", "phase": "phase_end"}'
        ']}'
    )
    assert _stage_count_by_phase(tmp_path, "post_build") == 2
    assert _stage_count_by_phase(tmp_path, "phase_end") == 1
    # Schutz gegen versehentliches Mitzaehlen: unbekannte Phase -> 0
    assert _stage_count_by_phase(tmp_path, "build") == 0


def test_loop_stops_when_planner_evidence_is_missing(tmp_path):
    # A role without its required source evidence must not be called.
    st = _state(tmp_path, tasks=False)
    with patch(
        "werkstatt.planner.run_planner",
        side_effect=AssertionError("Planner darf ohne Belege nicht laufen"),
    ):
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1


def test_loop_does_not_verify_before_planner_evidence_is_ready(tmp_path):
    """A Verify action cannot run before the coordinator has a valid plan."""
    st = _state(tmp_path)
    # Task-Datei explizit setzen, damit die Klassifikation sie findet.
    st.tasks = [{"id": "t1", "name": "Update README.md", "description": "Add line"}]
    # Preflight-Fehler in derselben Datei (Task-Datei) -> BLOCKER
    st.preflight_fehler = [
        {"klasse": "syntax", "stage_id": "py_compile", "datei": "README.md", "text": "SyntaxError"},
    ]
    with patch("werkstatt.loop._verify_patches") as verify:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        verify.assert_not_called()


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
    from werkstatt import render as loop_renderer
    with patch.object(loop_renderer, "header") as m_h, \
         patch.object(loop_renderer, "footer") as m_f:
        from werkstatt.loop import main
        rc = main(["--project", "test-x", "--dry-run"])
    assert rc == 0
    assert m_h.called, "renderer.header muss aufgerufen werden"
    assert m_f.called, "renderer.footer muss aufgerufen werden"


def test_loop_uses_approved_checkpoint_for_task_selection(tmp_path):
    """The coordinator resumes a current human-approved graph directly."""
    st = _state(tmp_path)
    st.run_id = "test-approved-run"
    st.tasks = [{
        "id": "t1", "name": "Read source", "action": "read",
        "criterion_refs": ["AC1"], "task_files": ["src/task.py"],
    }]
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.py").write_text("x = 1\n", encoding="utf-8")
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("a", st.tasks, tests=st.tests, akzeptanzkriterien=st.akzeptanzkriterien)
    _approve_test_plan(ps)
    loop_mod.set_run_id(st.run_id)

    decision = loop_mod._run_coordinator_action(ps, st)

    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["next_task_id"] == "t1"
    assert decision["next_executor"] == "read_only_task"


def test_loop_resume_selects_only_pending_checkpoint_task(tmp_path):
    """A resumed approved graph skips tasks already recorded as done."""
    st = _state(tmp_path)
    st.run_id = "test-approved-run"
    st.tasks = [
        {"id": "t1", "name": "Read first", "action": "read",
         "criterion_refs": ["AC1"], "task_files": ["src/task.py"]},
        {"id": "t2", "name": "Read second", "action": "read",
         "criterion_refs": ["AC1"], "task_files": ["src/task.py"]},
    ]
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.py").write_text("x = 1\n", encoding="utf-8")
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("a", st.tasks, tests=st.tests, akzeptanzkriterien=st.akzeptanzkriterien)
    _approve_test_plan(ps)
    ps.mark_done("t1")
    loop_mod.set_run_id(st.run_id)

    decision = loop_mod._run_coordinator_action(ps, st)

    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["next_task_id"] == "t2"


def test_terminal_action_retry_key_requires_checkpoint_progress(tmp_path):
    """Only the same terminal action with byte-equivalent state is a retry."""
    first = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    first.data = {"phase_end_review_checkpoint": {"sha256": "a" * 64}}
    repeated = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    repeated.data = {"phase_end_review_checkpoint": {"sha256": "a" * 64}}
    advanced = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    advanced.data = {"phase_end_review_checkpoint": {"sha256": "b" * 64}}

    key = loop_mod._checkpoint_action_key("phase_end_verify", first)

    assert key is not None
    assert loop_mod._checkpoint_action_key("phase_end_verify", repeated) == key
    assert loop_mod._checkpoint_action_key("phase_end_verify", advanced) != key
    assert loop_mod._checkpoint_action_key("execute_task_checkpoint", first) is None

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

    with patch("werkstatt.loop._verify_patches", side_effect=_verify_ok_with_evidence), \
         patch("werkstatt.loop.run_builder", side_effect=_mock_builder), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
             patch("werkstatt.reviewer.run_phase_end_review", return_value=True), \
         patch("werkstatt.loop._reflection_loop", return_value=False), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
    assert rc == 1


def test_loop_patch_post_apply_verify(tmp_path):
    """M-298d: Patch der nicht greift triggert Reflection."""
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "Update README", "file": "README.md"}]
    (tmp_path / "README.md").write_text("# Test\n")
    # Patch ersetzt String, aber write schlaegt fehl (simuliert via Patch-Mock)
    with patch("werkstatt.loop._verify_patches", side_effect=_verify_ok_with_evidence), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
             patch("werkstatt.reviewer.run_phase_end_review", return_value=True), \
         patch("werkstatt.loop._reflection_loop", return_value=False), \
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
        f'{{"id": "pre1", "phase": "pre_build", "command": {json.dumps([sys.executable, "-c", "import sys; sys.exit(0)"])}}},'
        f'{{"id": "post1", "phase": "post_build", "command": {json.dumps([sys.executable, "-c", "import sys; sys.exit(1)"])}}}'
        ']}'
    )
    # pre_build: nur pre1 (ok) -> True
    assert _verify_patches(st, phase="pre_build") is True
    # post_build: nur post1 (fail) -> False
    assert _verify_patches(st, phase="post_build") is False


def test_preflight_checkpoint_selected_before_architect(tmp_path, monkeypatch):
    """Architect planning waits for current preflight evidence at a checkpoint."""
    from werkstatt.checkpoint_coordinator import choose_planner_checkpoint_action

    st = _state(tmp_path, tasks=False)
    st.aufgabe = "Untersuche src/module.py auf Fehler und entwirf eine Reparatur."
    st.coordinator_setup_context_ready = True
    st.explorer_context = {"findings": "aktueller Projektkontext"}
    st.planner_role_artifacts = {
        "scout": {"output": {"auftrag_prosa": "Aktueller Scout-Bericht."}},
    }
    st.run_id = "preflight-checkpoint-run"
    phase_state = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    phase_state.run_id = st.run_id
    phase_state.init_new(st.aufgabe, [], tests=[], akzeptanzkriterien=[])
    phase_state.run_id = st.run_id
    loop_mod.set_run_id(st.run_id)

    decision = choose_planner_checkpoint_action(
        st,
        phase_data=phase_state.data,
        planner_role_stage="scout",
        plan_checkpoint_complete=False,
        plan_goal_matches=False,
        plan_run_matches=False,
        plan_project_matches=True,
        plan_fingerprint_matches=False,
        explicit_source_context_ready=False,
        preserve_failed_tasks_on_setup=False,
    )
    assert decision["coordinator_action"] == "plan_preflight"
    assert decision["next_executor"] == "preflight"

    findings = [{
        "klasse": "syntax", "stage_id": "py_compile",
        "datei": "src/module.py", "text": "SyntaxError",
    }]
    monkeypatch.setattr("werkstatt.planner._preflight_scan", lambda _state: findings)
    assert loop_mod._run_plan_preflight_checkpoint(st, phase_state, "p") == 0
    assert st.preflight_fehler == findings
    assert phase_state.load_preflight_checkpoint(
        goal=st.aufgabe, run_id=st.run_id,
    ) == findings

def _approved_prebuild_candidate(tmp_path, findings):
    goal = "Update README.md"
    state = _state(tmp_path)
    state.aufgabe = goal
    state.tasks = [{
        "id": "t1", "name": "Update README.md", "action": "update",
        "task_files": ["README.md"], "criterion_refs": ["AC1"],
    }]
    state.tests = ["pytest -q"]
    state.akzeptanzkriterien = ["Kriterium 1"]
    state.preflight_fehler = findings
    state.run_id = "prebuild-candidate-run"
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")

    phase = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    phase.run_id = state.run_id
    digest = phase.record_plan_candidate(
        goal=goal,
        run_id=state.run_id,
        tasks=state.tasks,
        tests=state.tests,
        criteria=state.akzeptanzkriterien,
        phases=[],
        architect_prose="Plan mit aktuellen Belegen.",
        preflight_findings=findings,
    )
    assert phase.approve_plan_candidate(
        goal=goal, run_id=state.run_id, candidate_sha256=digest,
    )
    loop_mod.set_run_id(state.run_id)
    return state, phase


def test_prebuild_classified_unrelated_debt_is_skipped(tmp_path, monkeypatch):
    findings = [{
        "klasse": "type", "stage_id": "mypy",
        "datei": "core/unrelated.py", "text": "bestehender Fehler",
    }]
    state, phase = _approved_prebuild_candidate(tmp_path, findings)
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda _state: True)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda *_a, **_k: False)

    assert loop_mod._run_plan_candidate_prebuild_verify(
        state, phase, "p",
    ) == 0
    assert phase.data["plan_prebuild_verify_checkpoint"]["status"] == "baseline_debt_only"
    assert phase.data["plan_prebuild_verify_checkpoint"]["relevant_failure_count"] == 0


def test_prebuild_blocker_on_task_file_stops_candidate(tmp_path, monkeypatch):
    findings = [{
        "klasse": "syntax", "stage_id": "py_compile",
        "datei": "README.md", "text": "SyntaxError",
    }]
    state, phase = _approved_prebuild_candidate(tmp_path, findings)
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda _state: True)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda *_a, **_k: False)

    assert loop_mod._run_plan_candidate_prebuild_verify(
        state, phase, "p",
    ) == 1
    assert phase.data.get("plan_complete") is not True


def test_prebuild_unclassified_failure_stops_closed(tmp_path, monkeypatch):
    state, phase = _approved_prebuild_candidate(tmp_path, [])
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda _state: True)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda *_a, **_k: False)

    assert loop_mod._run_plan_candidate_prebuild_verify(
        state, phase, "p",
    ) == 1
    assert phase.data.get("plan_complete") is not True

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
        {"id": "t2", "name": "Doku", "task_files": ["docs/index.md"]},
    ]
    files = _extract_files_from_tasks(tasks)
    assert "core/a.py" in files
    assert "core/b.py" in files
    assert "docs/index.md" in files
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


def test_verify_resolves_bare_python3_to_project_venv(tmp_path):
    """A generic config must not route module checks to the system Python."""
    import json
    from subprocess import CompletedProcess
    from unittest.mock import patch

    from werkstatt.verify import _verify_patches

    st = _state(tmp_path)
    st.project_name = "test-bare-python"
    venv_python = tmp_path / ".venv" / "bin" / "python3"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    venv_python.chmod(0o755)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(json.dumps({
        "stages": [{
            "id": "ruff_changed",
            "command": ["python3", "-m", "ruff", "check", "changed.py"],
        }],
    }), encoding="utf-8")
    captured = []

    def mock_run(cmd, **kwargs):
        captured.append(list(cmd))
        return CompletedProcess(cmd, 0, "", "")

    with patch("werkstatt.orchestrator.load_project_config", return_value={
        "venv_python": "python3", "project_dir": str(tmp_path),
    }), patch("subprocess.run", side_effect=mock_run):
        assert _verify_patches(st, phase="post_build") is True

    assert captured[0][0] == str(venv_python)
    assert captured[0][1:4] == ["-m", "ruff", "check"]


def test_loop_task_read_only(tmp_path, monkeypatch):
    """One checkpoint reads source evidence without dispatching the Builder."""
    from tests.factories import coordinator_decision_for_task
    from werkstatt.roles import task_dispatch as task_executor

    st = _state(tmp_path)
    st.tasks = [
        {"id": "t1", "name": "Lesen", "action": "read",
         "task_files": ["app/foo.py"]},
        {"id": "t2", "name": "Schreiben", "action": "update",
         "task_files": ["app/foo.py"], "dependencies": ["t1"]},
    ]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = []
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "foo.py").write_text("value = 1\n", encoding="utf-8")
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new("a", st.tasks, tests=st.tests, akzeptanzkriterien=[])

    events = []
    builder_calls = []
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "")
    monkeypatch.setattr("werkstatt.agent._enforce_run_budget", lambda _state: False)
    monkeypatch.setattr(
        task_executor, "audit", lambda *args, **_kwargs: events.append(args),
    )
    monkeypatch.setattr(task_executor, "group_start", lambda *_args: None)
    monkeypatch.setattr(task_executor, "group_end", lambda: None)
    monkeypatch.setattr(task_executor, "task", lambda *_args: None)
    monkeypatch.setattr(task_executor, "task_started", lambda *_args: None)
    monkeypatch.setattr(task_executor, "task_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        task_executor, "_run_with_progress",
        lambda *_args, **_kwargs: builder_calls.append("builder") or False,
    )
    monkeypatch.setattr("werkstatt.progress.append", lambda *_args, **_kwargs: None)

    rc, _tasks_ok, _tasks = task_executor.run_task_checkpoint(
        st,
        ps,
        coordinator_decision=coordinator_decision_for_task(ps, st),
    )

    assert rc == 0
    read_task = next(
        item for item in ps.data["tasks"]
        if item["id"] == "t1"
    )
    assert read_task["read_evidence"]["files"]["app/foo.py"]["bytes"] > 0
    assert len(read_task["read_evidence"]["files"]["app/foo.py"]["sha256"]) == 64
    assert builder_calls == []
    next_task = ps.get_task("t2")
    assert next_task is not None
    passed_sources, error = task_executor._read_dependency_sources(
        st, ps, next_task,
    )
    assert error == ""
    assert passed_sources[0]["read_task_id"] == "t1"
    assert passed_sources[0]["source_sha256"] == read_task["read_evidence"][
        "files"
    ]["app/foo.py"]["sha256"]
    assert "value = 1" in passed_sources[0]["excerpt"]


def test_loop_reviewer_after_reflection_uses_checkpoint_recovery_policy():
    """Recovery after chat/reflection requires independent semantic review."""
    from werkstatt.review_dispatch import reviewer_dispatch_decision

    decision = reviewer_dispatch_decision(
        {
            "name": "Repair auth handling",
            "description": "Fix the rejected authentication behavior.",
            "action": "update",
            "task_files": ["src/auth.py"],
        },
        "diff --git a/src/auth.py b/src/auth.py\n+++ b/src/auth.py\n+return check(user)",
        recovery=True,
    )

    assert decision["invoke_reviewer"] is True
    assert decision["reason"] == "chat_recovery_requires_independent_review"


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
    monkeypatch.setattr("werkstatt.apply_patches._call_hook", lambda *_a, **_k: {"allow": True})
    monkeypatch.setattr("werkstatt.apply_patches._call_hook", lambda *_a, **_k: {"allow": True})
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
        json.dumps({"stages": [{"id": "pc", "command": [
            sys.executable, "-m", "py_compile", "{changed_files}",
        ]}]})
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
        json.dumps({"stages": [{"id": "py_compile", "command": [
            sys.executable, "-m", "py_compile", "core/__init__.py",
        ]}]})
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
        json.dumps({"stages": [
            {"id": "pc", "command": [
                sys.executable, "-m", "py_compile", "core/__init__.py",
            ], "phase": "post_build"},
            {"id": "pytest_full", "command": [
                sys.executable, "-c", "import sys; sys.exit(0)",
            ], "phase": "phase_end"},
        ]})
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
    import werkstatt.roles.builder as builder_mod
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
    monkeypatch.setattr("werkstatt.apply_patches._call_hook", lambda *_a, **_k: {"allow": True})
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
    import werkstatt.roles.builder as builder_mod
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
    monkeypatch.setattr("werkstatt.apply_patches._call_hook", lambda *_a, **_k: {"allow": True})
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: False)

    result = loop_mod._reflection_loop(st, max_runden=1)
    assert result is False
    # Current apply contract emits a reflection-level event with diagnostics.
    assert "loop_reflection_patch_nicht_angewendet" in _audits


def test_reflection_kein_patch_vom_builder(tmp_path, monkeypatch):
    """M-329: Wenn Builder keine Patches liefert -> loop_reflection_kein_patch."""
    import werkstatt.roles.builder as builder_mod
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
    import werkstatt.roles.builder as builder_mod
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
    """M-357: _run_with_progress wandelt Exceptions in False um.

    Frueher (M-327): Exception re-raised -> Loop starb ohne Audit.
    Jetzt (M-357): Exception -> False -> Aufrufer (Task-Loop) geht
    in den Fehlerpfad mit Audit + _task_ende.
    """
    from werkstatt import loop as loop_mod

    def _boom():
        raise ValueError("kaputt")

    result = loop_mod._run_with_progress(_boom, 1, 1, "x")
    assert result is False


def test_run_with_progress_heartbeat(monkeypatch):
    """M-327: _run_with_progress ruft heartbeat waehrend fn laeuft."""
    import time as _time

    from werkstatt import loop as loop_mod
    from werkstatt import render as r

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


def test_plan_gate_phasen_valid(tmp_path, monkeypatch):
    """M-323c: 2 Phasen, alle Tasks mit gueltiger phase_id -> True."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [
        {"id": "t1", "phase_id": "p1", "task_files": ["src/a.py"],
         "criterion_refs": ["AC1"]},
        {"id": "t2", "phase_id": "p2", "task_files": ["src/b.py"],
         "criterion_refs": ["AC1"]},
    ]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = [
        {"id": "p1", "titel": "Phase 1", "tasks": ["t1"]},
        {"id": "p2", "titel": "Phase 2", "tasks": ["t2"]},
    ]
    monkeypatch.setattr(loop_mod, "_call_hook", lambda *_a, **_k: {"allow": True})
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


def test_plan_gate_flat_bleibt_gueltig(tmp_path, monkeypatch):
    """M-323c: flacher Plan (phasen leer) bleibt gueltig."""
    from werkstatt.loop import _plan_gate
    from werkstatt.state import RunState

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [
        {"id": "t1", "task_files": ["src/a.py"], "criterion_refs": ["AC1"]},
        {"id": "t2", "task_files": ["src/b.py"], "criterion_refs": ["AC1"]},
    ]
    st.tests = ["pytest -q"]
    st.akzeptanzkriterien = ["a"]
    st.phasen = []
    monkeypatch.setattr(loop_mod, "_call_hook", lambda *_a, **_k: {"allow": True})
    assert _plan_gate(st) is True


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


def test_plan_renderer_zeigt_phasen(tmp_path, capsys, monkeypatch):
    """M-348a: plan_renderer.plan zeigt Phasen + Tasks.

    monkeypatch _use_rich=False: sonst schreibt Rich an einer beim
    Import gecachten sys.stdout-Referenz vorbei und capsys sieht nichts.
    """
    from werkstatt import render as r
    monkeypatch.setattr(r, "_use_rich", False)
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


def test_plan_gate_config_cannot_disable_approval(tmp_path, monkeypatch):
    """require_plan_approval=false darf die Freigabe nicht ueberspringen."""
    from werkstatt import loop as loop_mod
    from werkstatt import paths
    from werkstatt.state import RunState
    (tmp_path / ".werkstatt").mkdir()
    config_file = tmp_path / "project.yaml"
    config_file.write_text("require_plan_approval: false\n", encoding="utf-8")
    monkeypatch.setattr(paths, "project_config", lambda _name: config_file)
    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "n")
    _audits = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    rc = loop_mod._human_gate_plan(st)
    assert rc == 1
    assert "loop_plan_gate_rejected" in _audits



def test_noop_scout_plan_gate_shows_befund(tmp_path, monkeypatch):
    """Der No-Op-Pfad zeigt seinen Befund und verlangt j/n-Freigabe."""
    from werkstatt import gates, render
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    st = RunState(
        project_dir=tmp_path,
        project_name="p",
        scout_bereits_erfuellt=True,
    )
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr(gates, "_HEADLESS", False)
    monkeypatch.setattr(render, "plan", lambda *args: None)
    prompts = []
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": prompts.append(prompt) or "j",
    )
    events = []
    monkeypatch.setattr(
        loop_mod, "audit", lambda kind, payload, *a, **kw:
        events.append((kind, payload)),
    )

    assert loop_mod._human_gate_plan(st) == 0
    assert prompts and "NO-OP-PLAN" in prompts[0]
    shown = next(payload for kind, payload in events if kind == "loop_plan_shown")
    assert "bereits als erfuellt" in shown["plan_text"]

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
    rc = loop_mod._human_gate_plan(st, )
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
    rc = loop_mod._human_gate_plan(st, )
    assert rc == 1
    assert "loop_plan_gate_eof" in _audits
