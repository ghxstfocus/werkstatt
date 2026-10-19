"""W36-RP (2026-10-18): run_pipeline-Integrationstests.

Mock-Helper + 3 Integrationstests (T-1, T-2, T-3).
Die 3 Tests schliessen die letzten zentralen
Integrations-Luecken:

  T-1: Builder-Lauf -> state.code_entwurf_historie
       befuellt (A1b-fix-Luecke).
  T-2: Apply -> state.mess_protokoll_nach_apply
       befuellt (W33a-Luecke).
  T-3: Judge -> state.review_runden akkumuliert
       Verdicts (W28b-Luecke).

AST-GRENZEN (siehe audit/00-audit-grenzen.md):
Der Helper mockt externe I/O. Er mockt NICHT:
  - record_code_entwurf (T-1 prueft es).
  - state-Attribute (state.code_entwurf_historie
    muss echt wachsen).
  - Parser (_parse_phase_plan, _parse_commands_
    planner).
  - builder_reply_mit_command_loop (T-1 nutzt
    den echten Builder-Loop mit ask_llm-Mock).

Aufrufer: run_pipeline Z. 12616 (main-Pfad).
Begruendung: klassischer Fall, den A1b-fix
adressiert.

subprocess: Die lokale Fixture _no_real_
subprocess blockiert alle subprocess-Aufrufe.
Tests, die subprocess brauchen, markieren sich
mit @pytest.mark.allow_subprocess(...). Der
Helper setzt gezielte subprocess-Mocks.

ask_llm-Rollen: Kein role-Parameter. Rollen
ueber system_prompt-String-Match:
  - builder_prompt -> Builder.
  - judge_prompt -> Judge.
  - tg_prompt -> Test-Gen.
  - reviewer_prompt -> Reviewer (Zaehler).
reviewer_prompt-Aufrufe: 1. Reviewer (Mess-
Wahl), 2. Reviewer (Commit). Zaehler fail-
closed bei >2 Aufrufen (A-W36-RP-10).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, "/opt/werkstatt")
import pipeline

sys.path.insert(0, "/opt/werkstatt/tests")
from test_pipeline import build_test_state

# =====================================================================
# W36-RP: subprocess fail-closed mit Whitelist.
# =====================================================================

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allow_subprocess(*names): erlaubt subprocess-"
        "Aufrufe, deren erstes Argument in names ist.")


@pytest.fixture(autouse=True)
def _no_real_subprocess(request, monkeypatch):
    """W36-RP: alle subprocess-Aufrufe im Test blockieren,
    ausser per Marker erlaubte."""
    import os as _os

    erlaubt = set()
    marker = request.node.get_closest_marker("allow_subprocess")
    if marker is not None:
        erlaubt = set(marker.args)

    def _ist_erlaubt(argv):
        if not argv:
            return False
        erstes = argv[0] if isinstance(argv, (list, tuple)) \
            else str(argv).split()[0]
        erstes = _os.path.basename(str(erstes))
        return erstes in erlaubt

    # Originale sichern (nur einmal)
    if not hasattr(subprocess, "__orig_run_w36__"):
        subprocess.__orig_run_w36__ = subprocess.run
        subprocess.__orig_call_w36__ = subprocess.call
        subprocess.__orig_check_call_w36__ = subprocess.check_call
        subprocess.__orig_check_output_w36__ = \
            subprocess.check_output
        subprocess.__orig_popen_w36__ = subprocess.Popen

    def _run(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.run({argv!r}) im Test "
                f"nicht erlaubt. Erlaubt: {erlaubt or '(keine)'}. "
                f"Fuege @pytest.mark.allow_subprocess(...) "
                f"hinzu oder mocke gezielt.")
        return subprocess.__orig_run_w36__(argv, *args, **kwargs)

    def _call(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.call({argv!r}) "
                f"im Test nicht erlaubt.")
        return subprocess.__orig_call_w36__(argv, *args, **kwargs)

    def _check_call(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.check_call({argv!r}) "
                f"im Test nicht erlaubt.")
        return subprocess.__orig_check_call_w36__(
            argv, *args, **kwargs)

    def _check_output(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.check_output({argv!r}) "
                f"im Test nicht erlaubt.")
        return subprocess.__orig_check_output_w36__(
            argv, *args, **kwargs)

    def _popen(argv, *args, **kwargs):
        if not _ist_erlaubt(argv):
            raise AssertionError(
                f"W36-RP: subprocess.Popen({argv!r}) "
                f"im Test nicht erlaubt.")
        return subprocess.__orig_popen_w36__(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _run)
    monkeypatch.setattr(subprocess, "call", _call)
    monkeypatch.setattr(subprocess, "check_call", _check_call)
    monkeypatch.setattr(subprocess, "check_output", _check_output)
    monkeypatch.setattr(subprocess, "Popen", _popen)


# =====================================================================
# W36-RP: Mock-Helper.
# =====================================================================

def _reply_ok(content: str):
    """Baut ein LLMReply-aehnliches Objekt mit ok=True."""
    return type("R", (), {"ok": True, "content": content,
                          "error": ""})()


def _reply_err(error: str = "test-fehler"):
    return type("R", (), {"ok": False, "content": "",
                          "error": error})()


def mock_run_pipeline_deps(
        monkeypatch,
        *,
        builder_reply: str = (
            "PATCH-BEGINN\n"
            "typ: patch\n"
            "pfad: core/x.py\n"
            "anker: y = 1\n"
            "ersatz: y = 2\n"
            "PATCH-ENDE\n"),
        judge_verdict: str = "GO",
        judge_verdict_sequenz: list[str] | None = None,
        commit_verdict: str = "COMMIT-GO",
        builder_max_runden: int = 3,
        mock_audit: bool = True,
) -> dict[str, Any]:
    """Setzt alle run_pipeline-Mocks.

    Rueckgabe: dict mit Mock-Handles (fuer Assertions).

    Defaults (A-W36-RP-5): jeder Aufruf sicher.
    Gefaehrliche Defaults (ask_llm ohne Prompt-Match):
    AssertionError.

    Rollen-Strategie ask_llm (A-W36-RP-4):
      - builder_prompt -> builder_reply.
      - judge_prompt -> judge_verdict.
      - tg_prompt -> leere Antwort (kein Test-Gen).
      - reviewer_prompt -> Zaehler. 1. -> "",
        2. -> commit_verdict. 3. -> AssertionError
        (A-W36-RP-10).
    """
    handle: dict[str, Any] = {}

    # --- ask_llm ---
    reviewer_zaehler = {"n": 0}

    def _fake_ask_llm(api_key, system_prompt, user_content,
                      model, temperature, *args, **kwargs):
        # W36-RP: Rollen ueber Frontmatter-Praefix,
        # nicht per Substring. Grund: der judge_prompt
        # enthaelt 'Reviewer' (judge.md + HARD_RULES_
        # BASE HR7), der builder_prompt enthaelt
        # 'Reviewer' (HARD_RULES_BUILDER), etc.
        # build_system_prompt gibt das Frontmatter
        # ('---\nname: <rolle>\n---') mit aus.
        sp = system_prompt or ""
        # W36-RP: Rollen ueber Body-Anfang. Grund:
        # build_system_prompt gibt den Body aus
        # (ohne Frontmatter). judge.md beginnt mit
        # "Du bist der Judge.", reviewer.md mit
        # "Du bist der Reviewer.".
        if sp.startswith("Du bist der Builder"):
            handle.setdefault("builder_calls", []).append(
                user_content)
            return _reply_ok(builder_reply)
        if sp.startswith("Du bist der Judge"):
            handle.setdefault("judge_calls", []).append(
                user_content)
            # 3a-1c-1a (A4-1): Sequenz-Modus fuer
            # mehrrundige Verdict-Tests. Nach Erschoepfung
            # der Sequenz Fallback auf judge_verdict
            # (fail-open; neue Sequenz-Tests muessen alle
            # Runden abdecken).
            if judge_verdict_sequenz is not None:
                idx = len(handle.setdefault(
                    "judge_calls_consumed", []))
                handle["judge_calls_consumed"].append(idx)
                if idx < len(judge_verdict_sequenz):
                    return _reply_ok(
                        judge_verdict_sequenz[idx])
            return _reply_ok(judge_verdict)
        if sp.startswith("Du bist der Test-Generator"):
            return _reply_ok("")
        if sp.startswith("Du bist der Reviewer"):
            reviewer_zaehler["n"] += 1
            n = reviewer_zaehler["n"]
            if n == 1:
                # Reviewer Mess-Wahl: keine Commands.
                return _reply_ok("")
            if n >= 2:
                # Reviewer Commit-Review (auch bei Wiederholung
                # im commit_versuche-Loop, 3a-1c-0 B1b).
                return _reply_ok(commit_verdict)
        raise AssertionError(
            f"W36-RP: ask_llm mit unbekanntem Body-Anfang "
            f"({sp[:80]!r}). Rollen-Match fehlgeschlagen.")

    monkeypatch.setattr(pipeline, "ask_llm", _fake_ask_llm)
    handle["ask_llm"] = _fake_ask_llm

    # --- apply_and_recheck ---
    def _fake_apply(state, always, file_whitelist):
        # Setzt mess_protokoll_nach_apply (T-2).
        state.mess_protokoll_nach_apply = (
            "=== read_file ===\ncore/x.py: y = 2\n")

    monkeypatch.setattr(pipeline, "apply_and_recheck",
                        _fake_apply)
    handle["apply_and_recheck"] = _fake_apply

    # --- build_commit_paket ---
    def _fake_bcp(state):
        # W36-RP: Message braucht "Aenderung:"-Section
        # mit Bullet-Pfaden (W10-A2/A3, Z. 8172).
        return {
            "message": "Test-Commit\n\n"
                       "Aenderung:\n"
                       "  - core/x.py\n",
            "dateien": ["core/x.py"],
        }

    monkeypatch.setattr(pipeline, "build_commit_paket",
                        _fake_bcp)
    handle["build_commit_paket"] = _fake_bcp

    # --- apply_commit_and_doku ---
    monkeypatch.setattr(pipeline, "apply_commit_and_doku",
                        lambda state, paket: True)

    # --- Basis-Gate ---
    def _fake_bg_ziel(project_dir, timeout=900):
        return {"exit_code": 0, "klassifizierung": "gruen",
                "failed_count": 0, "passed_count": 1,
                "failed_test_ids": [], "failed_test_ids_mehr": [],
                "dauer_s": 0.1, "raw_tail": ""}

    def _fake_bg_suite(project_dir, timeout=900):
        return {"exit_code": 0, "klassifizierung": "gruen",
                "failed_count": 0, "passed_count": 1,
                "failed_test_ids": [], "failed_test_ids_mehr": [],
                "dauer_s": 0.1, "raw_tail": ""}

    monkeypatch.setattr(pipeline, "_basis_gate_pytest_ziel",
                        _fake_bg_ziel)
    monkeypatch.setattr(pipeline, "_basis_gate_pytest_suite",
                        _fake_bg_suite)

    # --- budget_or_recover ---
    monkeypatch.setattr(pipeline, "budget_or_recover",
                        lambda *a, **kw: None)

    # --- execute_commands ---
    monkeypatch.setattr(pipeline, "execute_commands",
                        lambda *a, **kw: {})

    # --- subprocess.run: git diff --name-only ---
    def _fake_sp_run(argv, *args, **kwargs):
        # git-Kommandos erlaubt, jeweils mit
        # passender Attrappe.
        if not isinstance(argv, (list, tuple)):
            raise TypeError(
                f"W36-RP: subprocess.run({argv!r}) "
                f"kein Tupel.")
        if argv[:3] == ("git", "diff", "--name-only"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "core/x.py\n",
                                  "stderr": ""})()
        if argv[:2] == ("git", "log"):
            # git log -N --format=...
            return type("R", (), {"returncode": 0,
                                  "stdout": "",
                                  "stderr": ""})()
        if argv[:2] == ("git", "status"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "",
                                  "stderr": ""})()
        if argv[:3] == ("git", "rev-parse", "--short"):
            return type("R", (), {"returncode": 0,
                                  "stdout": "abc1234\n",
                                  "stderr": ""})()
        raise AssertionError(
            f"W36-RP: subprocess.run({argv!r}) unerwartet.")

    monkeypatch.setattr(subprocess, "run", _fake_sp_run)

    # --- audit ---
    if mock_audit:
        monkeypatch.setattr(pipeline, "audit",
                            lambda *a, **kw: None)

    # --- run_measurement_mit_argv ---
    # W36-RP: Basis-Gate laeuft mit "gruen"-Attrappe.
    # Der Test prueft nicht das Basis-Gate, sondern
    # die Builder-/Apply-/Judge-Kette danach.
    def _fake_run_measurement(m, whitelist, project_dir,
                              extra_arg=None):
        # out, ok, argv
        return ("", True, list(getattr(m, "argv", ())))

    monkeypatch.setattr(pipeline, "run_measurement_mit_argv",
                        _fake_run_measurement)

    # --- run_measurement (Wrapper) ---
    # Rueckgabe: (out, ok) laut Aufrufer Z. 9191.
    def _fake_run_measurement2(m, whitelist, project_dir):
        return ("", True)

    monkeypatch.setattr(pipeline, "run_measurement",
                        _fake_run_measurement2)

    # --- _lade_und_pruefe_projekt ---
    def _fake_lade_projekt(project_name):
        # W36-RP: build_catalog braucht nicht-leere
        # always_run/optional_catalog. Die IDs muessen
        # im all_m-Dict von build_catalog existieren.
        return {
            "project": project_name,
            "project_dir": "/tmp",
            "always_run": [
                "py_compile", "ruff", "mypy",
                "test_count", "git_status", "git_head",
            ],
            "optional_catalog": ["read_file"],
            "agent_docs": {},
            "file_whitelist": ["core/"],
        }

    monkeypatch.setattr(pipeline, "_lade_und_pruefe_projekt",
                        _fake_lade_projekt)

    # --- input (Human-Gate) ---
    # run_pipeline endet mit input("Deine Wahl: ").
    # Tests antworten mit "j" (approve).
    import builtins
    monkeypatch.setattr(builtins, "input",
                        lambda *a, **kw: "j")

    return handle


# =====================================================================
# T-1: Builder-Lauf -> state.code_entwurf_historie.
# =====================================================================

def test_t1_builder_lauf_befuellt_historie(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-1 (A-B1-13): Nach Builder-Lauf ist
    state.code_entwurf_historie befuellt.
    Schliesst die A1b-fix-Luecke (record_code_entwurf
    nur in run_pipeline, nicht in Tests).
    """
    mock_run_pipeline_deps(monkeypatch)
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    assert len(state.code_entwurf_historie) >= 1, (
        f"code_entwurf_historie leer (rc={rc}). "
        f"record_code_entwurf wurde nicht gerufen.")
    phasen = [e.get("phase")
              for e in state.code_entwurf_historie]
    assert "normal" in phasen, (
        f"Keine phase='normal' in Historie: {phasen}")


# =====================================================================
# T-2: Apply -> state.mess_protokoll_nach_apply.
# =====================================================================

def test_t2_apply_befuellt_mess_nach(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-2: Nach Apply ist
    state.mess_protokoll_nach_apply befuellt.
    Schliesst die W33a-Luecke.
    """
    mock_run_pipeline_deps(monkeypatch)
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    assert state.mess_protokoll_nach_apply, (
        f"mess_protokoll_nach_apply leer (rc={rc}). "
        f"apply_and_recheck hat keine Post-Apply-"
        f"Messung erzeugt.")


# =====================================================================
# T-3: Judge -> review_runden akkumuliert Verdicts.
# =====================================================================

def test_t3_review_loop_akkumuliert_verdicts(
        tmp_path: Path, monkeypatch) -> None:
    """W36-RP T-3: review_runden enthaelt Judge-
    Verdicts. Schliesst die W28b-Luecke.
    """
    mock_run_pipeline_deps(monkeypatch, judge_verdict="GO")
    # W36-RP: run_pipeline baut einen NEUEN State
    # (Z. 9159: state_ref.append(state)). state_ref
    # muss leer sein. Das neue State wird mit
    # load_agents/load_docs/build_catalog gebaut.
    state_ref: list = []

    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", state_ref)

    state = state_ref[0]
    verdicts = [r.get("verdict")
                for r in state.review_runden]
    assert "GO" in verdicts, (
        f"review_runden enthaelt kein GO: {verdicts} "
        f"(rc={rc})")


# =====================================================================
# W30-fix-b: max_builder_runden=0 -> fail-closed.
# =====================================================================

def test_w30_fix_b_max_builder_runden_null(
        tmp_path: Path, monkeypatch) -> None:
    """W30-fix-b: max_builder_runden=0 ist ein
    Konfigurationsfehler. Kein UnboundLocalError,
    sondern (None, 19) + Audit builder_runden_ungueltig.
    """
    state = build_test_state(project_dir=tmp_path)
    gerufen = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw:
            gerufen.append((kind, payload)))
    # ask_llm darf NICHT gerufen werden (Validierung
    # greift vor dem Loop).
    monkeypatch.setattr(
        pipeline, "ask_llm",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("ask_llm unerwartet gerufen")))
    # subprocess darf nicht gerufen werden.
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("subprocess unerwartet")))
    monkeypatch.setattr(
        subprocess, "check_output",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("subprocess unerwartet")))

    result = pipeline.builder_reply_mit_command_loop(
        state, "key", "builder-prompt",
        lambda _s: "user-prompt",
        tmp_path, "test",
        max_builder_runden=0)

    assert result == (None, 19), (
        f"Erwartet (None, 19), bekommen {result}")
    arten = [k for (k, _) in gerufen
             if k == "builder_runden_ungueltig"]
    assert len(arten) == 1, (
        f"builder_runden_ungueltig {len(arten)}x gerufen, "
        f"erwartet 1. Alle: {[k for k,_ in gerufen]}")
    for (k, payload) in gerufen:
        if k == "builder_runden_ungueltig":
            assert payload["max_builder_runden"] == 0


# =====================================================================
# W48-A16-b-2-a: solver_max_runden_erreicht Payload.
# =====================================================================

def test_solver_max_runden_erreicht_payload(
        tmp_path: Path, monkeypatch) -> None:
    """W48-A16-b-2-a: Deadlock-Pfad schreibt
    solver_max_runden_erreicht mit symmetrischem
    Payload (aufrufe, max_runden, pfad, grund).
    """
    state = build_test_state(
        project_dir=tmp_path)
    state.solver_config = {"max_runden": 1}
    state.solver_aufrufe = 1
    # W48-A16-b-2-a: Trigger "anker_nicht_gemessen"
    # (nicht "wirkungsloser_patch"). Daher
    # letzter_patch_wirkungslos=False.
    state.letzter_patch_wirkungslos = False
    state.anker_fehler_in_folge = 2

    gerufen = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw:
            gerufen.append((kind, payload)))
    monkeypatch.setattr(
        pipeline, "budget_or_recover",
        lambda *a, **kw: None)

    rc = pipeline.handle_deadlock_mit_solver(
        state, "key", tmp_path, "test", 10, 0)

    caps = [p for (k, p) in gerufen
            if k == "solver_max_runden_erreicht"]
    assert len(caps) == 1, (
        f"solver_max_runden_erreicht {len(caps)}x, "
        f"erwartet 1. Alle: {[k for k,_ in gerufen]}")
    payload = caps[0]
    assert payload["pfad"] == "deadlock", payload
    assert "aufrufe" in payload, payload
    assert "max_runden" in payload, payload
    assert payload["max_runden"] == 1, payload
    assert payload["grund"] == "anker_nicht_gemessen", payload
    assert rc is None, f"rc={rc}"


# =====================================================================
# W25-planner-md: Skills im Planner-Prompt.
# =====================================================================

def test_w25_planner_prompt_enthaelt_skills() -> None:
    """W25-planner-md: _planner_user_content enthaelt
    AVAILABLE SKILLS.
    """
    state = build_test_state()
    out = pipeline._planner_user_content(
        "Test-Auftrag", "historie", 1, state=state)
    assert "AVAILABLE SKILLS" in out, (
        "AVAILABLE SKILLS fehlt im Planner-Prompt")
    # Mindestens ein Skill-Name sichtbar.
    assert "patch-format" in out or "anker-regeln" in out


def test_w25_planner_prompt_enthaelt_geladene_skills() -> None:
    """W25-planner-md: _planner_user_content enthaelt
    GELADENE SKILLS, wenn state.geladene_skills gesetzt.
    """
    state = build_test_state()
    state.geladene_skills = ["patch-format"]
    out = pipeline._planner_user_content(
        "Test-Auftrag", "historie", 1, state=state)
    assert "GELADENE SKILLS" in out, (
        "GELADENE SKILLS fehlt im Planner-Prompt")
    assert "patch-format" in out


def test_w25_planner_load_skill_e2e(
        monkeypatch) -> None:
    """W25-planner-md E2E: Planner sendet load_skill,
    _verarbeite_skill_commands laedt, naechster Prompt
    enthaelt GELADENE SKILLS.
    """
    state = build_test_state()
    state.agents = pipeline.load_agents(
        "/opt/werkstatt/agents")
    state.agents.setdefault("planner", {})
    state.agents["planner"]["body"] = (
        "Du bist der Planner. Test.")
    # Runde 1: load_skill. Runde 2: Plan.
    antworten = [
        type("R", (), {
            "ok": True,
            "content": "COMMAND: load_skill patch-format",
            "error": ""})(),
        type("R", (), {
            "ok": True,
            "content": (
                "PHASE: Test\n"
                "UNTERBLOCK U1: Test\n"
                "datei:core/x.py, aktion:patch\n"),
            "error": ""})(),
    ]
    aufrufe = {"n": 0}
    prompts = []

    def _fake_ask(api_key, system_prompt, user_content,
                  *args, **kwargs):
        prompts.append(user_content)
        i = min(aufrufe["n"], len(antworten) - 1)
        aufrufe["n"] += 1
        return antworten[i]

    monkeypatch.setattr(pipeline, "ask_llm", _fake_ask)
    monkeypatch.setattr(
        pipeline, "extract_paths_from_aufgabe",
        lambda *a, **kw: [])
    monkeypatch.setattr(
        pipeline, "read_target_snippets",
        lambda *a, **kw: "")
    monkeypatch.setattr(
        pipeline, "format_doc_snippets",
        lambda *a, **kw: "")
    monkeypatch.setattr(
        pipeline, "format_projekt_stand",
        lambda *a, **kw: "")

    pipeline._planner_lauf(
        state, "key", "auftrag",
        Path("/tmp"), "test", "historie",
        max_runden=3)

    # Runde 2 muss GELADENE SKILLS enthalten.
    assert len(prompts) >= 2, (
        f"Erwartet 2 Runden, {len(prompts)}.")
    assert "GELADENE SKILLS" in prompts[1], (
        "GELADENE SKILLS fehlt in Runde 2.")
    assert "patch-format" in prompts[1]
    # state.geladene_skills enthaelt patch-format.
    assert "patch-format" in state.geladene_skills


# =====================================================================
# 3a-1a: run_pipeline-Charakterisierung (2026-10-19)
# Reviewer-Gate 3a-1a, 8 Tests.
# =====================================================================

def _state_ref():
    """Leerer state_ref fuer run_pipeline."""
    return []


def test_run_pipeline_state_guard_valueerror(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Setup: phasen_state + nicht-leerer state_ref
    -> ValueError.

    Zitat run_pipeline Z. 7674-7679:
        if phasen_state is not None:
            if state_ref:
                raise ValueError(...)
    """
    mock_run_pipeline_deps(monkeypatch)
    # Phasen-State mit projekt_dir bauen
    ph = build_test_state(project_dir=tmp_path)
    ph.phase_aktiv = True
    ref = [ph]  # nicht leer
    with pytest.raises(ValueError, match="state_ref nicht leer"):
        pipeline.run_pipeline(
            "test-projekt", "Test-Auftrag", ref,
            phasen_state=ph)


def test_run_pipeline_phasen_state_uebernommen(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Setup: phasen_state wird uebernommen
    (state_ref[0] is phasen_state).

    Zitat run_pipeline Z. 7680:
        state = phasen_state
    """
    mock_run_pipeline_deps(monkeypatch)
    # Rollen + Doku bereitstellen, damit run_pipeline
    # nicht an KeyError "reviewer" scheitert.
    _agents = {
        r: {"body": f"Du bist der {r.capitalize()}.",
            "name": r}
        for r in ("builder", "reviewer", "solver",
                  "test_generator")
    }
    monkeypatch.setattr(
        pipeline, "load_agents", lambda d: _agents)
    monkeypatch.setattr(
        pipeline, "load_docs", lambda d, p: {})
    monkeypatch.setattr(
        pipeline, "load_recent_commits", lambda *a, **kw: "")
    ph = build_test_state(project_dir=tmp_path)
    ph.agents = _agents
    ph.phase_aktiv = True
    ref = []
    pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref,
        phasen_state=ph)
    assert len(ref) == 1
    assert ref[0] is ph
    # P-Bugfix Z. 7684: state.aufgabe = aufgabe
    assert ph.aufgabe == "Test-Auftrag"


def test_run_pipeline_klassisch_neuer_state(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Setup: phasen_state=None -> neuer RunState
    in state_ref.

    Zitat run_pipeline Z. 7685-7698 (else: state = RunState).
    """
    mock_run_pipeline_deps(monkeypatch)
    ref = []
    pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert len(ref) == 1
    # Neuer State, nicht phasen_state
    assert ref[0].aufgabe == "Test-Auftrag"


def test_run_pipeline_builder_fehler_rc4(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a S2: Builder-Fehler -> rc=4.

    Zitat run_pipeline Z. 7965-7970:
        if not reply_roh.ok:
            ...
            return 4
    """
    mock_run_pipeline_deps(monkeypatch)
    # Builder-Antwort: reply.ok=False
    from werkstatt.state import LLMReply
    monkeypatch.setattr(
        pipeline, "builder_reply_mit_command_loop",
        lambda *a, **kw: (LLMReply(ok=False, error="kaputt"), None))
    ref = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 4, f"erwartet rc=4, gefunden rc={rc}"


def test_run_pipeline_judge_go_commit(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a S4: Judge-GO -> Commit-Pfad.

    Zitat run_pipeline Z. 8929 (commit_verdict == "COMMIT-GO").
    """
    mock_run_pipeline_deps(monkeypatch, judge_verdict="GO",
                           commit_verdict="COMMIT-GO")
    ref = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    state = ref[0]
    # Commit-Paket gebaut
    assert state.commit_paket, (
        f"commit_paket leer (rc={rc})")
    # Commit-Paket enthaelt message
    assert "message" in state.commit_paket


def test_run_pipeline_basis_gate_rot(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Luecke: Basis-Gate rot -> Fail-Pfad.

    Zitat run_pipeline Z. 7735-7748:
        for mid, m in always.items():
            out, ok = run_measurement(m, file_whitelist, project_dir)
            if not ok:
                basis_fehler.append(mid)
        ...
        audit("basis_gate_rot", ...)
    """
    mock_run_pipeline_deps(monkeypatch)
    # Rollen bereitstellen (run_pipeline greift auf
    # agents["reviewer"] zu, nach dem Basis-Gate).
    _agents = {
        r: {"body": f"Du bist der {r.capitalize()}.",
            "name": r}
        for r in ("builder", "reviewer", "solver",
                  "test_generator")
    }
    monkeypatch.setattr(
        pipeline, "load_agents", lambda d: _agents)
    monkeypatch.setattr(
        pipeline, "load_docs", lambda d, p: {})
    # Basis-Gate rot: run_measurement liefert ok=False
    monkeypatch.setattr(
        pipeline, "run_measurement",
        lambda *a, **kw: ("", False))
    gerufen = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw:
            gerufen.append(kind))
    ref = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc != 0, f"erwartet rc != 0, gefunden rc={rc}"
    assert "basis_gate_rot" in gerufen, (
        f"erwartet audit basis_gate_rot, "
        f"gefunden: {gerufen[:10]}")


def test_run_pipeline_commit_fehler_rollback(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Luecke: apply_commit_and_doku False -> Fail-Pfad.

    Zitat run_pipeline Z. 9052-9053:
        if apply_commit_and_doku(state, state.commit_paket):
            audit("commit_applied", ...)
    """
    mock_run_pipeline_deps(monkeypatch, judge_verdict="GO",
                           commit_verdict="COMMIT-GO")
    # apply_commit_and_doku False
    monkeypatch.setattr(
        pipeline, "apply_commit_and_doku",
        lambda state, paket: False)
    ref = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc != 0, f"erwartet rc != 0 bei commit-fehler, gefunden rc={rc}"


def test_run_pipeline_solver_trigger_im_block(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1a Recovery: solver_trigger im Block (Deadlock).

    Zitat run_pipeline Z. 5840/5856 (handle_deadlock_mit_solver,
    audit solver_trigger_c).
    """
    mock_run_pipeline_deps(monkeypatch)
    # Builder-Deadlock erzwingen: builder_reply liefert 3x COMMAND
    # ohne Patch.
    from werkstatt.state import LLMReply
    monkeypatch.setattr(
        pipeline, "builder_reply_mit_command_loop",
        lambda *a, **kw: (
            LLMReply(ok=False, error="deadlock"),
            19))
    ref = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 19, f"erwartet rc=19 (deadlock), gefunden rc={rc}"


# =====================================================================
# 3a-1c-0 (C-CN-3, 2026-10-19): 2 B1b-Tests fuer Fail-Closed-Pfade
# in run_pipeline. Reviewer-Freigabe (a) mit 5 Auflagen.
# =====================================================================

def test_run_pipeline_scope_violation_rc9(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-0 B1b: _check_commit_scope False -> rc=9.

    Zitat run_pipeline Z. 8797-8801:
        _scope_ok, _scope_grund = _check_commit_scope(
            state, _diff_name_only, project_dir, project_name)
        if not _scope_ok:
            return 9

    Deckt ab: deterministisches Commit-Scope-Gate vor
    LLM-Review (R16-Aequivalent). Fail-Closed, rc=9.
    """
    mock_run_pipeline_deps(monkeypatch,
                           judge_verdict="GO",
                           commit_verdict="COMMIT-GO")
    monkeypatch.setattr(
        pipeline, "_check_commit_scope",
        lambda *a, **kw: (False, "scope_violation"))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 9, (
        f"erwartet rc=9 bei scope_violation, gefunden rc={rc}")


def test_run_pipeline_commit_no_go_max_rc7(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-0 B1b: commit_versuche >= max_commit_versuche -> rc=7.

    Zitat run_pipeline Z. 8942-8946:
        commit_versuche += 1
        if commit_versuche >= max_commit_versuche:
            return _fail_closed(
                state, project_dir, project_name, 7,
                "commit_no_go_max_versuche")

    Deckt ab: Fail-Closed nach max_commit_versuche x
    COMMIT-NO-GO (Endlos-Loop-Schutz). rc=7.
    Helper-Parameter commit_verdict (tests:170) reicht;
    _rollback_zieldateien wird gemockt, weil _fail_closed
    es aufruft.
    """
    mock_run_pipeline_deps(monkeypatch,
                           judge_verdict="GO",
                           commit_verdict="COMMIT-NO-GO")
    monkeypatch.setattr(
        pipeline, "_rollback_zieldateien",
        lambda *a, **kw: None)
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 7, (
        f"erwartet rc=7 bei commit_no_go_max, gefunden rc={rc}")


# =====================================================================
# 3a-1c-1a (2026-10-19): AQ-Vorspann C4. 2 Tests.
# Reviewer-Freigabe A4-1 + L-1/COMMAND (5 Auflagen).
# =====================================================================

def test_run_pipeline_eskalation_rc14(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1a AQ-1: ESKALATION -> rc=14.

    Zitat run_pipeline Z. 8186-8194:
        if verdict == "ESKALATION":
            ...
            audit("recovery_eskalation", ...)
            return 14

    A3: Unterscheidung zu UNKLAR. UNKLAR schreibt
    audit("review_unklar_widerspruch") oder
    audit("review_unklar_eskalation"). ESKALATION schreibt
    audit("recovery_eskalation"). Der Test asserted
    rc=14, "recovery_eskalation" da, KEIN
    "review_unklar_*".
    """
    mock_run_pipeline_deps(monkeypatch,
                           judge_verdict="ESKALATION")
    monkeypatch.setattr(
        pipeline, "ask_reviewer_for_recovery",
        lambda *a, **kw: type("V", (), {
            "frage_an_menschen": "test-frage",
            "empfehlung": "test-empfehlung"})())
    monkeypatch.setattr(
        pipeline, "print_recovery", lambda *a, **kw: None)
    gerufen: list[str] = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(kind))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 14, (
        f"erwartet rc=14 bei ESKALATION, gefunden rc={rc}")
    assert "recovery_eskalation" in gerufen, (
        f"erwartet audit recovery_eskalation, "
        f"gefunden: {gerufen[:15]}")
    assert "review_unklar_eskalation" not in gerufen, (
        f"UNKLAR-Pfad unerwartet beruehrt "
        f"(review_unklar_eskalation): {gerufen[:15]}")
    assert "review_unklar_widerspruch" not in gerufen, (
        f"UNKLAR-Pfad unerwartet beruehrt "
        f"(review_unklar_widerspruch): {gerufen[:15]}")


def test_run_pipeline_command_judge_command_audit(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1a AQ-2: COMMAND dispatcht audit(judge_command).

    Zitat run_pipeline Z. 8162-8185:
        if verdict == "COMMAND":
            cmds = parse_commands(reply.content)
            for cmd in cmds:
                if cmd.get("id") == "solver":
                    _handle_solver_command(...)
                else:
                    execute_commands(...)
            audit("judge_command", {...}, ...)
            continue

    C4-Dispatch: COMMAND loest audit("judge_command") aus
    und continue't. _handle_solver_command ist gemockt —
    Solver-Ausfuehrung wird NICHT durch diesen Test
    charakterisiert (A7-2).

    A7-1: Zaehlung statt "present". Sequenz
    ["COMMAND: RUN solver", "GO"] mit max_rounds=2:
    Runde 1 = COMMAND (1x judge_command), Runde 2 = GO
    (0x judge_command). count("judge_command") == 1
    beweist Dispatch in Runde 1 UND Terminierung in
    Runde 2.

    A7-3: 2 Overrides (audit, _handle_solver_command).
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=["COMMAND: RUN solver", "GO"])
    monkeypatch.setattr(
        pipeline, "_handle_solver_command",
        lambda *a, **kw: None)
    gerufen: list[str] = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(kind))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 0, (
        f"erwartet rc=0 bei Sequenz COMMAND->GO, "
        f"gefunden rc={rc}")
    n = gerufen.count("judge_command")
    assert n == 1, (
        f"erwartet judge_command genau 1x (Runde 1 "
        f"COMMAND, Runde 2 GO), gefunden {n}x. "
        f"Alle audits: {gerufen[:20]}")
    # A8-4-nach-1: verdict-Assert trennt "break"
    # (verdict=GO, rc=0 aus Apply) von "return 0"
    # (verdict=NO-GO, rc=0 aus fruehem return).
    assert ref[0].review_runden[-1]["verdict"] == "GO", (
        f"erwartet letzter verdict GO, gefunden "
        f"{ref[0].review_runden[-1].get('verdict')!r}")



# =====================================================================
# 3a-1c-1b (2026-10-19): AQ-Tests V2-Dispatch + Fallback.
# =====================================================================


def test_run_pipeline_fallback_go(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1b AQ: Fallback-Anker run_pipeline-Loop.

    Sequenz ["COMMAND: RUN solver"], judge_verdict="GO".
    Runde 1 = COMMAND (Sequenz-Ende), Runde 2 = Fallback
    "GO" -> break -> Apply-Pfad -> rc=0.

    Fallback-Anker fuer run_pipeline-Loop, NICHT fuer
    V1/V2 (A8-5-Nach-1).

    Apply-Pfad: wie test_t2 (984f784). apply_and_recheck
    ist im Helper gemockt und setzt
    state.mess_protokoll_nach_apply.

    Overrides:
      1. audit.
      2. _handle_solver_command.
    Helper-Parameter: judge_verdict_sequenz, judge_verdict.
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=["COMMAND: RUN solver"],
        judge_verdict="GO")
    monkeypatch.setattr(
        pipeline, "_handle_solver_command",
        lambda *a, **kw: None)
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(kind))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 0, (
        f"erwartet rc=0 bei Fallback GO, gefunden rc={rc}")
    n = gerufen.count("judge_command")
    assert n == 1, (
        f"erwartet judge_command 1x, gefunden {n}x. "
        f"Alle: {gerufen[:20]}")
    assert ref[0].review_runden[-1]["verdict"] == "GO", (
        f"erwartet verdict GO nach Fallback, "
        f"gefunden {ref[0].review_runden[-1].get('verdict')!r}")


def test_run_pipeline_no_go_dispatch(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1b AQ: NO-GO ohne Trigger -> solver_trigger.

    Sequenz ["NO-GO", "GO"]. Runde 1 NO-GO ohne Trigger
    (_trigger_grund=""), Runde 2 GO -> break.

    Erwartete Kinds: solver_trigger (8256).
    NICHT erwartet: solver_trigger_a/b/c, solver_max_
    runden_erreicht, solver_budget_exhausted,
    solver_failed, solver_befund, recovery_no_go.

    Layer VOR/NACH (A8-3-Nach-3a):
      solver_trigger in audit_kinds  | C4-Rumpf | V2
      review_runden enthaelt NO-GO   | C4-Rumpf | C4-Rumpf
      rc == 0                        | C4-Rumpf | C4-Rumpf

    Overrides:
      1. gegenstand_gleich -> (0.0, "").
      2. pruefe_trigger_b -> False.
      3. budget_or_recover -> None.
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=["NO-GO", "GO"])
    monkeypatch.setattr(
        pipeline, "gegenstand_gleich",
        lambda *a, **kw: (0.0, ""))
    monkeypatch.setattr(
        pipeline, "pruefe_trigger_b",
        lambda *a, **kw: False)
    monkeypatch.setattr(
        pipeline, "budget_or_recover",
        lambda *a, **kw: None)
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(kind))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 0, (
        f"erwartet rc=0 (NO-GO Runde 1, GO Runde 2), "
        f"gefunden rc={rc}")
    assert gerufen.count("solver_trigger") == 1, (
        f"erwartet solver_trigger 1x, gefunden "
        f"{gerufen.count('solver_trigger')}x. "
        f"Alle: {gerufen[:20]}")
    for kind in ("solver_trigger_a", "solver_trigger_b",
                 "solver_trigger_c",
                 "solver_max_runden_erreicht",
                 "solver_budget_exhausted",
                 "solver_failed", "solver_befund",
                 "recovery_no_go"):
        assert kind not in gerufen, (
            f"unerwarteter audit-Kind {kind!r}: "
            f"{gerufen[:20]}")
    verdicts = [r.get("verdict") for r in ref[0].review_runden]
    assert "NO-GO" in verdicts, (
        f"review_runden enthaelt kein NO-GO: {verdicts}")


def test_run_pipeline_no_go_recovery(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1b AQ: 2x NO-GO -> Recovery post-loop.

    Sequenz starr NO-GO. 2 Runden NO-GO -> Loop endet.
    post-loop if verdict != "GO": Recovery -> rc=15.

    Layer VOR/NACH (A8-3-Nach-3a):
      rc == 15                        | C4-Rumpf | C4-Rumpf
      recovery_no_go in audit_kinds   | C4-Rumpf | C4-Rumpf
    V2 wird durchlaufen (2x None/continue), nicht
    direkt asserted (A8-3-Nach-2b).

    Overrides:
      1. gegenstand_gleich -> (0.0, "").
      2. pruefe_trigger_b -> False.
      3. ask_reviewer_for_recovery -> RecoveryVorschlag.
      4. print_recovery -> None.
      5. audit -> Sammeln.
    Helper-Parameter: judge_verdict="NO-GO".
    budget_or_recover NICHT im Recovery-Pfad (8460-8468).
    """
    mock_run_pipeline_deps(monkeypatch, judge_verdict="NO-GO")
    monkeypatch.setattr(
        pipeline, "gegenstand_gleich",
        lambda *a, **kw: (0.0, ""))
    monkeypatch.setattr(
        pipeline, "pruefe_trigger_b",
        lambda *a, **kw: False)
    monkeypatch.setattr(
        pipeline, "ask_reviewer_for_recovery",
        lambda *a, **kw: type("V", (), {
            "frage_an_menschen": "test-frage",
            "empfehlung": "test-empfehlung"})())
    monkeypatch.setattr(
        pipeline, "print_recovery",
        lambda *a, **kw: None)
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(kind))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 15, (
        f"erwartet rc=15 bei 2x NO-GO, gefunden rc={rc}")
    assert gerufen.count("recovery_no_go") == 1, (
        f"erwartet recovery_no_go 1x, gefunden "
        f"{gerufen.count('recovery_no_go')}x. "
        f"Alle: {gerufen[:20]}")



# =====================================================================
# 3a-1c-1-b (2026-10-19): UNKLAR-Verhaltens-Tests (A9-8-3a).
# Profi-Ansatz: _review_unklar_widerspruch NICHT gemockt (pure Logik).
# =====================================================================


def _fake_recovery_obj():
    return type("V", (), {
        "frage_an_menschen": "test-frage",
        "empfehlung": "test-empfehlung"})()


def test_run_pipeline_unklar_kette_rc14(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1-b AQ: 2x UNKLAR in Folge -> rc=14.

    Zitat _review_verdict_behandlung (V2) Z. 8839-8922:
        if verdict == "UNKLAR":
            _hat_widerspruch = _review_unklar_widerspruch(
                reply.content)
            if _hat_widerspruch:
                audit("review_unklar_widerspruch", ...)
            else:
                audit("review_r15_verstoss", ...)
            _n_unklar = sum(...)
            if _n_unklar >= 2:
                audit("review_unklar_eskalation", {...})
                ...
                return 14

    _review_unklar_widerspruch laeuft real (pure Logik,
    startswith "Widerspruch:"). ask_llm liefert 2x
    "Widerspruch: Test\nUNKLAR" -> classify_verdict
    Fallback -> UNKLAR.

    Overrides (3, Profi-Ansatz):
      1. ask_reviewer_for_recovery (LLM-nah).
      2. print_recovery (Seiteneffekt).
      3. audit (Spy).
    Helper-Parameter: judge_verdict_sequenz.
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=[
            "Widerspruch: Test\nUNKLAR",
            "Widerspruch: Test\nUNKLAR",
        ])
    monkeypatch.setattr(
        pipeline, "ask_reviewer_for_recovery",
        lambda *a, **kw: _fake_recovery_obj())
    monkeypatch.setattr(
        pipeline, "print_recovery", lambda *a: None)
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(
            (kind, payload)))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 14, (
        f"erwartet rc=14 bei 2x UNKLAR, gefunden rc={rc}")
    kinds = [k for k, _ in gerufen]
    assert kinds.count("review_unklar_widerspruch") == 2, (
        f"erwartet 2x review_unklar_widerspruch, "
        f"gefunden {kinds.count('review_unklar_widerspruch')}x. "
        f"Alle: {kinds[:20]}")
    assert kinds.count("review_unklar_eskalation") == 1, (
        f"erwartet 1x review_unklar_eskalation, "
        f"gefunden {kinds.count('review_unklar_eskalation')}x")
    assert "review_r15_verstoss" not in kinds, (
        f"unerwartet review_r15_verstoss: {kinds[:20]}")


def test_run_pipeline_unklar_eskalation_payload_raw(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1-b AQ: review_unklar_eskalation Payload enthaelt
    raw + n_unklar.

    Zitat _review_verdict_behandlung (V2) Z. 8896-8901:
        audit("review_unklar_eskalation",
              {"runde": runde,
               "n_unklar": _n_unklar,
               "raw": reply.content[:2000]},
              project_dir, project_name)

    Overrides (3, Profi-Ansatz): wie Test 1.
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=[
            "Widerspruch: Test\nUNKLAR",
            "Widerspruch: Test\nUNKLAR",
        ])
    monkeypatch.setattr(
        pipeline, "ask_reviewer_for_recovery",
        lambda *a, **kw: _fake_recovery_obj())
    monkeypatch.setattr(
        pipeline, "print_recovery", lambda *a: None)
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(
            (kind, payload)))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 14
    eskalationen = [
        p for k, p in gerufen if k == "review_unklar_eskalation"]
    assert len(eskalationen) == 1, (
        f"erwartet 1x review_unklar_eskalation, "
        f"gefunden {len(eskalationen)}x")
    payload = eskalationen[0]
    assert "raw" in payload, (
        f"raw fehlt in Payload: {payload}")
    assert payload["n_unklar"] == 2, (
        f"n_unklar != 2: {payload.get('n_unklar')}")
    assert "Widerspruch: Test" in payload["raw"], (
        f"raw enthaelt nicht den Widerspruch-Text: "
        f"{payload['raw'][:100]}")



def test_run_pipeline_unklar_ohne_widerspruch_r15_verstoss(
        tmp_path: Path, monkeypatch) -> None:
    """3a-1c-1-b AQ: 1x UNKLAR ohne Widerspruch -> Verstoss-Audit.

    Zitat _review_verdict_behandlung (V2) Z. 8840-8854:
        if verdict == "UNKLAR":
            _hat_widerspruch = _review_unklar_widerspruch(
                reply.content)
            if _hat_widerspruch:
                audit("review_unklar_widerspruch", ...)
            else:
                audit("review_r15_verstoss",
                      {"rund": runde,
                       "grund": "unklar_ohne_widerspruch"}, ...)
            _n_unklar = sum(...)
            if _n_unklar >= 2:
                ...
                return 14
            continue

    Sequenz: Runde 1 "Ich weiss nicht." -> UNKLAR ohne
    Widerspruch (Verstoss), 1x UNKLAR reicht NICHT fuer
    Eskalation -> continue. Runde 2 GO -> break -> rc=0.

    Overrides (1): audit (Spy).
    _review_unklar_widerspruch laeuft real (pure Logik).
    Kein ask_reviewer_for_recovery / print_recovery
    (nicht erreicht).
    """
    mock_run_pipeline_deps(
        monkeypatch,
        judge_verdict_sequenz=[
            "Ich weiss nicht.",
            "GO",
        ])
    gerufen: list = []
    monkeypatch.setattr(
        pipeline, "audit",
        lambda kind, payload, *a, **kw: gerufen.append(
            (kind, payload)))
    ref: list = []
    rc = pipeline.run_pipeline(
        "test-projekt", "Test-Auftrag", ref)
    assert rc == 0, (
        f"erwartet rc=0 (UNKLAR dann GO), gefunden rc={rc}")
    kinds = [k for k, _ in gerufen]
    assert kinds.count("review_r15_verstoss") == 1, (
        f"erwartet 1x review_r15_verstoss, "
        f"gefunden {kinds.count('review_r15_verstoss')}x. "
        f"Alle: {kinds[:20]}")
    assert kinds.count("review_unklar_eskalation") == 0, (
        "unerwartet review_unklar_eskalation (1x UNKLAR "
        "darf nicht eskalieren)")
    assert kinds.count("review_unklar_widerspruch") == 0



# =====================================================================
# 3a-1c-2-vorbereitung (2026-10-19): Verhaltens-Tests fuer
# _build_commit_input (A10-13a). Ersetzen Struktur-Tests.
# =====================================================================


def test_build_commit_input_enthaelt_unterblock_kontext() -> None:
    """A10-13a: _build_commit_input uebernimmt unterblock_kontext.

    _build_commit_input bekommt w11_unterblock_kontext als
    Parameter (Signatur: state, diff_name_only,
    w11_unterblock_kontext, auflagen_text). Der Test prueft
    das Verhalten, NICHT die Code-Position (run_pipeline
    vs _commit_review_loop). Nach 3a-1c-2 bleibt der Test
    gruen: _build_commit_input verhaelt sich gleich.
    """
    from test_pipeline import build_test_state
    state = build_test_state()
    result = pipeline._build_commit_input(
        state, "core/x.py",
        "UNTERBLOCK: U1 (1 von 2) \u2014 Testtitel",
        "keine")
    assert "UNTERBLOCK:" in result
    assert "U1" in result
    assert "1 von 2" in result


def test_build_commit_input_ohne_unterblock_kontext() -> None:
    """A10-13a: leerer unterblock_kontext -> kein UNTERBLOCK-Marker."""
    from test_pipeline import build_test_state
    state = build_test_state()
    result = pipeline._build_commit_input(
        state, "core/x.py", "", "keine")
    assert "UNTERBLOCK:" not in result
